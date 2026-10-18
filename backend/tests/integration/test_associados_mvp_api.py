"""
Testes de integração da API de Associados com os campos do MVP:
dia_vencimento, WhatsApp no padrão Baileys e contador de convites do mês.
"""
import csv
import io
from datetime import date, timedelta
import pytest
from httpx import AsyncClient
from app.core.config import settings

CPF_VALIDO_1 = "529.982.247-25"
CPF_VALIDO_2 = "111.444.777-35"
CPF_VALIDO_3 = "123.456.789-09"


def _payload(**extra) -> dict:
    return {
        "nome": "Maria Maravilha",
        "cpf": CPF_VALIDO_1,
        "whatsapp": "(75) 99999-9999",
        "email": "maria@maravilha.com",
        **extra,
    }


async def _criar_associado(client: AsyncClient, **extra) -> dict:
    res = await client.post("/api/v1/associados/", json=_payload(**extra))
    assert res.status_code == 201, res.text
    return res.json()


async def test_post_higieniza_whatsapp_e_persiste_dia_vencimento(async_client: AsyncClient):
    criado = await _criar_associado(async_client, dia_vencimento=20)

    assert criado["whatsapp"] == "5575999999999"
    assert criado["dia_vencimento"] == 20
    assert criado["convidados_usados_mes"] == 0

    lido = (await async_client.get(f"/api/v1/associados/{criado['id']}")).json()
    assert lido["whatsapp"] == "5575999999999"
    assert lido["dia_vencimento"] == 20


async def test_post_sem_dia_vencimento_usa_padrao_das_configuracoes(async_client: AsyncClient):
    criado = await _criar_associado(async_client)
    assert criado["dia_vencimento"] == settings.DIA_VENCIMENTO_PADRAO


@pytest.mark.parametrize("dia", [0, 32])
async def test_post_dia_vencimento_invalido_retorna_422(async_client: AsyncClient, dia):
    res = await async_client.post("/api/v1/associados/", json=_payload(dia_vencimento=dia))
    assert res.status_code == 422


async def test_post_whatsapp_invalido_retorna_422(async_client: AsyncClient):
    res = await async_client.post("/api/v1/associados/", json=_payload(whatsapp="+1 555 123 4567"))
    assert res.status_code == 422


async def test_patch_atualiza_dia_vencimento_e_higieniza_whatsapp(async_client: AsyncClient):
    criado = await _criar_associado(async_client)

    res = await async_client.patch(
        f"/api/v1/associados/{criado['id']}",
        json={"dia_vencimento": 5, "whatsapp": "+55 (11) 98888-7777"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["dia_vencimento"] == 5
    assert res.json()["whatsapp"] == "5511988887777"


@pytest.mark.parametrize("campo", ["dia_vencimento", "whatsapp"])
async def test_patch_rejeita_null_em_campos_obrigatorios(async_client: AsyncClient, campo):
    criado = await _criar_associado(async_client)

    res = await async_client.patch(f"/api/v1/associados/{criado['id']}", json={campo: None})
    assert res.status_code == 422


async def test_convidados_usados_mes_exposto_em_detalhe_listagem_e_patch(async_client: AsyncClient):
    """Conta só os convites do mês corrente, descartando os cancelados e os de outros meses."""
    criado = await _criar_associado(async_client)
    hoje = date.today()
    mes_anterior = hoje.replace(day=1) - timedelta(days=1)

    ids_hoje = []
    for i in range(3):
        res = await async_client.post("/api/v1/convidados/", json={
            "associado_titular_id": criado["id"],
            "nome": f"Convidado Hoje {i}",
            "data_visita": hoje.isoformat(),
        })
        assert res.status_code == 201, res.text
        ids_hoje.append(res.json()["id"])
    res = await async_client.post("/api/v1/convidados/", json={
        "associado_titular_id": criado["id"],
        "nome": "Convidado Mes Anterior",
        "data_visita": mes_anterior.isoformat(),
    })
    assert res.status_code == 201, res.text
    assert (await async_client.post(f"/api/v1/convidados/{ids_hoje[0]}/cancelar")).status_code == 200

    detalhe = (await async_client.get(f"/api/v1/associados/{criado['id']}")).json()
    assert detalhe["convidados_usados_mes"] == 2

    listagem = (await async_client.get("/api/v1/associados/?q=Maria")).json()
    assert listagem["items"][0]["convidados_usados_mes"] == 2

    atualizado = await async_client.patch(f"/api/v1/associados/{criado['id']}", json={"dia_vencimento": 15})
    assert atualizado.status_code == 200
    assert atualizado.json()["convidados_usados_mes"] == 2


async def test_importacao_reporta_whatsapp_invalido_como_erro_da_linha(async_client: AsyncClient):
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";")
    escritor.writerow(["Nome", "CPF", "WhatsApp", "Email"])
    escritor.writerow(["Socio Valido", CPF_VALIDO_1, "(11) 98888-7777", "valido@club.com"])
    escritor.writerow(["Socio Estrangeiro", CPF_VALIDO_2, "+1 555 123 4567", "estrangeiro@club.com"])
    escritor.writerow(["Socio Curto", CPF_VALIDO_3, "12345", "curto@club.com"])
    conteudo = buffer.getvalue().encode("utf-8")

    res = await async_client.post(
        "/api/v1/associados/importar",
        files={"file": ("socios.csv", conteudo, "text/csv")},
    )
    assert res.status_code == 200, res.text
    resultado = res.json()
    assert resultado["total_lidos"] == 3
    assert resultado["total_importados"] == 1
    assert sorted(erro["linha"] for erro in resultado["erros"]) == [3, 4]
    assert all(erro["campo"] == "whatsapp" for erro in resultado["erros"])

    importado = (await async_client.get("/api/v1/associados/?q=Valido")).json()["items"][0]
    assert importado["whatsapp"] == "5511988887777"
    assert importado["dia_vencimento"] == settings.DIA_VENCIMENTO_PADRAO
