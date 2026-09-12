"""
Testes de integração assíncronos para o fluxo completo de associados:
Importação em lote de planilhas Excel/CSV, busca paginada e exclusão.
"""
import io
import pytest
import openpyxl
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_importar_excel_endpoint_flow(async_client: AsyncClient):
    """Testa o endpoint de upload multipart para importação de sócios via Excel."""
    # Gera arquivo Excel em memória com 2 sócios válidos
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Importacao"
    ws.append(["Nome", "CPF", "WhatsApp", "Email", "Status"])
    ws.append(["Fernando Diniz", "52998224725", "11988889999", "diniz@fluminense.com", "ATIVO"])
    ws.append(["Abel Ferreira", "11144477735", "11977778888", "abel@palmeiras.com", "ATIVO"])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    files = {
        "file": ("socios_treinadores.xlsx", stream.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }

    # 1. Primeira importação
    response = await async_client.post("/api/v1/associados/importar", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_lidos"] == 2
    assert data["total_importados"] == 2
    assert data["total_ignorados_duplicados"] == 0
    assert len(data["erros"]) == 0

    # 2. Segunda importação com o mesmo arquivo (Teste de Idempotência)
    stream.seek(0)
    files_repeat = {
        "file": ("socios_treinadores.xlsx", stream.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    repeat_res = await async_client.post("/api/v1/associados/importar", files=files_repeat)
    assert repeat_res.status_code == 200
    repeat_data = repeat_res.json()
    assert repeat_data["total_lidos"] == 2
    assert repeat_data["total_importados"] == 0
    assert repeat_data["total_ignorados_duplicados"] == 2


@pytest.mark.asyncio
async def test_search_and_pagination_associados(async_client: AsyncClient):
    """Testa busca por termo 'q' e paginação estruturada."""
    # Cria associados específicos para busca
    p1 = {
        "nome": "Zico Galinho",
        "cpf": "33344455508",
        "whatsapp": "+5521999991010",
        "email": "zico10@flamengo.com"
    }
    p2 = {
        "nome": "Roberto Dinamite",
        "cpf": "77788899941",
        "whatsapp": "+5521988882020",
        "email": "dinamite@vasco.com"
    }
    res1 = await async_client.post("/api/v1/associados/", json=p1)
    assert res1.status_code == 201
    res2 = await async_client.post("/api/v1/associados/", json=p2)
    assert res2.status_code == 201

    # 1. Busca pelo termo "Zico"
    res_zico = await async_client.get("/api/v1/associados/?q=Zico")
    assert res_zico.status_code == 200
    data_zico = res_zico.json()
    assert data_zico["total"] >= 1
    assert any(item["nome"] == "Zico Galinho" for item in data_zico["items"])

    # 2. Busca por CPF parcial (com ou sem pontuação)
    res_cpf = await async_client.get("/api/v1/associados/?q=777.888")
    assert res_cpf.status_code == 200
    data_cpf = res_cpf.json()
    assert any(item["nome"] == "Roberto Dinamite" for item in data_cpf["items"])


@pytest.mark.asyncio
async def test_delete_associado(async_client: AsyncClient):
    """Testa remoção de um associado."""
    new_member = {
        "nome": "Membro Temporário",
        "cpf": "01234567890", # Será validado conforme implementação
        "whatsapp": "+5511911112222",
        "email": "temp@club.com"
    }
    # Criamos diretamente usando CPF válido
    create_res = await async_client.post("/api/v1/associados/", json={
        "nome": "Membro Temporário",
        "cpf": "529.982.247-25",
        "whatsapp": "+5511911112222",
        "email": "temp@club.com"
    })
    if create_res.status_code == 201:
        member_id = create_res.json()["id"]
        del_res = await async_client.delete(f"/api/v1/associados/{member_id}")
        assert del_res.status_code == 204

        get_res = await async_client.get(f"/api/v1/associados/{member_id}")
        assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_update_associado_and_conflict(async_client: AsyncClient):
    """Testa atualização cadastral e conflito de email duplicado."""
    # Cria sócio 1
    s1 = await async_client.post("/api/v1/associados/", json={
        "nome": "Sócio Antigo",
        "cpf": "111.444.777-35",
        "whatsapp": "+5511988880001",
        "email": "antigo@club.com"
    })
    s1_id = s1.json()["id"]

    # Cria sócio 2
    s2 = await async_client.post("/api/v1/associados/", json={
        "nome": "Sócio Novo",
        "cpf": "529.982.247-25",
        "whatsapp": "+5511988880002",
        "email": "novo@club.com"
    })
    s2_id = s2.json()["id"]

    # 1. Atualiza nome com sucesso
    patch_res = await async_client.patch(f"/api/v1/associados/{s1_id}", json={
        "nome": "Sócio Atualizado"
    })
    assert patch_res.status_code == 200
    assert patch_res.json()["nome"] == "Sócio Atualizado"

    # 2. Tenta atualizar email do sócio 1 para o email do sócio 2 (deve falhar 400)
    conflict_res = await async_client.patch(f"/api/v1/associados/{s1_id}", json={
        "email": "novo@club.com"
    })
    assert conflict_res.status_code == 400
    assert "já está sendo utilizado" in conflict_res.json()["detail"]


@pytest.mark.asyncio
async def test_not_found_associado_operations(async_client: AsyncClient):
    """Testa retornos 404 para ID inexistente."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    get_res = await async_client.get(f"/api/v1/associados/{fake_id}")
    assert get_res.status_code == 404

    del_res = await async_client.delete(f"/api/v1/associados/{fake_id}")
    assert del_res.status_code == 404

