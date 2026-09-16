"""
Testes unitários para o serviço de WhatsApp e provedores desacoplados.
"""
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import httpx
from app.services.whatsapp_service import (
    WhatsAppProvider,
    MockWhatsAppProvider,
    EvolutionApiWhatsAppProvider,
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


@pytest.mark.asyncio
async def test_evolution_api_provider_send():
    provider = EvolutionApiWhatsAppProvider(
        api_url="http://evolution-api:8080",
        api_key="secret_token_123",
        instance_name="clube_instancia"
    )

    mock_response = httpx.Response(
        200,
        json={"key": {"id": "WPP_MSG_123"}, "status": "PENDING"},
        request=httpx.Request("POST", "http://test")
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        res = await provider.send_message(
            phone="11977776666",
            message="Teste Evolution API"
        )

        assert res["status"] == "success"
        assert res["message_id"] == "WPP_MSG_123"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://evolution-api:8080/message/sendText/clube_instancia"
        assert kwargs["headers"]["apikey"] == "secret_token_123"
        assert kwargs["json"]["number"] == "5511977776666"
        assert kwargs["json"]["text"] == "Teste Evolution API"


def test_get_whatsapp_provider_factory():
    provider = get_whatsapp_provider("MOCK")
    assert isinstance(provider, MockWhatsAppProvider)

    provider_evo = get_whatsapp_provider("EVOLUTION_API")
    assert isinstance(provider_evo, EvolutionApiWhatsAppProvider)


@pytest.mark.asyncio
async def test_mock_whatsapp_provider_instance_and_qr():
    provider = MockWhatsAppProvider()
    status = await provider.get_connection_status()
    assert status["instance"]["state"] == "open"

    created = await provider.create_instance_if_not_exists()
    assert created["instance"]["status"] == "created"

    qr = await provider.get_qr_code()
    assert "data:image/png;base64" in qr["base64"]


@pytest.mark.asyncio
async def test_evolution_api_provider_status_and_qr():
    provider = EvolutionApiWhatsAppProvider(
        api_url="http://evolution-api:8080",
        api_key="secret_token_123",
        instance_name="clube_instancia"
    )

    # 1. Connection Status
    mock_status_response = httpx.Response(
        200,
        json={"instance": {"instanceName": "clube_instancia", "state": "open"}},
        request=httpx.Request("GET", "http://test")
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_status_response
        res = await provider.get_connection_status()
        assert res["instance"]["state"] == "open"
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "http://evolution-api:8080/instance/connectionState/clube_instancia"

    # 2. Create Instance (Already Exists 409)
    mock_create_response = httpx.Response(
        409,
        json={"error": "Instance already exists"},
        request=httpx.Request("POST", "http://test")
    )
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_create_response
        res_create = await provider.create_instance_if_not_exists()
        assert res_create["status"] == "exists"

    # 3. QR Code Connect
    mock_qr_response = httpx.Response(
        200,
        json={"base64": "data:image/png;base64,mockqr", "code": "code123"},
        request=httpx.Request("GET", "http://test")
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch.object(provider, "create_instance_if_not_exists", new_callable=AsyncMock) as mock_create:
        mock_get.return_value = mock_qr_response
        res_qr = await provider.get_qr_code()
        assert res_qr["code"] == "code123"
        assert res_qr["base64"] == "data:image/png;base64,mockqr"
        mock_create.assert_called_once()

