"""
Feature 2 (MVP) - API de Associados para o painel admin: CRUD, validações, busca, filtro por
situação financeira, paginação e contagem eficiente.

Contratos definidos aqui (a implementar):
- POST   /api/v1/associados/            201 | 409 CPF duplicado (com/sem máscara) | 409 e-mail duplicado
                                         (case-insensitive) | 422 CPF inválido | 422 WhatsApp inválido
- PATCH  /api/v1/associados/{id}        200 | 404 | 409 e-mail de outro associado | 422 WhatsApp inválido
- GET    /api/v1/associados/{id}        200 | 404
- DELETE /api/v1/associados/{id}        405 (substituído por POST /{id}/inativar)
- GET    /api/v1/associados/?q=&situacao=EM_DIA|PENDENTE|ATRASADO&status=&page=&page_size=
    * q: nome (ilike) OU CPF com ou sem máscara (parcial)
    * situacao: derivada das faturas em aberto com referencia_mes <= mês corrente
      (ATRASADA => ATRASADO; senão PENDENTE => PENDENTE; senão EM_DIA); valor inválido => 422
    * ordenação por nome asc; resposta {items, total, page, page_size, total_pages}
    * cada item (e o detalhe/POST/PATCH) traz convidados_usados_mes, franquia_convidados
      (Configuracao.franquia_convidados) e situacao_financeira
    * listagem/detalhe NÃO carregam o histórico de convidados nem as faturas completas; o nº de
      queries não cresce com o nº de associados (sem N+1).
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import List

import pytest
from httpx import AsyncClient
from sqlalchemy import event

from app.models.associado import Associado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.configuracao_repository import ConfiguracaoRepository

URL = "/api/v1/associados/"
CPF_1 = "529.982.247-25"
CPF_2 = "111.444.777-35"
CPF_3 = "123.456.789-09"


def _payload(**extra) -> dict:
    return {
        "nome": "Maria Maravilha",
        "cpf": CPF_1,
        "whatsapp": "(75) 99999-9999",
        "email": "maria@maravilha.com",
        **extra,
    }


async def _criar(client: AsyncClient, **extra) -> dict:
    res = await client.post(URL, json=_payload(**extra))
    assert res.status_code == 201, res.text
    return res.json()


def _uuid(valor) -> uuid.UUID:
    return valor if isinstance(valor, uuid.UUID) else uuid.UUID(str(valor))


def _ref_mes(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _fatura(associado_id, referencia_mes: str, status: StatusFatura) -> Fatura:
    ano, mes = (int(p) for p in referencia_mes.split("-"))
    return Fatura(
        associado_id=_uuid(associado_id),
        referencia_mes=referencia_mes,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(ano, mes, 10),
        status=status,
    )


# ------------------------------------------------------------------------------
# Criação e validações
# ------------------------------------------------------------------------------
async def test_post_retorna_campos_do_painel(async_client: AsyncClient):
    criado = await _criar(async_client)

    assert criado["cpf"] == CPF_1
    assert criado["whatsapp"] == "5575999999999"
    assert criado["status"] == "ATIVO"
    assert criado["convidados_usados_mes"] == 0
    assert criado["franquia_convidados"] == 8
    assert criado["situacao_financeira"] == "EM_DIA"


async def test_post_aceita_cpf_sem_mascara_e_grava_formatado(async_client: AsyncClient):
    criado = await _criar(async_client, cpf="52998224725")
    assert criado["cpf"] == CPF_1


@pytest.mark.parametrize("cpf", ["52998224700", "111.111.111-11", "1234"])
async def test_post_cpf_invalido_retorna_422(async_client: AsyncClient, cpf):
    res = await async_client.post(URL, json=_payload(cpf=cpf))
    assert res.status_code == 422
    assert any(err["loc"][-1] == "cpf" for err in res.json()["detail"])


@pytest.mark.parametrize("cpf_repetido", [CPF_1, "52998224725"])
async def test_post_cpf_duplicado_retorna_409(async_client: AsyncClient, cpf_repetido):
    await _criar(async_client)
    res = await async_client.post(URL, json=_payload(cpf=cpf_repetido, email="outra@maravilha.com"))
    assert res.status_code == 409
    assert "CPF" in res.json()["detail"]


@pytest.mark.parametrize("email_repetido", ["maria@maravilha.com", "MARIA@Maravilha.com"])
async def test_post_email_duplicado_retorna_409(async_client: AsyncClient, email_repetido):
    await _criar(async_client)
    res = await async_client.post(URL, json=_payload(cpf=CPF_2, email=email_repetido))
    assert res.status_code == 409
    assert "e-mail" in res.json()["detail"].lower()


async def test_post_whatsapp_invalido_retorna_422(async_client: AsyncClient):
    res = await async_client.post(URL, json=_payload(whatsapp="123"))
    assert res.status_code == 422


# ------------------------------------------------------------------------------
# Atualização, detalhe e exclusão
# ------------------------------------------------------------------------------
async def test_patch_email_de_outro_associado_retorna_409(async_client: AsyncClient):
    a = await _criar(async_client)
    await _criar(async_client, cpf=CPF_2, email="joao@maravilha.com")

    res = await async_client.patch(f"{URL}{a['id']}", json={"email": "JOAO@maravilha.com"})
    assert res.status_code == 409


async def test_patch_status_bloqueado_e_whatsapp_invalido(async_client: AsyncClient):
    a = await _criar(async_client)

    res = await async_client.patch(f"{URL}{a['id']}", json={"status": "BLOQUEADO"})
    assert res.status_code == 200
    assert res.json()["status"] == "BLOQUEADO"
    assert res.json()["franquia_convidados"] == 8

    res = await async_client.patch(f"{URL}{a['id']}", json={"whatsapp": "999"})
    assert res.status_code == 422


async def test_patch_inexistente_retorna_404(async_client: AsyncClient):
    res = await async_client.patch(f"{URL}00000000-0000-0000-0000-000000000000", json={"nome": "Fulano"})
    assert res.status_code == 404


async def test_detalhe_traz_situacao_e_franquia_configurada(async_client: AsyncClient, db_session):
    a = await _criar(async_client)
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.franquia_convidados = 5
    db_session.add(_fatura(a["id"], _ref_mes(date.today()), StatusFatura.PENDENTE))
    await db_session.commit()

    detalhe = (await async_client.get(f"{URL}{a['id']}")).json()

    assert detalhe["franquia_convidados"] == 5
    assert detalhe["situacao_financeira"] == "PENDENTE"


async def test_inativar_substitui_a_exclusao(async_client: AsyncClient):
    a = await _criar(async_client)
    assert (await async_client.delete(f"{URL}{a['id']}")).status_code == 405
    assert (await async_client.post(f"{URL}{a['id']}/inativar", json={})).status_code == 200
    assert (await async_client.get(f"{URL}{a['id']}")).json()["status"] == "INATIVO"


# ------------------------------------------------------------------------------
# Listagem: busca, filtro, paginação
# ------------------------------------------------------------------------------
@pytest.fixture
async def tres_associados(async_client: AsyncClient) -> List[dict]:
    return [
        await _criar(async_client, nome="Carla Dias", cpf=CPF_1, email="carla@club.com"),
        await _criar(async_client, nome="Bruno Alves", cpf=CPF_2, email="bruno@club.com"),
        await _criar(async_client, nome="Ana Costa", cpf=CPF_3, email="ana@club.com"),
    ]


@pytest.mark.parametrize("termo", ["Carla", "carla dias", "529.982.247-25", "52998224725", "98224"])
async def test_busca_por_nome_ou_cpf_com_e_sem_mascara(async_client: AsyncClient, tres_associados, termo):
    res = await async_client.get(URL, params={"q": termo})
    assert res.status_code == 200
    assert [i["nome"] for i in res.json()["items"]] == ["Carla Dias"]


async def test_paginacao_ordenada_por_nome(async_client: AsyncClient, tres_associados):
    p1 = (await async_client.get(URL, params={"page": 1, "page_size": 2})).json()
    p2 = (await async_client.get(URL, params={"page": 2, "page_size": 2})).json()

    assert [i["nome"] for i in p1["items"]] == ["Ana Costa", "Bruno Alves"]
    assert [i["nome"] for i in p2["items"]] == ["Carla Dias"]
    assert (p1["total"], p1["total_pages"], p1["page"], p1["page_size"]) == (3, 2, 1, 2)


async def test_item_da_listagem_traz_contador_franquia_e_situacao(
    async_client: AsyncClient, db_session, tres_associados
):
    carla = tres_associados[0]
    hoje = date.today()
    mes_anterior = hoje.replace(day=1) - timedelta(days=1)
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.franquia_convidados = 4
    db_session.add_all([
        Convidado(associado_titular_id=_uuid(carla["id"]), nome="C1", data_visita=hoje),
        Convidado(associado_titular_id=_uuid(carla["id"]), nome="C2", data_visita=hoje),
        Convidado(associado_titular_id=_uuid(carla["id"]), nome="Cancelado", data_visita=hoje,
                  status=StatusConvidado.CANCELADO),
        Convidado(associado_titular_id=_uuid(carla["id"]), nome="Antigo", data_visita=mes_anterior),
    ])
    await db_session.commit()

    item = (await async_client.get(URL, params={"q": "Carla"})).json()["items"][0]

    assert item["convidados_usados_mes"] == 2
    assert item["franquia_convidados"] == 4
    assert item["situacao_financeira"] == "EM_DIA"


async def test_filtro_por_situacao_financeira(async_client: AsyncClient, db_session, tres_associados):
    carla, bruno, ana = tres_associados
    ref = _ref_mes(date.today())
    db_session.add_all([
        _fatura(carla["id"], ref, StatusFatura.PAGO),
        _fatura(bruno["id"], ref, StatusFatura.PENDENTE),
        _fatura(ana["id"], ref, StatusFatura.ATRASADA),
    ])
    await db_session.commit()

    async def nomes(situacao: str) -> tuple:
        body = (await async_client.get(URL, params={"situacao": situacao})).json()
        return body["total"], [i["nome"] for i in body["items"]], {i["situacao_financeira"] for i in body["items"]}

    assert await nomes("EM_DIA") == (1, ["Carla Dias"], {"EM_DIA"})
    assert await nomes("PENDENTE") == (1, ["Bruno Alves"], {"PENDENTE"})
    assert await nomes("ATRASADO") == (1, ["Ana Costa"], {"ATRASADO"})


async def test_filtro_situacao_combina_com_busca_e_paginacao(async_client: AsyncClient, db_session, tres_associados):
    carla, bruno, ana = tres_associados
    ref = _ref_mes(date.today())
    db_session.add_all([
        _fatura(bruno["id"], ref, StatusFatura.PENDENTE),
        _fatura(ana["id"], ref, StatusFatura.PENDENTE),
    ])
    await db_session.commit()

    body = (await async_client.get(URL, params={"situacao": "PENDENTE", "page_size": 1})).json()
    assert (body["total"], body["total_pages"]) == (2, 2)
    assert [i["nome"] for i in body["items"]] == ["Ana Costa"]

    body = (await async_client.get(URL, params={"situacao": "PENDENTE", "q": "Bruno"})).json()
    assert [i["nome"] for i in body["items"]] == ["Bruno Alves"]

    body = (await async_client.get(URL, params={"situacao": "EM_DIA", "q": "Bruno"})).json()
    assert body["total"] == 0 and body["items"] == []


async def test_filtro_situacao_invalida_retorna_422(async_client: AsyncClient):
    res = await async_client.get(URL, params={"situacao": "QUITADO"})
    assert res.status_code == 422


# ------------------------------------------------------------------------------
# Eficiência: agregação sem histórico e sem N+1
# ------------------------------------------------------------------------------
class _ContadorSQL:
    def __init__(self, sync_engine) -> None:
        self.engine = sync_engine
        self.statements: List[str] = []

    def _on_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def __enter__(self) -> "_ContadorSQL":
        event.listen(self.engine, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *exc) -> None:
        event.remove(self.engine, "before_cursor_execute", self._on_execute)


async def _popular(db_session, inicio: int, quantidade: int) -> None:
    hoje = date.today()
    ref = _ref_mes(hoje)
    for n in range(inicio, inicio + quantidade):
        a = Associado(
            nome=f"Socio {n:03d}",
            cpf=f"000.000.{n:03d}-00",
            whatsapp=f"5575999{n:06d}",
            email=f"socio{n}@club.com",
        )
        db_session.add(a)
        await db_session.flush()
        db_session.add_all([
            Convidado(associado_titular_id=a.id, nome="Conv A", data_visita=hoje),
            Convidado(associado_titular_id=a.id, nome="Conv B", data_visita=hoje - timedelta(days=40)),
            _fatura(a.id, ref, StatusFatura.PENDENTE),
        ])
    await db_session.commit()


async def test_listagem_nao_carrega_historico_e_nao_tem_n_mais_1(async_client: AsyncClient, db_session):
    engine = db_session.bind.sync_engine
    await _popular(db_session, 1, 2)
    await async_client.get(URL)  # aquece (cria Configuracao)

    with _ContadorSQL(engine) as poucos:
        res = await async_client.get(URL, params={"page_size": 50})
    assert res.status_code == 200 and res.json()["total"] == 2

    await _popular(db_session, 3, 6)
    with _ContadorSQL(engine) as muitos:
        res = await async_client.get(URL, params={"page_size": 50})
    assert res.status_code == 200 and res.json()["total"] == 8
    assert all(i["convidados_usados_mes"] == 1 for i in res.json()["items"])
    assert all(i["situacao_financeira"] == "PENDENTE" for i in res.json()["items"])

    assert len(muitos.statements) == len(poucos.statements), (poucos.statements, muitos.statements)
    todos = poucos.statements + muitos.statements
    assert not any("convidados.qr_code_token" in s for s in todos), "listagem carregou convidados completos"
    assert not any("faturas.pix_copia_cola" in s for s in todos), "listagem carregou faturas completas"


async def test_detalhe_nao_carrega_historico_de_convidados(async_client: AsyncClient, db_session):
    a = await _criar(async_client)
    db_session.add(Convidado(associado_titular_id=_uuid(a["id"]), nome="Conv", data_visita=date.today()))
    await db_session.commit()

    with _ContadorSQL(db_session.bind.sync_engine) as sql:
        detalhe = (await async_client.get(f"{URL}{a['id']}")).json()

    assert detalhe["convidados_usados_mes"] == 1
    assert not any("convidados.qr_code_token" in s for s in sql.statements)
