"""
Feature 2 (MVP) - Endpoint rápido de convidado por associado e cota mensal configurável.

Contratos definidos aqui (a implementar):
- POST /api/v1/associados/{associado_id}/convidados
    body: {"nome": str (3..150), "cpf": Optional[str], "data_visita": Optional[date] (padrão: hoje)}
    201: {
        "convidado": ConvidadoResponse,
        "is_gratuito": bool,
        "tipo": "GRATUITO" | "EXCEDENTE",
        "convidados_usados_mes": int,     # no mês de data_visita, incluindo este, sem CANCELADO
        "franquia": int,                  # Configuracao.franquia_convidados
        "excedentes_mes": int,            # max(0, usados - franquia)
        "valor_taxa_extra": "35.00",      # Configuracao.valor_convidado_extra (unitário)
        "aviso": Optional[str]            # None se gratuito; texto com "franquia" e "R$ 35,00" se excedente
    }
    404 associado inexistente | 403 associado BLOQUEADO (detail cita "bloqueado") | 422 payload inválido
- POST /api/v1/convidados/ e GET /api/v1/convidados/cota/{id} também usam a Configuracao.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.repositories.configuracao_repository import ConfiguracaoRepository


def _url(associado_id) -> str:
    return f"/api/v1/associados/{associado_id}/convidados"


async def _socio(db_session, status: StatusAssociado = StatusAssociado.ATIVO) -> Associado:
    socio = Associado(
        nome="Titular Convite Rapido",
        cpf="529.982.247-25",
        whatsapp="5575999990000",
        email="convite.rapido@club.com",
        status=status,
    )
    db_session.add(socio)
    await db_session.commit()
    return socio


async def _configurar(db_session, franquia: int, valor_extra: str) -> None:
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.franquia_convidados = franquia
    cfg.valor_convidado_extra = Decimal(valor_extra)
    await db_session.commit()


async def test_primeiro_convidado_e_gratuito(async_client: AsyncClient, db_session):
    socio = await _socio(db_session)

    res = await async_client.post(_url(socio.id), json={"nome": "Visitante Um"})

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["is_gratuito"] is True
    assert body["tipo"] == "GRATUITO"
    assert body["convidados_usados_mes"] == 1
    assert body["franquia"] == 8
    assert body["excedentes_mes"] == 0
    assert Decimal(body["valor_taxa_extra"]) == Decimal("35.00")
    assert body["aviso"] is None
    assert body["convidado"]["associado_titular_id"] == str(socio.id)
    assert body["convidado"]["data_visita"] == date.today().isoformat()
    assert body["convidado"]["status"] == "EMITIDO"
    assert len(body["convidado"]["qr_code_token"]) == 64


async def test_excedente_usa_configuracao_e_retorna_aviso(async_client: AsyncClient, db_session):
    socio = await _socio(db_session)
    await _configurar(db_session, franquia=2, valor_extra="50.00")

    respostas = [
        (await async_client.post(_url(socio.id), json={"nome": f"Visitante {i}"})).json()
        for i in range(4)
    ]

    assert [r["is_gratuito"] for r in respostas] == [True, True, False, False]
    assert [r["tipo"] for r in respostas] == ["GRATUITO", "GRATUITO", "EXCEDENTE", "EXCEDENTE"]
    assert [r["convidados_usados_mes"] for r in respostas] == [1, 2, 3, 4]
    assert [r["excedentes_mes"] for r in respostas] == [0, 0, 1, 2]
    assert all(r["franquia"] == 2 for r in respostas)
    assert all(Decimal(r["valor_taxa_extra"]) == Decimal("50.00") for r in respostas)
    assert [r["aviso"] is None for r in respostas] == [True, True, False, False]
    assert "franquia" in respostas[2]["aviso"].lower()
    assert "R$ 50,00" in respostas[2]["aviso"]
    assert Decimal(respostas[2]["convidado"]["valor_cobrado"]) == Decimal("50.00")
    assert Decimal(respostas[0]["convidado"]["valor_cobrado"]) == Decimal("0")


async def test_cota_zera_na_virada_do_mes(async_client: AsyncClient, db_session):
    socio = await _socio(db_session)
    hoje = date.today()
    mes_anterior = hoje.replace(day=1) - timedelta(days=1)
    db_session.add_all([
        Convidado(associado_titular_id=socio.id, nome=f"Antigo {i}", data_visita=mes_anterior)
        for i in range(8)
    ])
    await db_session.commit()

    body = (await async_client.post(_url(socio.id), json={"nome": "Novo Mes"})).json()

    assert body["is_gratuito"] is True
    assert body["convidados_usados_mes"] == 1


async def test_cancelados_nao_consomem_franquia(async_client: AsyncClient, db_session):
    socio = await _socio(db_session)
    hoje = date.today()
    db_session.add_all(
        [Convidado(associado_titular_id=socio.id, nome=f"Ativo {i}", data_visita=hoje) for i in range(7)]
        + [Convidado(associado_titular_id=socio.id, nome="Cancelado", data_visita=hoje,
                     status=StatusConvidado.CANCELADO)]
    )
    await db_session.commit()

    body = (await async_client.post(_url(socio.id), json={"nome": "Oitavo"})).json()

    assert body["is_gratuito"] is True
    assert body["convidados_usados_mes"] == 8
    assert body["excedentes_mes"] == 0


async def test_data_visita_explicita_conta_no_mes_da_visita(async_client: AsyncClient, db_session):
    socio = await _socio(db_session)
    hoje = date.today()
    proximo_mes = (hoje.replace(day=1) + timedelta(days=32)).replace(day=5)
    db_session.add_all([
        Convidado(associado_titular_id=socio.id, nome=f"Hoje {i}", data_visita=hoje) for i in range(3)
    ])
    await db_session.commit()

    body = (await async_client.post(
        _url(socio.id), json={"nome": "Futuro", "cpf": "123.456.789-09", "data_visita": proximo_mes.isoformat()}
    )).json()

    assert body["convidados_usados_mes"] == 1
    assert body["convidado"]["data_visita"] == proximo_mes.isoformat()
    assert body["convidado"]["cpf"] == "123.456.789-09"


async def test_contador_do_associado_reflete_convidado_adicionado(async_client: AsyncClient, db_session):
    socio = await _socio(db_session)
    for i in range(2):
        assert (await async_client.post(_url(socio.id), json={"nome": f"Visitante {i}"})).status_code == 201

    detalhe = (await async_client.get(f"/api/v1/associados/{socio.id}")).json()
    item = (await async_client.get("/api/v1/associados/", params={"q": "Titular"})).json()["items"][0]

    assert detalhe["convidados_usados_mes"] == 2
    assert item["convidados_usados_mes"] == 2


async def test_associado_bloqueado_nao_adiciona_convidado(async_client: AsyncClient, db_session):
    socio = await _socio(db_session, status=StatusAssociado.BLOQUEADO)

    res = await async_client.post(_url(socio.id), json={"nome": "Barrado"})

    assert res.status_code == 403
    assert "bloqueado" in res.json()["detail"].lower()
    lista = (await async_client.get("/api/v1/convidados/", params={"associado_id": str(socio.id)})).json()
    assert lista == []


async def test_associado_inexistente_retorna_404(async_client: AsyncClient):
    res = await async_client.post(_url(uuid.uuid4()), json={"nome": "Ninguem"})
    assert res.status_code == 404


@pytest.mark.parametrize("payload", [{}, {"nome": "ab"}, {"nome": "Valido", "data_visita": "amanha"}])
async def test_payload_invalido_retorna_422(async_client: AsyncClient, db_session, payload):
    socio = await _socio(db_session)
    res = await async_client.post(_url(socio.id), json=payload)
    assert res.status_code == 422


async def test_endpoints_legados_de_convidados_usam_configuracao(async_client: AsyncClient, db_session):
    socio = await _socio(db_session)
    await _configurar(db_session, franquia=1, valor_extra="42.50")
    hoje = date.today().isoformat()

    primeiro = await async_client.post(
        "/api/v1/convidados/", json={"associado_titular_id": str(socio.id), "nome": "Legado 1", "data_visita": hoje}
    )
    segundo = await async_client.post(
        "/api/v1/convidados/", json={"associado_titular_id": str(socio.id), "nome": "Legado 2", "data_visita": hoje}
    )
    cota = (await async_client.get(f"/api/v1/convidados/cota/{socio.id}")).json()

    assert primeiro.json()["is_gratuito"] is True
    assert segundo.json()["is_gratuito"] is False
    assert Decimal(segundo.json()["valor_cobrado"]) == Decimal("42.50")
    assert cota["franquia_total"] == 1
    assert cota["excedentes_emitidos"] == 1
    assert Decimal(cota["valor_unitario_excedente"]) == Decimal("42.50")
