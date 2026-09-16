"""
Testes de integração para os endpoints da API de WhatsApp e conexão de instâncias.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_whatsapp_status_endpoint(async_client: AsyncClient):
    """Verifica consulta de status da instância do WhatsApp."""
    with patch("app.services.whatsapp_service.EvolutionApiWhatsAppProvider.get_connection_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {
            "instance": {"instanceName": "club_maravilha", "state": "open"}
        }

        response = await async_client.get("/api/v1/whatsapp/status")
        assert response.status_code == 200
        data = response.json()
        assert data["instance"] == "club_maravilha"
        assert data["state"] == "open"
        assert data["connected"] is True


@pytest.mark.asyncio
async def test_whatsapp_status_endpoint_disconnected(async_client: AsyncClient):
    """Verifica consulta de status quando a instância está desconectada."""
    with patch("app.services.whatsapp_service.EvolutionApiWhatsAppProvider.get_connection_status", new_callable=AsyncMock) as mock_status:
        mock_status.return_value = {
            "instance": {"instanceName": "club_maravilha", "state": "close"}
        }

        response = await async_client.get("/api/v1/whatsapp/status")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "close"
        assert data["connected"] is False


@pytest.mark.asyncio
async def test_whatsapp_qr_endpoint_html(async_client: AsyncClient):
    """Verifica renderização da tela com QR Code para leitura no celular."""
    with patch("app.services.whatsapp_service.EvolutionApiWhatsAppProvider.get_qr_code", new_callable=AsyncMock) as mock_qr, \
         patch("app.services.whatsapp_service.EvolutionApiWhatsAppProvider.get_connection_status", new_callable=AsyncMock) as mock_status:
        
        mock_status.return_value = {"instance": {"instanceName": "club_maravilha", "state": "connecting"}}
        mock_qr.return_value = {
            "base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "code": "mock_pairing_code"
        }

        response = await async_client.get("/api/v1/whatsapp/qr", headers={"Accept": "text/html"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        html = response.text
        assert "Club Maravilha" in html
        assert "data:image/png;base64" in html
        assert "QR Code" in html


@pytest.mark.asyncio
async def test_whatsapp_send_test_endpoint(async_client: AsyncClient):
    """Verifica envio de mensagem de teste avulsa."""
    with patch("app.services.whatsapp_service.EvolutionApiWhatsAppProvider.send_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {
            "status": "success",
            "provider": "EvolutionApiWhatsAppProvider",
            "phone": "5511999998888",
            "message_id": "TEST_MSG_456"
        }

        payload = {
            "phone": "11999998888",
            "message": "Mensagem de teste do Club Maravilha"
        }

        response = await async_client.post("/api/v1/whatsapp/send-test", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["phone"] == "5511999998888"
        assert data["message_id"] == "TEST_MSG_456"
        mock_send.assert_called_once_with("5511999998888", "Mensagem de teste do Club Maravilha")
