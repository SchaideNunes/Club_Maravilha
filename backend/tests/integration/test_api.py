"""
Testes de integração assíncronos para a API FastAPI.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """Testa a rota de saúde do sistema."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["service"] == "club-maravilha-backend"


@pytest.mark.asyncio
async def test_crud_associado_flow(async_client: AsyncClient):
    """Testa cadastro e consulta de associado com validações."""
    payload = {
        "nome": "Marina Souza",
        "cpf": "123.456.789-09",
        "whatsapp": "+5511977776666",
        "email": "marina.souza@clubmaravilha.com",
        "foto_url": "https://club.com/marina.webp"
    }

    # 1. Criação com sucesso
    create_res = await async_client.post("/api/v1/associados/", json=payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["nome"] == payload["nome"]
    assert created_data["status"] == "ATIVO"
    assert "id" in created_data
    associado_id = created_data["id"]

    # 2. Rejeição de CPF duplicado
    dup_res = await async_client.post("/api/v1/associados/", json=payload)
    assert dup_res.status_code == 400
    assert "Já existe um associado cadastrado com o CPF" in dup_res.json()["detail"]

    # 3. Consulta por ID
    get_res = await async_client.get(f"/api/v1/associados/{associado_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == associado_id

    # 4. Listagem
    list_res = await async_client.get("/api/v1/associados/")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
    assert len(list_res.json()["items"]) >= 1


@pytest.mark.asyncio
async def test_turnstile_whitelist_endpoint(async_client: AsyncClient):
    """Testa endpoint de sincronização da lista branca para a catraca física."""
    response = await async_client.get("/api/v1/catraca/whitelist")
    assert response.status_code == 200
    data = response.json()
    assert "total_authorized" in data
    assert "members" in data
    assert "guests" in data
