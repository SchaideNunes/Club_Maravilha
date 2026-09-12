"""
Testes de integração para a Régua Diária de Cobrança e confirmação instantânea de pagamento via WhatsApp.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.services.whatsapp_service import MockWhatsAppProvider
from app.services.whatsapp_queue_service import get_global_whatsapp_queue


@pytest.mark.asyncio
async def test_endpoint_executar_regua_cobranca(async_client: AsyncClient, db_session: AsyncSession):
    # Cria associado e fatura para D-0
    socio = Associado(
        nome="Associado Régua Endpoint",
        cpf="555.555.555-55",
        whatsapp="+5511955554444",
        email="regua_endpoint@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    hoje = date(2026, 9, 10)
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=hoje,
        status=StatusFatura.PENDENTE,
        pix_copia_cola="pix_copia_cola_endpoint"
    )
    db_session.add(fatura)
    await db_session.commit()

    # Chama endpoint de execução da régua
    res = await async_client.post(
        "/api/v1/faturas/executar-regua",
        params={"data_referencia": "2026-09-10"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["d_zero_enviados"] == 1
    assert data["total_enfileirados"] >= 1

    # Verifica se a fatura foi marcada
    await db_session.refresh(fatura)
    assert fatura.notificado_d_zero_em is not None


@pytest.mark.asyncio
async def test_instant_whatsapp_receipt_on_pix_payment(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Cria associado inadimplente
    socio = Associado(
        nome="Mariana Recibo",
        cpf="666.666.666-66",
        whatsapp="+5511966667777",
        email="mariana_recibo@clube.com",
        status=StatusAssociado.INADIMPLENTE
    )
    db_session.add(socio)
    await db_session.commit()

    # 2. Cria fatura pendente com txid
    txid = "TXID_RECIBO_WPP_TEST_999"
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 9, 10),
        status=StatusFatura.PENDENTE,
        txid=txid,
        pix_copia_cola="pix_recibo_instantaneo"
    )
    db_session.add(fatura)
    await db_session.commit()

    # 3. Dispara Webhook de liquidação instantânea
    webhook_payload = {
        "evento": "pix_recebido",
        "txid": txid,
        "valor": "150.00",
        "horario": "2026-09-12T16:00:00Z"
    }

    res = await async_client.post(
        "/api/v1/webhooks/pix",
        json=webhook_payload,
        headers={"X-Webhook-Secret": "mock_webhook_secret_dev"}
    )
    assert res.status_code == 200

    # 4. Verifica se associado foi reativado e notificação pós-pagamento registrada
    await db_session.refresh(fatura)
    await db_session.refresh(socio)
    assert fatura.status == StatusFatura.PAGO
    assert fatura.notificado_pos_pagamento_em is not None
    assert socio.status == StatusAssociado.ATIVO
