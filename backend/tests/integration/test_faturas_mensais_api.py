"""
Testes de integração da API de faturas mensais e baixa manual (Feature 3).

Contratos HTTP:
- POST /api/v1/faturas/gerar-mes  body opcional {"referencia_mes": "AAAA-MM"} (default: mês de
  hoje_clube()) -> 200 {"referencia_mes", "criadas", "ja_existentes", "total"}; referência
  inválida (mês fora de 01..12 ou formato diferente de AAAA-MM) -> 422.
- POST /api/v1/faturas/marcar-atrasadas ?data_referencia=AAAA-MM-DD (opcional, default
  hoje_clube()) -> 200 {"data_referencia", "atualizadas"}.
- GET /api/v1/faturas/ ?referencia_mes=&status=&q=&associado_id=&page=1&page_size=20 (<=100)
  -> 200 {"items", "total", "page", "page_size", "total_pages"}; cada item traz id, associado_id,
  associado_nome, referencia_mes, data_vencimento, valor_base, valor_convidados_excedentes,
  valor_desconto, valor_total, convites_usados, convites_extras, status, forma_pagamento,
  data_pagamento, lembretes_ativos. `q` busca no nome (case-insensitive) ou CPF do associado.
  Ordenação: nome do associado asc, depois data_vencimento desc.
- POST /api/v1/faturas/{id}/baixa-manual body FaturaBaixaManual -> 200 FaturaResponse
  (status PAGO, forma_pagamento, data_pagamento, lembretes_ativos=false, convites_usados,
  convites_extras); PAGO/CANCELADO -> 409; inexistente -> 404; forma inválida -> 422.
- POST /api/v1/faturas/ (criação manual) duplicando associado+referencia_mes -> 409.
- FaturaResponse passa a expor convites_usados, convites_extras e lembretes_ativos.
"""
import asyncio
import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core import clock
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services import whatsapp_queue_service as fila_mod
from app.services.whatsapp_queue_service import WhatsAppQueueService
from app.services.whatsapp_service import MockWhatsAppProvider
from tests.conftest import TestingSessionLocal

API = "/api/v1/faturas"


@pytest.fixture
def congelar_hoje(monkeypatch):
    def _congelar(dia: date) -> None:
        instante = datetime(dia.year, dia.month, dia.day, 12, 0, tzinfo=clock.get_clube_tz())
        monkeypatch.setattr(clock, "agora_clube", lambda: instante)
    return _congelar


@pytest.fixture
def provider():
    return MockWhatsAppProvider()


@pytest.fixture
def fila_global(provider):
    """Fila global isolada (Mock + banco de teste), restaurada ao final."""
    anterior = fila_mod._global_queue
    fila = WhatsAppQueueService(
        provider=provider,
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
        session_factory=TestingSessionLocal,
    )
    fila_mod.set_global_whatsapp_queue(fila)
    yield fila
    fila_mod._global_queue = anterior


async def _configurar(session):
    cfg = await ConfiguracaoRepository(session).get_or_create()
    cfg.valor_mensalidade = Decimal("150.00")
    cfg.franquia_convidados = 8
    cfg.valor_convidado_extra = Decimal("35.00")
    cfg.chave_pix = "financeiro@clubmaravilha.com.br"
    cfg.template_recibo = "Recibo {nome} {valor_total} {vencimento}"
    await session.commit()
    return cfg


def _socio(n: int, nome: str | None = None, **campos) -> Associado:
    dados = dict(
        nome=nome or f"Socio {n:02d}",
        cpf=f"000.000.{n:03d}-00",
        whatsapp=f"55759999900{n:02d}",
        email=f"socio{n}@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=10,
        data_adesao=date(2025, 1, 1),
    )
    dados.update(campos)
    return Associado(**dados)


async def _fatura(session, socio, referencia="2026-11", vencimento=date(2026, 11, 10),
                  status=StatusFatura.PENDENTE, **campos) -> Fatura:
    dados = dict(
        associado_id=socio.id,
        referencia_mes=referencia,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=vencimento,
        status=status,
    )
    dados.update(campos)
    fatura = Fatura(**dados)
    session.add(fatura)
    await session.commit()
    return fatura


# ---------------------------------------------------------------------------
# Geração mensal
# ---------------------------------------------------------------------------

