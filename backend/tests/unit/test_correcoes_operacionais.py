"""
Correções operacionais pós-MVP.

1. Inadimplência independe da automação de WhatsApp: com `automacao_ativa=False` nada é enfileirado,
   mas sócios com fatura vencida há DIAS_CARENCIA_BLOQUEIO dias ou mais continuam virando INADIMPLENTE.
2. POST /faturas/{id}/simular-pagamento só existe fora de produção (404 com ENVIRONMENT=production).
3. Catraca:
   - Em produção, TURNSTILE_API_TOKEN precisa ser forte (não pode ser o padrão nem ter menos de 16 caracteres).
   - O checksum da whitelist muda quando o CONTEÚDO muda (ex: um sócio sai e outro entra), não só a contagem.
   - QR de convidado só libera no dia da visita (data_visita == hoje do clube).
"""
import secrets
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core import clock
from app.core.config import Settings, settings
from app.core.constants import DIAS_CARENCIA_BLOQUEIO
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.billing_engine_service import BillingEngineService
from app.services.catraca_service import CatracaService
from app.services.whatsapp_queue_service import MessagePriority

HOJE = date(2026, 10, 15)


@pytest.fixture
def congelar_hoje(monkeypatch):
    instante = datetime(HOJE.year, HOJE.month, HOJE.day, 12, 0, tzinfo=clock.get_clube_tz())
    monkeypatch.setattr(clock, "agora_clube", lambda: instante)


class FilaFalsa:
    def __init__(self) -> None:
        self.itens = []

    async def enqueue(self, phone, message, priority=MessagePriority.NORMAL, log_context=None) -> None:
        self.itens.append(phone)


def _socio(n: int, **campos) -> Associado:
    dados = dict(
        nome=f"Socio {n:02d}",
        cpf=f"000.000.{n:03d}-00",
        whatsapp=f"55759999900{n:02d}",
        email=f"socio{n}@clube.com",
        status=StatusAssociado.ATIVO,
        facial_id=f"FACE-{n}",
    )
    dados.update(campos)
    return Associado(**dados)


# ------------------------------------------------------------------------------
# 1. Inadimplência sem automação
# ------------------------------------------------------------------------------
async def test_automacao_desligada_ainda_marca_inadimplentes(db_session):
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.automacao_ativa = False
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    socio_id = socio.id
    db_session.add(Fatura(associado_id=socio_id, referencia_mes="2026-08", valor_base=Decimal("150.00"),
                          valor_total=Decimal("150.00"), status=StatusFatura.PENDENTE,
                          data_vencimento=HOJE - timedelta(days=DIAS_CARENCIA_BLOQUEIO)))
    await db_session.commit()
    fila = FilaFalsa()

    report = await BillingEngineService(session=db_session, queue_service=fila).processar_regua_diaria(
        data_referencia=HOJE
    )

    assert fila.itens == []
    assert report.automacao_ativa is False
    assert report.total_enfileirados == 0
    assert report.inadimplentes_atualizados == 1
    status_atual = await db_session.scalar(select(Associado.status).where(Associado.id == socio_id))
    assert status_atual == StatusAssociado.INADIMPLENTE


# ------------------------------------------------------------------------------
# 2. Simular pagamento fora de produção
# ------------------------------------------------------------------------------
async def test_simular_pagamento_nao_existe_em_producao(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    res = await async_client.post(f"/api/v1/faturas/{uuid.uuid4()}/simular-pagamento")
    assert res.status_code == 404
    assert "produção" in res.json()["detail"]


# ------------------------------------------------------------------------------
# 3. Catraca
# ------------------------------------------------------------------------------
def _settings_producao(**extra) -> Settings:
    return Settings(
        ENVIRONMENT="production",
        SECRET_KEY=secrets.token_urlsafe(48),
        PIX_WEBHOOK_SECRET="segredo_webhook_super_seguro_producao_2026",
        **extra,
    )


@pytest.mark.parametrize("token", ["mock_turnstile_token", "token_seguranca_catraca_local", "curto", ""])
def test_producao_exige_token_forte_da_catraca(token):
    with pytest.raises(RuntimeError, match="TURNSTILE_API_TOKEN"):
        _settings_producao(TURNSTILE_API_TOKEN=token)


def test_producao_aceita_token_forte_da_catraca():
    forte = secrets.token_urlsafe(24)
    assert _settings_producao(TURNSTILE_API_TOKEN=forte).TURNSTILE_API_TOKEN == forte


async def test_checksum_muda_quando_um_socio_e_trocado_por_outro(db_session, congelar_hoje):
    ana = _socio(1)
    bia = _socio(2)
    caio = _socio(3, status=StatusAssociado.INADIMPLENTE)
    db_session.add_all([ana, bia, caio])
    await db_session.commit()
    service = CatracaService(db_session)

    antes = await service.get_whitelist()
    assert antes["total_authorized"] == 2

    # Mesma contagem, conteúdo diferente: Bia sai, Caio entra
    bia.status = StatusAssociado.INADIMPLENTE
    caio.status = StatusAssociado.ATIVO
    await db_session.commit()
    depois = await service.get_whitelist()

    assert depois["total_authorized"] == 2
    assert depois["checksum"] != antes["checksum"]
    # Sem mudança, o checksum é estável
    assert (await service.get_whitelist())["checksum"] == depois["checksum"]


@pytest.mark.parametrize("dias", [-1, 1])
async def test_qr_de_convidado_so_vale_no_dia_da_visita(db_session, congelar_hoje, dias):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    convite = Convidado(associado_titular_id=socio.id, nome="Visitante", data_visita=HOJE + timedelta(days=dias),
                        status=StatusConvidado.EMITIDO)
    db_session.add(convite)
    await db_session.commit()

    resultado = await CatracaService(db_session).process_turnstile_event({"token": convite.qr_code_token})

    assert resultado["authorized"] is False
    await db_session.refresh(convite)
    assert convite.status == StatusConvidado.EMITIDO


async def test_qr_de_convidado_no_dia_libera(db_session, congelar_hoje):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    convite = Convidado(associado_titular_id=socio.id, nome="Visitante", data_visita=HOJE,
                        status=StatusConvidado.EMITIDO)
    db_session.add(convite)
    await db_session.commit()

    resultado = await CatracaService(db_session).process_turnstile_event({"token": convite.qr_code_token})

    assert resultado["authorized"] is True
