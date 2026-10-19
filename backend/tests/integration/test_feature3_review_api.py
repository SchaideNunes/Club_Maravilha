"""
Testes de integração para os endpoints da API (Feature 3 - Code Review):
1. Baixa manual via HTTP retorna 200 mesmo quando a fila de WhatsApp pós-commit falha;
2. API da Catraca: endpoint /whitelist inclui no D+1 e exclui no D+7;
3. Validação de padrão no GET /faturas/ (referencia_mes) rejeita formato inválido com 422;
4. Busca textual q no GET /faturas/ com escape de curingas SQL (% e _);
5. Reativação na baixa manual notifica sincronização da catraca.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.catraca_service import CatracaService
from app.services.whatsapp_queue_service import WhatsAppQueueService

API_FATURAS = "/api/v1/faturas"
API_CATRACA = "/api/v1/catraca"


async def _configurar_clube(session):
    cfg = await ConfiguracaoRepository(session).get_or_create()
    cfg.valor_mensalidade = Decimal("150.00")
    cfg.franquia_convidados = 8
    cfg.valor_convidado_extra = Decimal("35.00")
    cfg.chave_pix = "financeiro@clubmaravilha.com.br"
    cfg.template_recibo = "Recibo {nome} {valor_total}"
    await session.commit()
    return cfg


def _criar_socio(numero: int, **campos) -> Associado:
    dados = {
        "nome": f"Associado API {numero:02d}",
        "cpf": f"222.333.444-{numero:02d}",
        "whatsapp": f"55759999911{numero:02d}",
        "email": f"socio_api_{numero}@clube.com",
        "status": StatusAssociado.ATIVO,
        "dia_vencimento": 10,
        "data_adesao": date(2025, 1, 1),
    }
    dados.update(campos)
    return Associado(**dados)


# ===========================================================================
# 1. Baixa manual HTTP retorna 200 mesmo com falha no enqueue pós-commit
# ===========================================================================

@pytest.mark.asyncio
async def test_api_baixa_manual_retorna_200_com_falha_na_fila(async_client: AsyncClient, db_session, monkeypatch):
    """
    Quando o enqueue do WhatsApp pós-commit levanta uma exceção, o endpoint de baixa
    manual deve responder HTTP 200 e a fatura deve constar com status PAGO.
    """
    await _configurar_clube(db_session)
    socio = _criar_socio(1)
    db_session.add(socio)
    await db_session.commit()

    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-11",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 11, 10),
        status=StatusFatura.PENDENTE,
    )
    db_session.add(fatura)
    await db_session.commit()

    # Monkeypatch no enqueue da classe WhatsAppQueueService para simular falha
    monkeypatch.setattr(
        WhatsAppQueueService,
        "enqueue",
        AsyncMock(side_effect=RuntimeError("Timeout ao conectar ao motor Baileys")),
    )

    fatura_id = fatura.id
    resp = await async_client.post(
        f"{API_FATURAS}/{fatura_id}/baixa-manual",
        json={"forma_pagamento": "PIX"}
    )

    assert resp.status_code == 200
    dados = resp.json()
    assert dados["id"] == str(fatura_id)
    assert dados["status"] == "PAGO"
    assert dados["forma_pagamento"] == "PIX"


# ===========================================================================
# 2. Catraca Whitelist: inclusão no D+1 e bloqueio no D+7
# ===========================================================================

@pytest.mark.asyncio
async def test_api_catraca_whitelist_carencia_d_mais_7(async_client: AsyncClient, db_session):
    """
    Sócio ativo com fatura vencida em 10/10 e marcada ATRASADA:
    - GET /api/v1/catraca/whitelist?data=2026-10-11 (D+1) -> Sócio autorizado;
    - GET /api/v1/catraca/whitelist?data=2026-10-17 (D+7) -> Sócio bloqueado.
    """
    socio = _criar_socio(2, facial_id="FACE_API_D7")
    db_session.add(socio)
    await db_session.commit()

    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-10",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 10, 10),
        status=StatusFatura.ATRASADA,
    )
    db_session.add(fatura)
    await db_session.commit()

    # D+1: autoriza
    resp_d1 = await async_client.get(f"{API_CATRACA}/whitelist", params={"data": "2026-10-11"})
    assert resp_d1.status_code == 200
    membros_d1 = [m["facial_id"] for m in resp_d1.json()["members"]]
    assert "FACE_API_D7" in membros_d1

    # D+7: bloqueia
    resp_d7 = await async_client.get(f"{API_CATRACA}/whitelist", params={"data": "2026-10-17"})
    assert resp_d7.status_code == 200
    membros_d7 = [m["facial_id"] for m in resp_d7.json()["members"]]
    assert "FACE_API_D7" not in membros_d7


# ===========================================================================
# 3. Validação do parâmetro referencia_mes no GET /faturas/
# ===========================================================================

@pytest.mark.asyncio
async def test_api_faturas_validacao_referencia_mes(async_client: AsyncClient):
    """
    O parâmetro referencia_mes deve aceitar estritamente o formato AAAA-MM (01 a 12),
    retornando HTTP 422 para formatos ou meses inválidos.
    """
    # Mês 13 inválido
    r1 = await async_client.get(f"{API_FATURAS}/", params={"referencia_mes": "2026-13"})
    assert r1.status_code == 422

    # String arbitrária
    r2 = await async_client.get(f"{API_FATURAS}/", params={"referencia_mes": "novembro"})
    assert r2.status_code == 422

    # Formato correto
    r3 = await async_client.get(f"{API_FATURAS}/", params={"referencia_mes": "2026-11"})
    assert r3.status_code == 200


# ===========================================================================
# 4. Busca textual q com escape de caracteres especiais
# ===========================================================================

@pytest.mark.asyncio
async def test_api_faturas_busca_com_escape_de_curingas(async_client: AsyncClient, db_session):
    """
    Garante que buscas com caracteres '%' ou '_' não atuem como curingas do LIKE.
    """
    await _configurar_clube(db_session)
    s1 = _criar_socio(4, nome="Roberto Carlos")
    s2 = _criar_socio(5, nome="Roberto_Carlos")
    db_session.add_all([s1, s2])
    await db_session.commit()

    # Cria faturas para ambos
    db_session.add_all([
        Fatura(
            associado_id=s1.id,
            referencia_mes="2026-11",
            valor_base=Decimal("150.00"),
            valor_total=Decimal("150.00"),
            data_vencimento=date(2026, 11, 10),
            status=StatusFatura.PENDENTE,
        ),
        Fatura(
            associado_id=s2.id,
            referencia_mes="2026-11",
            valor_base=Decimal("150.00"),
            valor_total=Decimal("150.00"),
            data_vencimento=date(2026, 11, 10),
            status=StatusFatura.PENDENTE,
        ),
    ])
    await db_session.commit()

    resp = await async_client.get(f"{API_FATURAS}/", params={"q": "Roberto_Carlos"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    nomes = [item["associado_nome"] for item in items]
    assert "Roberto_Carlos" in nomes
    assert "Roberto Carlos" not in nomes


# ===========================================================================
# 5. Reativação na baixa manual notifica catraca
# ===========================================================================

@pytest.mark.asyncio
async def test_api_baixa_manual_com_reativacao_notifica_catraca(async_client: AsyncClient, db_session):
    """
    Quando um associado INADIMPLENTE tem sua única fatura em aberto liquidada,
    ele é reativado para ATIVO e a sincronização imediata da catraca é disparada.
    """
    await _configurar_clube(db_session)
    socio = _criar_socio(6, status=StatusAssociado.INADIMPLENTE)
    db_session.add(socio)
    await db_session.commit()

    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-10",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 10, 10),
        status=StatusFatura.ATRASADA,
    )
    db_session.add(fatura)
    await db_session.commit()

    fatura_id = fatura.id
    socio_id = socio.id

    with patch.object(CatracaService, "notify_turnstile_sync", new_callable=AsyncMock) as mock_sync:
        mock_sync.return_value = {"status": "synchronized"}
        resp = await async_client.post(
            f"{API_FATURAS}/{fatura_id}/baixa-manual",
            json={"forma_pagamento": "DINHEIRO"}
        )
        assert resp.status_code == 200
        mock_sync.assert_awaited_once()

    # Confirma que o sócio foi reativado no banco
    db_session.expire_all()
    socio_atualizado = (await db_session.execute(select(Associado).where(Associado.id == socio_id))).scalar_one()
    assert socio_atualizado.status == StatusAssociado.ATIVO
