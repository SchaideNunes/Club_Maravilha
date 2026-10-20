"""
Cadastro de Sócios - Planos/categorias de mensalidade.

Contratos (rotas administrativas, prefixo /api/v1/planos):
- GET    /planos/?ativo=true|false   200 lista ordenada por nome; cada item traz total_associados
                                     (vínculos com sócios que não estão INATIVOS)
- POST   /planos/                    201 | 409 nome duplicado (case-insensitive) | 422 valor negativo
- PATCH  /planos/{id}                200 | 404 | 409 nome de outro plano
- DELETE /planos/{id}                204 | 404 | 409 quando algum sócio (qualquer status) usa o plano

Valor da mensalidade: Decimal com 2 casas, serializado como string ("150.00"). Valor 0 = isento.
"""
import uuid
from decimal import Decimal

from httpx import AsyncClient

from app.models.associado import Associado, StatusAssociado

URL = "/api/v1/planos/"


async def _criar_plano(client: AsyncClient, **extra) -> dict:
    payload = {"nome": "Individual", "valor_mensalidade": "150.00", **extra}
    res = await client.post(URL, json=payload)
    assert res.status_code == 201, res.text
    return res.json()


async def test_cria_plano_com_valor_decimal(async_client: AsyncClient):
    plano = await _criar_plano(async_client, nome="Familiar", descricao="Titular + família", valor_mensalidade="220.5")

    assert plano["nome"] == "Familiar"
    assert plano["descricao"] == "Titular + família"
    assert Decimal(plano["valor_mensalidade"]) == Decimal("220.50")
    assert plano["ativo"] is True
    assert plano["total_associados"] == 0
    uuid.UUID(plano["id"])


async def test_plano_isento_aceita_valor_zero(async_client: AsyncClient):
    plano = await _criar_plano(async_client, nome="Remido", valor_mensalidade="0")
    assert Decimal(plano["valor_mensalidade"]) == Decimal("0.00")


async def test_valor_negativo_e_nome_curto_retornam_422(async_client: AsyncClient):
    assert (await async_client.post(URL, json={"nome": "Neg", "valor_mensalidade": "-1"})).status_code == 422
    assert (await async_client.post(URL, json={"nome": "A", "valor_mensalidade": "10"})).status_code == 422


async def test_nome_duplicado_case_insensitive_retorna_409(async_client: AsyncClient):
    await _criar_plano(async_client, nome="Individual")
    res = await async_client.post(URL, json={"nome": "  individual ", "valor_mensalidade": "100"})
    assert res.status_code == 409


async def test_lista_ordenada_por_nome_e_filtra_ativos(async_client: AsyncClient):
    await _criar_plano(async_client, nome="Universitário", valor_mensalidade="90")
    familiar = await _criar_plano(async_client, nome="Familiar", valor_mensalidade="220")
    await _criar_plano(async_client, nome="Individual", valor_mensalidade="150")
    await async_client.patch(f"{URL}{familiar['id']}", json={"ativo": False})

    todos = (await async_client.get(URL)).json()
    assert [p["nome"] for p in todos] == ["Familiar", "Individual", "Universitário"]

    ativos = (await async_client.get(URL, params={"ativo": "true"})).json()
    assert [p["nome"] for p in ativos] == ["Individual", "Universitário"]

    inativos = (await async_client.get(URL, params={"ativo": "false"})).json()
    assert [p["nome"] for p in inativos] == ["Familiar"]


async def test_patch_atualiza_e_valida_conflito(async_client: AsyncClient):
    individual = await _criar_plano(async_client, nome="Individual")
    await _criar_plano(async_client, nome="Familiar", valor_mensalidade="220")

    res = await async_client.patch(f"{URL}{individual['id']}", json={"valor_mensalidade": "160.00", "descricao": "Novo"})
    assert res.status_code == 200
    assert Decimal(res.json()["valor_mensalidade"]) == Decimal("160.00")
    assert res.json()["descricao"] == "Novo"

    conflito = await async_client.patch(f"{URL}{individual['id']}", json={"nome": "FAMILIAR"})
    assert conflito.status_code == 409

    inexistente = await async_client.patch(f"{URL}{uuid.uuid4()}", json={"nome": "X Y"})
    assert inexistente.status_code == 404


async def test_total_associados_ignora_inativos(async_client: AsyncClient, db_session):
    plano = await _criar_plano(async_client)
    plano_id = uuid.UUID(plano["id"])
    db_session.add_all([
        Associado(nome="Ana Ativa", cpf="529.982.247-25", whatsapp="5575999990001", email="ana@x.com",
                  plano_id=plano_id, status=StatusAssociado.ATIVO),
        Associado(nome="Ivo Inativo", cpf="111.444.777-35", whatsapp="5575999990002", email="ivo@x.com",
                  plano_id=plano_id, status=StatusAssociado.INATIVO),
    ])
    await db_session.commit()

    lista = (await async_client.get(URL)).json()
    assert lista[0]["total_associados"] == 1


async def test_delete_remove_plano_sem_socios(async_client: AsyncClient):
    plano = await _criar_plano(async_client)
    assert (await async_client.delete(f"{URL}{plano['id']}")).status_code == 204
    assert (await async_client.get(URL)).json() == []
    assert (await async_client.delete(f"{URL}{plano['id']}")).status_code == 404


async def test_delete_bloqueado_quando_ha_socio_vinculado_mesmo_inativo(async_client: AsyncClient, db_session):
    plano = await _criar_plano(async_client)
    db_session.add(Associado(nome="Ivo Inativo", cpf="111.444.777-35", whatsapp="5575999990002",
                             email="ivo@x.com", plano_id=uuid.UUID(plano["id"]), status=StatusAssociado.INATIVO))
    await db_session.commit()

    res = await async_client.delete(f"{URL}{plano['id']}")
    assert res.status_code == 409
    assert "associado" in res.json()["detail"].lower()


async def test_rotas_de_planos_exigem_autenticacao(async_client_sem_auth: AsyncClient):
    assert (await async_client_sem_auth.get(URL)).status_code == 401
    assert (await async_client_sem_auth.post(URL, json={"nome": "Xx", "valor_mensalidade": "1"})).status_code == 401
