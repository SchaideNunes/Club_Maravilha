"""
Feature 5 - Dashboard operacional do painel admin (prefixo /api/v1/dashboard, protegido por get_current_admin).

Contratos:
- GET /api/v1/dashboard/resumo -> 200
    {
      "total_associados": int,        # todos os associados cadastrados (qualquer status)
      "faturas_pagas_mes": int,       # faturas PAGO com referencia_mes = mês de hoje_clube() (AAAA-MM)
      "faturas_pendentes_mes": int,   # faturas PENDENTE com referencia_mes = mês corrente
      "faturas_atrasadas": int,       # faturas ATRASADA de qualquer mês
      "disparos_hoje": int,           # LogMensagem (SUCESSO + ERRO) com enviado_em no dia de hoje_clube()
      "disparos_erro_hoje": int,      # LogMensagem ERRO no dia de hoje_clube()
      "whatsapp_status": "CONECTADO" | "DESCONECTADO" | "AGUARDANDO_QRCODE"
    }
  "Hoje" é o dia civil no fuso do clube (settings.TIMEZONE): de 00:00 a 24:00 locais, mesmo com
  enviado_em gravado em UTC. O status do WhatsApp vem de `provider.get_connection_status()` via a
  dependência `get_provider` de app/api/v1/endpoints/whatsapp.py (sobrescrita nos testes); se o
  provider lançar exceção ou devolver valor desconhecido, responde "DESCONECTADO" (nunca 500).
- GET /api/v1/dashboard/atividades?limit=20 (1..100; fora disso 422) -> 200 lista unificada, ordenada
  por `data` DESC, com os últimos disparos (LogMensagem) e baixas (faturas PAGO com data_pagamento):
    {"tipo": "DISPARO" | "BAIXA", "data": datetime ISO, "descricao": str não vazia,
     "associado_nome": str | null, "status": str | null}
  DISPARO: data = enviado_em, status = "SUCESSO" | "ERRO". BAIXA: data = data_pagamento.
  `limit` vale para a lista já unificada. Faturas PAGO sem data_pagamento não entram.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import pytest
from httpx import AsyncClient

from app.api.v1.endpoints.whatsapp import get_provider
from app.core import clock
from app.main import app
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.services.whatsapp_service import MockWhatsAppProvider

RESUMO = "/api/v1/dashboard/resumo"
ATIVIDADES = "/api/v1/dashboard/atividades"


class ProviderStatus(MockWhatsAppProvider):
    def __init__(self, status: str = "CONECTADO", falhar: bool = False) -> None:
        super().__init__()
        self.status = status
        self.falhar = falhar

    async def get_connection_status(self) -> Dict[str, Any]:
        if self.falhar:
            raise RuntimeError("engine fora do ar")
        return {"status": self.status}


@pytest.fixture(autouse=True)
def hoje_15_de_outubro(monkeypatch):
    instante = datetime(2026, 10, 15, 12, 0, tzinfo=clock.get_clube_tz())
    monkeypatch.setattr(clock, "agora_clube", lambda: instante)


@pytest.fixture
def usar_provider():
    def _usar(provider) -> None:
        app.dependency_overrides[get_provider] = lambda: provider
    yield _usar
    app.dependency_overrides.pop(get_provider, None)


def _socio(n: int, **campos) -> Associado:
    dados = dict(
        nome=f"Socio {n:02d}",
        cpf=f"000.000.{n:03d}-00",
        whatsapp=f"55759999900{n:02d}",
        email=f"socio{n}@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=10,
        data_adesao=date(2025, 1, 1),
    )
    dados.update(campos)
    return Associado(**dados)


def _fatura(socio, referencia, status, data_pagamento=None, vencimento=date(2026, 10, 10)) -> Fatura:
    return Fatura(
        associado_id=socio.id,
        referencia_mes=referencia,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=vencimento,
        status=status,
        forma_pagamento=FormaPagamento.PIX,
        data_pagamento=data_pagamento,
    )


def _log(enviado_em, status=StatusEnvio.SUCESSO, socio=None, etapa=EtapaRegua.D0) -> LogMensagem:
    return LogMensagem(
        associado_id=socio.id if socio else None,
        destinatario=socio.whatsapp if socio else "5575999990000",
        etapa=etapa,
        mensagem="Mensagem de cobrança",
        status=status,
        erro="falha" if status == StatusEnvio.ERRO else None,
        enviado_em=enviado_em,
    )


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


async def _popular(db_session):
    socios = [_socio(n) for n in range(1, 9)]
    socios[7].status = StatusAssociado.BLOQUEADO
    db_session.add_all(socios)
    await db_session.flush()

    db_session.add_all([
        # Mês corrente (2026-10)
        _fatura(socios[0], "2026-10", StatusFatura.PAGO, _utc(2026, 10, 10, 15, 0)),
        _fatura(socios[1], "2026-10", StatusFatura.PAGO, _utc(2026, 10, 12, 15, 0)),
        _fatura(socios[2], "2026-10", StatusFatura.PENDENTE),
        _fatura(socios[3], "2026-10", StatusFatura.PENDENTE),
        _fatura(socios[4], "2026-10", StatusFatura.PENDENTE),
        _fatura(socios[5], "2026-10", StatusFatura.ATRASADA),
        _fatura(socios[6], "2026-10", StatusFatura.CANCELADO),
        # Mês anterior (2026-09): PAGO não conta no mês; ATRASADA conta no total de atrasadas
        _fatura(socios[0], "2026-09", StatusFatura.PAGO, _utc(2026, 9, 10, 15, 0), date(2026, 9, 10)),
        _fatura(socios[1], "2026-09", StatusFatura.ATRASADA, vencimento=date(2026, 9, 10)),
        _fatura(socios[2], "2026-09", StatusFatura.ATRASADA, vencimento=date(2026, 9, 10)),
    ])

    db_session.add_all([
        _log(_utc(2026, 10, 15, 13, 0), StatusEnvio.SUCESSO, socios[2]),     # hoje 10:00 local
        _log(_utc(2026, 10, 15, 14, 0), StatusEnvio.ERRO, socios[3]),        # hoje 11:00 local
        _log(_utc(2026, 10, 16, 2, 30), StatusEnvio.SUCESSO, socios[4]),     # hoje 23:30 local
        _log(_utc(2026, 10, 15, 2, 30), StatusEnvio.ERRO, socios[5]),        # ontem 23:30 local
        _log(_utc(2026, 10, 14, 12, 0), StatusEnvio.SUCESSO, socios[6]),     # ontem
    ])
    await db_session.commit()
    return socios


# ------------------------------------------------------------------------------
# Resumo
# ------------------------------------------------------------------------------
async def test_resumo_agrega_indicadores_do_mes_e_do_dia(async_client: AsyncClient, db_session, usar_provider):
    await _popular(db_session)
    usar_provider(ProviderStatus("CONECTADO"))

    res = await async_client.get(RESUMO)

    assert res.status_code == 200, res.text
    assert res.json() == {
        "total_associados": 8,
        "faturas_pagas_mes": 2,
        "faturas_pendentes_mes": 3,
        "faturas_atrasadas": 3,
        "disparos_hoje": 3,
        "disparos_erro_hoje": 1,
        "whatsapp_status": "CONECTADO",
    }


async def test_resumo_banco_vazio_retorna_zeros(async_client: AsyncClient, usar_provider):
    usar_provider(ProviderStatus("DESCONECTADO"))

    res = await async_client.get(RESUMO)

    assert res.status_code == 200
    corpo = res.json()
    for campo in (
        "total_associados",
        "faturas_pagas_mes",
        "faturas_pendentes_mes",
        "faturas_atrasadas",
        "disparos_hoje",
        "disparos_erro_hoje",
    ):
        assert corpo[campo] == 0, campo
    assert corpo["whatsapp_status"] == "DESCONECTADO"


async def test_resumo_repassa_aguardando_qrcode(async_client: AsyncClient, usar_provider):
    usar_provider(ProviderStatus("AGUARDANDO_QRCODE"))
    res = await async_client.get(RESUMO)
    assert res.json()["whatsapp_status"] == "AGUARDANDO_QRCODE"


async def test_resumo_tolera_falha_do_provider(async_client: AsyncClient, usar_provider):
    usar_provider(ProviderStatus(falhar=True))

    res = await async_client.get(RESUMO)

    assert res.status_code == 200
    assert res.json()["whatsapp_status"] == "DESCONECTADO"


async def test_resumo_status_desconhecido_vira_desconectado(async_client: AsyncClient, usar_provider):
    usar_provider(ProviderStatus("QUALQUER_COISA"))
    res = await async_client.get(RESUMO)
    assert res.json()["whatsapp_status"] == "DESCONECTADO"


async def test_resumo_usa_mes_de_hoje_clube(async_client: AsyncClient, db_session, usar_provider, monkeypatch):
    await _popular(db_session)
    usar_provider(ProviderStatus())
    instante = datetime(2026, 9, 20, 12, 0, tzinfo=clock.get_clube_tz())
    monkeypatch.setattr(clock, "agora_clube", lambda: instante)

    corpo = (await async_client.get(RESUMO)).json()

    assert corpo["faturas_pagas_mes"] == 1
    assert corpo["faturas_pendentes_mes"] == 0
    assert corpo["disparos_hoje"] == 0


# ------------------------------------------------------------------------------
# Atividades recentes
# ------------------------------------------------------------------------------
async def test_atividades_unifica_disparos_e_baixas_em_ordem_decrescente(async_client: AsyncClient, db_session):
    await _popular(db_session)

    res = await async_client.get(ATIVIDADES, params={"limit": 50})

    assert res.status_code == 200, res.text
    itens = res.json()
    # 5 disparos + 3 faturas PAGO com data_pagamento
    assert len(itens) == 8
    assert [i["tipo"] for i in itens].count("DISPARO") == 5
    assert [i["tipo"] for i in itens].count("BAIXA") == 3

    datas = [datetime.fromisoformat(i["data"].replace("Z", "+00:00")).replace(tzinfo=None) for i in itens]
    assert datas == sorted(datas, reverse=True)

    primeiro = itens[0]
    assert primeiro["tipo"] == "DISPARO"
    assert primeiro["associado_nome"] == "Socio 05"
    assert primeiro["status"] == "SUCESSO"

    for item in itens:
        assert set(item) >= {"tipo", "data", "descricao", "associado_nome", "status"}
        assert isinstance(item["descricao"], str) and item["descricao"].strip()

    baixas = [i for i in itens if i["tipo"] == "BAIXA"]
    assert [b["associado_nome"] for b in baixas] == ["Socio 02", "Socio 01", "Socio 01"]

    erros = [i for i in itens if i["tipo"] == "DISPARO" and i["status"] == "ERRO"]
    assert {e["associado_nome"] for e in erros} == {"Socio 04", "Socio 06"}


async def test_atividades_limit_vale_para_a_lista_unificada(async_client: AsyncClient, db_session):
    await _popular(db_session)

    itens = (await async_client.get(ATIVIDADES, params={"limit": 4})).json()

    assert len(itens) == 4
    # 16/10 02:30Z, 15/10 14:00Z, 15/10 13:00Z, 15/10 02:30Z (todos disparos, mais recentes que as baixas)
    assert [i["associado_nome"] for i in itens] == ["Socio 05", "Socio 04", "Socio 03", "Socio 06"]


async def test_atividades_limit_padrao_20(async_client: AsyncClient, db_session):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    db_session.add_all([_log(_utc(2026, 10, 1 + (n % 14), n % 24, 0), socio=socio) for n in range(30)])
    await db_session.commit()

    itens = (await async_client.get(ATIVIDADES)).json()

    assert len(itens) == 20


async def test_atividades_disparo_sem_associado(async_client: AsyncClient, db_session):
    db_session.add(_log(_utc(2026, 10, 15, 13, 0), etapa=EtapaRegua.TESTE))
    await db_session.commit()

    itens = (await async_client.get(ATIVIDADES)).json()

    assert len(itens) == 1
    assert itens[0]["tipo"] == "DISPARO"
    assert itens[0]["associado_nome"] is None


async def test_atividades_ignora_pago_sem_data_pagamento(async_client: AsyncClient, db_session):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    db_session.add(_fatura(socio, "2026-10", StatusFatura.PAGO, data_pagamento=None))
    await db_session.commit()

    assert (await async_client.get(ATIVIDADES)).json() == []


@pytest.mark.parametrize("limit", [0, 101, -1])
async def test_atividades_limit_fora_do_intervalo_retorna_422(async_client: AsyncClient, limit):
    res = await async_client.get(ATIVIDADES, params={"limit": limit})
    assert res.status_code == 422