async def test_gerar_mes_cria_faturas_e_e_idempotente(async_client: AsyncClient, db_session):
    await _configurar(db_session)
    socio = _socio(1, dia_vencimento=31)
    db_session.add_all([socio, _socio(2, status=StatusAssociado.BLOQUEADO)])
    await db_session.flush()
    db_session.add_all([
        Convidado(associado_titular_id=socio.id, nome=f"C{i}", data_visita=date(2026, 1, 15))
        for i in range(11)
    ])
    await db_session.commit()

    res = await async_client.post(f"{API}/gerar-mes", json={"referencia_mes": "2026-02"})
    assert res.status_code == 200
    assert res.json() == {"referencia_mes": "2026-02", "criadas": 2, "ja_existentes": 0, "total": 2}

    res2 = await async_client.post(f"{API}/gerar-mes", json={"referencia_mes": "2026-02"})
    assert res2.status_code == 200
    assert res2.json() == {"referencia_mes": "2026-02", "criadas": 0, "ja_existentes": 2, "total": 2}

    lista = await async_client.get(f"{API}/", params={"referencia_mes": "2026-02", "q": "Socio 01"})
    assert lista.status_code == 200
    [item] = lista.json()["items"]
    assert item["data_vencimento"] == "2026-02-28"
    assert item["status"] == "PENDENTE"
    assert Decimal(item["valor_base"]) == Decimal("150.00")
    assert item["convites_usados"] == 11
    assert item["convites_extras"] == 3
    assert Decimal(item["valor_convidados_excedentes"]) == Decimal("105.00")
    assert Decimal(item["valor_total"]) == Decimal("255.00")


async def test_gerar_mes_sem_corpo_usa_mes_corrente(async_client: AsyncClient, db_session, congelar_hoje):
    congelar_hoje(date(2026, 11, 3))
    await _configurar(db_session)
    db_session.add(_socio(1))
    await db_session.commit()

    res = await async_client.post(f"{API}/gerar-mes")

    assert res.status_code == 200
    assert res.json()["referencia_mes"] == "2026-11"
    assert res.json()["criadas"] == 1


@pytest.mark.parametrize("referencia", ["2026-13", "2026-00", "2026/11", "11-2026", ""])
async def test_gerar_mes_referencia_invalida_retorna_422(async_client: AsyncClient, db_session, referencia):
    await _configurar(db_session)
    res = await async_client.post(f"{API}/gerar-mes", json={"referencia_mes": referencia})
    assert res.status_code == 422


async def test_criacao_manual_duplicada_no_mesmo_mes_retorna_409(async_client: AsyncClient, db_session):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.commit()
    payload = {
        "associado_id": str(socio.id),
        "referencia_mes": "2026-11",
        "valor_base": "150.00",
        "data_vencimento": "2026-11-10",
        "forma_pagamento": "PIX",
    }

    assert (await async_client.post(f"{API}/", json=payload)).status_code == 201
    dup = await async_client.post(f"{API}/", json=payload)
    assert dup.status_code == 409


# ---------------------------------------------------------------------------
# Atraso e situação financeira
# ---------------------------------------------------------------------------

async def test_marcar_atrasadas_reflete_na_situacao_financeira(async_client: AsyncClient, db_session,
                                                              congelar_hoje):
    congelar_hoje(date(2026, 11, 15))
    socio = _socio(1)
    db_session.add(socio)
    await db_session.commit()
    fatura = await _fatura(db_session, socio)

    antes = await async_client.get(f"/api/v1/associados/{socio.id}")
    assert antes.json()["situacao_financeira"] == "PENDENTE"

    res = await async_client.post(f"{API}/marcar-atrasadas")
    assert res.status_code == 200
    assert res.json() == {"data_referencia": "2026-11-15", "atualizadas": 1}

    detalhe = await async_client.get(f"{API}/{fatura.id}")
    assert detalhe.json()["status"] == "ATRASADA"
    depois = await async_client.get(f"/api/v1/associados/{socio.id}")
    assert depois.json()["situacao_financeira"] == "ATRASADO"


