"""
Testes de integração assíncronos para o ciclo de vida de faturas e processamento de webhooks Pix em < 2s.
"""
from datetime import date
from decimal import Decimal
import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_full_invoice_and_instant_pix_webhook_flow(async_client: AsyncClient):
    """Testa geração de fatura Pix e liquidação instantânea via Webhook."""
    # 1. Cria um associado (inicialmente com status INADIMPLENTE para testar reativação)
    member_payload = {
        "nome": "Marcos Rogério",
        "cpf": "52998224725",
        "whatsapp": "11999990000",
        "email": "marcos@clubmaravilha.com"
    }
    member_res = await async_client.post("/api/v1/associados/", json=member_payload)
    assert member_res.status_code == 201
    member_id = member_res.json()["id"]

    # Altera associado para INADIMPLENTE
    await async_client.patch(f"/api/v1/associados/{member_id}", json={"status": "INADIMPLENTE"})

    # 2. Emite uma fatura Pix
    fatura_payload = {
        "associado_id": member_id,
        "referencia_mes": "2026-09",
        "valor_base": "150.00",
        "valor_convidados_excedentes": "35.00",
        "valor_desconto": "0.00",
        "valor_total": "185.00",
        "data_vencimento": "2026-09-10",
        "forma_pagamento": "PIX"
    }
    fatura_res = await async_client.post("/api/v1/faturas/", json=fatura_payload)
    assert fatura_res.status_code == 201
    fatura_data = fatura_res.json()
    assert fatura_data["status"] == "PENDENTE"
    assert fatura_data["txid"] is not None
    assert fatura_data["pix_copia_cola"] is not None
    assert fatura_data["pix_qr_code_url"] is not None
    txid = fatura_data["txid"]
    fatura_id = fatura_data["id"]

    # 3. Dispara Webhook de Pagamento Instantâneo (Simulando Gateway Pix em 2s)
    webhook_payload = {
        "txid": txid,
        "valor": "185.00",
        "horario": "2026-09-12T19:00:00.123Z",
        "endToEndId": "E000000002026091219000001",
        "pagador": {
            "nome": "Marcos Rogério",
            "cpf": "52998224725"
        }
    }
    headers = {"X-Webhook-Secret": settings.PIX_WEBHOOK_SECRET}
    webhook_res = await async_client.post("/api/v1/webhooks/pix", json=webhook_payload, headers=headers)
    assert webhook_res.status_code == 200
    assert webhook_res.json()["status"] == "success"

    # 4. Verifica se a fatura foi marcada como PAGO
    get_fat_res = await async_client.get(f"/api/v1/faturas/{fatura_id}")
    assert get_fat_res.status_code == 200
    updated_fat = get_fat_res.json()
    assert updated_fat["status"] == "PAGO"
    assert updated_fat["data_pagamento"] is not None
    assert updated_fat["metadata_webhook"] is not None

    # 5. Verifica se o associado foi automaticamente reativado para ATIVO
    get_mem_res = await async_client.get(f"/api/v1/associados/{member_id}")
    assert get_mem_res.status_code == 200
    assert get_mem_res.json()["status"] == "ATIVO"

    # 6. Teste de Idempotência: reenvio do mesmo webhook
    repeat_res = await async_client.post("/api/v1/webhooks/pix", json=webhook_payload, headers=headers)
    assert repeat_res.status_code == 200
    assert "já liquidada" in repeat_res.json()["message"].lower()


@pytest.mark.asyncio
async def test_webhook_security_rejection(async_client: AsyncClient):
    """Rejeita webhooks sem credencial válida ou com txid inexistente."""
    # 1. Secret inválido
    res_unauth = await async_client.post(
        "/api/v1/webhooks/pix",
        json={"txid": "CM-TESTE"},
        headers={"X-Webhook-Secret": "segredo_incorreto"}
    )
    assert res_unauth.status_code == 401

    # 2. Txid inexistente
    res_not_found = await async_client.post(
        "/api/v1/webhooks/pix",
        json={"txid": "CM-INEXISTENTE-99999"},
        headers={"X-Webhook-Secret": settings.PIX_WEBHOOK_SECRET}
    )
    assert res_not_found.status_code == 404


@pytest.mark.asyncio
async def test_cancelar_fatura(async_client: AsyncClient):
    """Testa cancelamento de uma fatura pendente."""
    # Cria associado
    mem = await async_client.post("/api/v1/associados/", json={
        "nome": "Associado Fatura Cancelada",
        "cpf": "11144477735",
        "whatsapp": "+5511977770000",
        "email": "cancelado@club.com"
    })
    member_id = mem.json()["id"]

    # Cria fatura
    fat = await async_client.post("/api/v1/faturas/", json={
        "associado_id": member_id,
        "referencia_mes": "2026-10",
        "valor_base": "150.00",
        "valor_total": "150.00",
        "data_vencimento": "2026-10-10",
        "forma_pagamento": "PIX"
    })
    fat_id = fat.json()["id"]

    # Cancela fatura
    cancel_res = await async_client.post(f"/api/v1/faturas/{fat_id}/cancelar")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELADO"
