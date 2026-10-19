"""
Testes unitários para o serviço de WhatsApp e provedores desacoplados.

Feature 4: o provedor legado Evolution API foi removido (substituído pelo motor Baileys próprio,
coberto em test_baileys_provider.py); o Mock passa a seguir o contrato normalizado de status.
"""
import pytest
from datetime import date
from decimal import Decimal
from app.services.whatsapp_service import (
    WhatsAppProvider,
    MockWhatsAppProvider,
    BaileysWhatsAppProvider,
    WhatsAppMessageBuilder,
    get_whatsapp_provider,
)


def test_whatsapp_message_builder_templates():
    nome = "Carlos Eduardo"
    valor = Decimal("150.00")
    vencimento = date(2026, 9, 15)
    pix = "00020126580014br.gov.bcb.pix..."

    # 1. D-3
    msg_d3 = WhatsAppMessageBuilder.build_d_minus_3(nome, valor, vencimento)
    assert "Carlos Eduardo" in msg_d3
    assert "150.00" in msg_d3
    assert "15/09/2026" in msg_d3
    assert "3 dias" in msg_d3

    # 2. D-0
    msg_d0 = WhatsAppMessageBuilder.build_d_zero(nome, valor, vencimento, pix)
    assert "vence hoje" in msg_d0
    assert pix in msg_d0
    assert "Pix Copia e Cola" in msg_d0

    # 3. Pós-Pagamento
    msg_pago = WhatsAppMessageBuilder.build_pos_pagamento(nome, valor, "2026-09")
    assert "confirmamos o pagamento" in msg_pago.lower()
    assert "liberado" in msg_pago.lower()
    assert "catraca" in msg_pago.lower()

    # 4. D+3
    msg_d3_plus = WhatsAppMessageBuilder.build_d_plus_3(nome, valor, vencimento, pix)
    assert "vencida há 3 dias" in msg_d3_plus
    assert pix in msg_d3_plus

    # 5. D+7
    msg_d7_plus = WhatsAppMessageBuilder.build_d_plus_7(nome, valor, vencimento, pix)
    assert "vencida há 7 dias" in msg_d7_plus
    assert "bloqueado" in msg_d7_plus.lower()
    assert pix in msg_d7_plus


@pytest.mark.asyncio
async def test_mock_whatsapp_provider_send():
    provider = MockWhatsAppProvider()
    assert len(provider.sent_messages) == 0

    response = await provider.send_message(
        phone="+55 (11) 98888-7777",
        message="Mensagem de teste"
    )

    assert response["status"] == "success"
    assert response["provider"] == "MockWhatsAppProvider"
    assert len(provider.sent_messages) == 1
    
    sent = provider.sent_messages[0]
    # Garante normalização de telefone (apenas números com DDI +55)
    assert sent["phone"] == "5511988887777"
    assert sent["message"] == "Mensagem de teste"


def test_get_whatsapp_provider_factory():
    provider = get_whatsapp_provider("MOCK")
    assert isinstance(provider, MockWhatsAppProvider)

    provider_baileys = get_whatsapp_provider("BAILEYS")
    assert isinstance(provider_baileys, BaileysWhatsAppProvider)


@pytest.mark.asyncio
async def test_mock_whatsapp_provider_status_qr_logout_restart():
    """Feature 4: o Mock segue o contrato normalizado da interface (status CONECTADO/DESCONECTADO/AGUARDANDO_QRCODE)."""
    provider = MockWhatsAppProvider()

    status = await provider.get_connection_status()
    assert status["status"] == "CONECTADO"

    qr = await provider.get_qr_code()
    assert qr["status"] == "CONECTADO"
    assert qr["qrcode"] is None

    assert (await provider.logout())["status"] == "DESCONECTADO"
    assert (await provider.restart())["status"] in ("CONECTADO", "AGUARDANDO_QRCODE")