async def test_marcar_atrasadas_com_data_explicita(async_client: AsyncClient, db_session):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.commit()
    await _fatura(db_session, socio)

    res = await async_client.post(f"{API}/marcar-atrasadas", params={"data_referencia": "2026-11-10"})
    assert res.json() == {"data_referencia": "2026-11-10", "atualizadas": 0}
    res = await async_client.post(f"{API}/marcar-atrasadas", params={"data_referencia": "2026-11-11"})
    assert res.json() == {"data_referencia": "2026-11-11", "atualizadas": 1}


# ---------------------------------------------------------------------------
# Painel de mensalidades
# ---------------------------------------------------------------------------

async def _popular_painel(session):
    ana = _socio(1, nome="Ana Lima")
    bruno = _socio(2, nome="Bruno Costa")
    carla = _socio(3, nome="Carla Dias", cpf="529.982.247-25")
    session.add_all([ana, bruno, carla])
    await session.commit()
    await _fatura(session, carla, valor_convidados_excedentes=Decimal("35.00"),
                  valor_total=Decimal("185.00"), convites_usados=9, convites_extras=1)
    await _fatura(session, ana, status=StatusFatura.ATRASADA)
    await _fatura(session, bruno, status=StatusFatura.PAGO)
    await _fatura(session, ana, referencia="2026-10", vencimento=date(2026, 10, 10), status=StatusFatura.PAGO)
    return ana, bruno, carla


async def test_listagem_painel_paginada_com_dados_do_associado(async_client: AsyncClient, db_session):
    ana, bruno, carla = await _popular_painel(db_session)

    res = await async_client.get(f"{API}/", params={"referencia_mes": "2026-11"})

    assert res.status_code == 200
    corpo = res.json()
    assert corpo["total"] == 3
    assert corpo["page"] == 1
    assert corpo["page_size"] == 20
    assert corpo["total_pages"] == 1
    assert [i["associado_nome"] for i in corpo["items"]] == ["Ana Lima", "Bruno Costa", "Carla Dias"]
    item_carla = corpo["items"][2]
    assert item_carla["associado_id"] == str(carla.id)
    assert item_carla["referencia_mes"] == "2026-11"
    assert item_carla["data_vencimento"] == "2026-11-10"
    assert Decimal(item_carla["valor_base"]) == Decimal("150.00")
    assert Decimal(item_carla["valor_convidados_excedentes"]) == Decimal("35.00")
    assert Decimal(item_carla["valor_desconto"]) == Decimal("0.00")
    assert Decimal(item_carla["valor_total"]) == Decimal("185.00")
    assert item_carla["convites_usados"] == 9
    assert item_carla["convites_extras"] == 1
    assert item_carla["status"] == "PENDENTE"
    assert item_carla["lembretes_ativos"] is True
    assert "forma_pagamento" in item_carla and "data_pagamento" in item_carla
    assert corpo["items"][1]["lembretes_ativos"] is False  # Bruno: PAGO


async def test_listagem_painel_filtros_status_e_busca(async_client: AsyncClient, db_session):
    ana, _, carla = await _popular_painel(db_session)

    atrasadas = (await async_client.get(f"{API}/", params={"status": "ATRASADA"})).json()
    assert [i["associado_nome"] for i in atrasadas["items"]] == ["Ana Lima"]

    por_nome = (await async_client.get(f"{API}/", params={"q": "ana"})).json()
    assert por_nome["total"] == 2  # Ana tem faturas de 2026-10 e 2026-11
    assert [i["referencia_mes"] for i in por_nome["items"]] == ["2026-11", "2026-10"]

    por_cpf = (await async_client.get(f"{API}/", params={"q": "52998224725", "referencia_mes": "2026-11"})).json()
    assert [i["associado_id"] for i in por_cpf["items"]] == [str(carla.id)]

    combinado = (await async_client.get(
        f"{API}/", params={"q": "ana", "status": "PAGO", "referencia_mes": "2026-10"}
    )).json()
    assert combinado["total"] == 1


async def test_listagem_painel_paginacao(async_client: AsyncClient, db_session):
    await _popular_painel(db_session)

    pagina2 = (await async_client.get(f"{API}/", params={"page": 2, "page_size": 2})).json()

    assert pagina2["total"] == 4
    assert pagina2["page"] == 2
    assert pagina2["page_size"] == 2
    assert pagina2["total_pages"] == 2
    assert len(pagina2["items"]) == 2
    assert (await async_client.get(f"{API}/", params={"page_size": 101})).status_code == 422
    assert (await async_client.get(f"{API}/", params={"page": 0})).status_code == 422


