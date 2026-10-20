"""
Cadastro de Sócios - Membros da família (dependentes) vinculados ao titular.

Contratos (prefixo /api/v1/associados/{associado_id}/familia):
- GET    /                 200 lista ordenada por nome | 404 associado inexistente
- POST   /                 201 | 404 associado | 409 CPF já cadastrado na família deste titular
                           | 422 CPF inválido / parentesco inválido / nascimento futuro
- PATCH  /{membro_id}      200 | 404 (membro inexistente ou de outro titular)
- DELETE /{membro_id}      204 | 404

Parentesco: CONJUGE | FILHO | ENTEADO | PAI_MAE | IRMAO | OUTRO. CPF opcional, normalizado para
000.000.000-00. Dependentes não consomem a franquia de convidados.
"""
import uuid

from httpx import AsyncClient

URL_ASSOCIADOS = "/api/v1/associados/"


async def _titular(client: AsyncClient, cpf: str = "529.982.247-25", email: str = "maria@maravilha.com") -> dict:
    res = await client.post(URL_ASSOCIADOS, json={
        "nome": "Maria Maravilha", "cpf": cpf, "whatsapp": "75999999999", "email": email,
    })
    assert res.status_code == 201, res.text
    return res.json()


def _url(associado_id: str) -> str:
    return f"{URL_ASSOCIADOS}{associado_id}/familia/"


async def test_cadastra_e_lista_dependentes_ordenados(async_client: AsyncClient):
    titular = await _titular(async_client)
    url = _url(titular["id"])

    res = await async_client.post(url, json={
        "nome": "Pedro Maravilha", "parentesco": "FILHO", "cpf": "11144477735", "data_nascimento": "2012-03-01",
    })
    assert res.status_code == 201, res.text
    filho = res.json()
    assert filho["cpf"] == "111.444.777-35"
    assert filho["parentesco"] == "FILHO"
    assert filho["ativo"] is True
    assert filho["associado_id"] == titular["id"]

    res = await async_client.post(url, json={"nome": "João Maravilha", "parentesco": "CONJUGE"})
    assert res.status_code == 201, res.text
    assert res.json()["cpf"] is None

    lista = (await async_client.get(url)).json()
    assert [m["nome"] for m in lista] == ["João Maravilha", "Pedro Maravilha"]


async def test_validacoes_retornam_422(async_client: AsyncClient):
    titular = await _titular(async_client)
    url = _url(titular["id"])
    assert (await async_client.post(url, json={"nome": "Pedro", "parentesco": "PRIMO"})).status_code == 422
    assert (await async_client.post(url, json={"nome": "Pedro", "parentesco": "FILHO", "cpf": "123"})).status_code == 422
    assert (await async_client.post(url, json={"nome": "Pe", "parentesco": "FILHO"})).status_code == 422
    assert (await async_client.post(url, json={
        "nome": "Pedro", "parentesco": "FILHO", "data_nascimento": "2999-01-01",
    })).status_code == 422


async def test_cpf_duplicado_na_mesma_familia_retorna_409(async_client: AsyncClient):
    titular = await _titular(async_client)
    url = _url(titular["id"])
    await async_client.post(url, json={"nome": "Pedro Maravilha", "parentesco": "FILHO", "cpf": "111.444.777-35"})
    res = await async_client.post(url, json={"nome": "Outro Nome", "parentesco": "OUTRO", "cpf": "11144477735"})
    assert res.status_code == 409


async def test_mesmo_dependente_pode_estar_em_duas_familias(async_client: AsyncClient):
    mae = await _titular(async_client)
    pai = await _titular(async_client, cpf="123.456.789-09", email="pai@maravilha.com")
    payload = {"nome": "Pedro Maravilha", "parentesco": "FILHO", "cpf": "111.444.777-35"}
    assert (await async_client.post(_url(mae["id"]), json=payload)).status_code == 201
    assert (await async_client.post(_url(pai["id"]), json=payload)).status_code == 201


async def test_atualiza_e_remove_dependente(async_client: AsyncClient):
    titular = await _titular(async_client)
    url = _url(titular["id"])
    membro = (await async_client.post(url, json={"nome": "Pedro Maravilha", "parentesco": "FILHO"})).json()

    res = await async_client.patch(f"{url}{membro['id']}", json={"nome": "Pedro M. Silva", "ativo": False})
    assert res.status_code == 200, res.text
    assert res.json()["nome"] == "Pedro M. Silva"
    assert res.json()["ativo"] is False

    assert (await async_client.delete(f"{url}{membro['id']}")).status_code == 204
    assert (await async_client.get(url)).json() == []
    assert (await async_client.delete(f"{url}{membro['id']}")).status_code == 404


async def test_membro_de_outro_titular_retorna_404(async_client: AsyncClient):
    mae = await _titular(async_client)
    pai = await _titular(async_client, cpf="123.456.789-09", email="pai@maravilha.com")
    membro = (await async_client.post(_url(mae["id"]), json={"nome": "Pedro Maravilha", "parentesco": "FILHO"})).json()

    assert (await async_client.patch(f"{_url(pai['id'])}{membro['id']}", json={"nome": "Hacker"})).status_code == 404
    assert (await async_client.delete(f"{_url(pai['id'])}{membro['id']}")).status_code == 404


async def test_titular_inexistente_retorna_404(async_client: AsyncClient):
    url = _url(str(uuid.uuid4()))
    assert (await async_client.get(url)).status_code == 404
    assert (await async_client.post(url, json={"nome": "Pedro Maravilha", "parentesco": "FILHO"})).status_code == 404