# ---------------------------------------------------------------------------
# Baixa manual
# ---------------------------------------------------------------------------

async def test_baixa_manual_endpoint_fluxo_completo(async_client: AsyncClient, db_session, fila_global,
                                                   provider, congelar_hoje):
    congelar_hoje(date(2026, 11, 20))
    await _configurar(db_session)
    socio = _socio(1, nome="Joana Prado", status=StatusAssociado.INADIMPLENTE)
    db_session.add(socio)
    await db_session.commit()
    fatura = await _fatura(db_session, socio, status=StatusFatura.ATRASADA,
                           convites_usados=9, convites_extras=1,
                           valor_convidados_excedentes=Decimal("35.00"), valor_total=Decimal("185.00"))

    res = await async_client.post(
        f"{API}/{fatura.id}/baixa-manual",
        json={"forma_pagamento": "DINHEIRO", "data_pagamento": "2026-01-15T10:00:00Z"},
    )

    assert res.status_code == 200
    corpo = res.json()
    assert corpo["id"] == str(fatura.id)
    assert corpo["status"] == "PAGO"
    assert corpo["forma_pagamento"] == "DINHEIRO"
    assert corpo["data_pagamento"].startswith("2026-01-15T10:00:00")
    assert corpo["lembretes_ativos"] is False
    assert corpo["convites_usados"] == 9
    assert corpo["convites_extras"] == 1

    socio_res = await async_client.get(f"/api/v1/associados/{socio.id}")
    assert socio_res.json()["status"] == "ATIVO"
    assert socio_res.json()["situacao_financeira"] == "EM_DIA"

    assert fila_global.qsize == 1
    await fila_global.process_one()
    assert provider.sent_messages[0]["message"] == "Recibo Joana Prado R$ 185,00 10/11/2026"
    async with TestingSessionLocal() as s:
        logs = list((await s.execute(select(LogMensagem))).scalars().all())
    assert [(l.etapa, l.status, l.fatura_id) for l in logs] == [
        (EtapaRegua.RECIBO, StatusEnvio.SUCESSO, fatura.id)
    ]


@pytest.mark.parametrize("status_fatura", [StatusFatura.PAGO, StatusFatura.CANCELADO])
async def test_baixa_manual_endpoint_conflito(async_client: AsyncClient, db_session, fila_global, status_fatura):
    await _configurar(db_session)
    socio = _socio(1)
    db_session.add(socio)
    await db_session.commit()
    fatura = await _fatura(db_session, socio, status=status_fatura)

    res = await async_client.post(f"{API}/{fatura.id}/baixa-manual", json={"forma_pagamento": "PIX"})

    assert res.status_code == 409
    assert fila_global.qsize == 0


async def test_baixa_manual_endpoint_inexistente_404(async_client: AsyncClient, fila_global):
    res = await async_client.post(f"{API}/{uuid.uuid4()}/baixa-manual", json={"forma_pagamento": "PIX"})
    assert res.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"forma_pagamento": "BOLETO"},
        {},
        {"forma_pagamento": "PIX", "data_pagamento": "2999-01-01T00:00:00Z"},
    ],
)
async def test_baixa_manual_endpoint_payload_invalido_422(async_client: AsyncClient, db_session,
                                                         fila_global, payload):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.commit()
    fatura = await _fatura(db_session, socio)

    res = await async_client.post(f"{API}/{fatura.id}/baixa-manual", json=payload)

    assert res.status_code == 422


async def test_baixa_manual_endpoint_concorrente_gera_um_recibo(async_client: AsyncClient, db_session,
                                                               fila_global):
    await _configurar(db_session)
    socio = _socio(1)
    db_session.add(socio)
    await db_session.commit()
    fatura = await _fatura(db_session, socio)

    respostas = await asyncio.gather(
        async_client.post(f"{API}/{fatura.id}/baixa-manual", json={"forma_pagamento": "PIX"}),
        async_client.post(f"{API}/{fatura.id}/baixa-manual", json={"forma_pagamento": "CARTAO"}),
    )

    assert sorted(r.status_code for r in respostas) == [200, 409]
    assert fila_global.qsize == 1
