"""
Endpoints da API para diagnóstico, conexão via QR Code e testes de WhatsApp (Evolution API).
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.whatsapp_service import (
    get_whatsapp_provider,
    normalize_whatsapp_number,
)

router = APIRouter()


class WhatsAppSendTestRequest(BaseModel):
    phone: str = Field(..., description="Número do destinatário com DDD (ex: 11988887777)")
    message: str = Field(..., min_length=1, description="Texto da mensagem de teste")


@router.get("/status", summary="Verifica status da conexão da instância WhatsApp")
async def get_status() -> Dict[str, Any]:
    """Retorna o estado atual da conexão da instância com a rede do WhatsApp."""
    provider = get_whatsapp_provider()
    status_data = await provider.get_connection_status()

    instance_info = status_data.get("instance", {})
    state = instance_info.get("state", "unknown")
    instance_name = instance_info.get("instanceName", settings.WHATSAPP_INSTANCE_NAME)
    connected = (state == "open")

    return {
        "instance": instance_name,
        "state": state,
        "connected": connected,
        "provider": settings.WHATSAPP_PROVIDER,
        "api_url": settings.WHATSAPP_API_URL,
    }


@router.get("/qr", summary="Obtém o QR Code para conectar o WhatsApp")
async def get_qr(
    request: Request,
    accept: Optional[str] = Header(None)
) -> Any:
    """
    Retorna o QR Code para leitura no celular.
    Se acessado pelo navegador (Accept: text/html), exibe uma página visual moderna
    com auto-refresh que detecta a leitura do QR Code automaticamente.
    """
    provider = get_whatsapp_provider()
    status_data = await provider.get_connection_status()
    instance_info = status_data.get("instance", {})
    state = instance_info.get("state", "unknown")
    instance_name = instance_info.get("instanceName", settings.WHATSAPP_INSTANCE_NAME)

    qr_data = await provider.get_qr_code()
    base64_img = qr_data.get("base64")
    code = qr_data.get("code")

    is_html_request = accept and "text/html" in accept

    if not is_html_request:
        return {
            "instance": instance_name,
            "state": state,
            "connected": state == "open",
            "base64": base64_img,
            "code": code,
        }

    # Renderização HTML amigável para escaneamento no celular
    is_connected = (state == "open")
    qr_img_tag = (
        f'<img src="{base64_img}" alt="QR Code WhatsApp" style="width: 260px; height: 260px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;" />'
        if base64_img and not is_connected
        else ""
    )

    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conectar WhatsApp - Club Maravilha</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }}
        body {{
            background: #f8fafc;
            color: #0f172a;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            padding: 24px;
        }}
        .card {{
            background: #ffffff;
            border-radius: 20px;
            padding: 36px 32px;
            max-width: 440px;
            width: 100%;
            text-align: center;
            border: 1px solid #e2e8f0;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
        }}
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        .badge-open {{ background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }}
        .badge-connecting {{ background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }}
        .badge-close {{ background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }}
        h1 {{ font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }}
        p.subtitle {{ font-size: 14px; color: #64748b; margin-bottom: 24px; line-height: 1.5; }}
        .qr-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 20px 0;
            min-height: 270px;
        }}
        .steps {{
            background: #f1f5f9;
            border-radius: 12px;
            padding: 16px;
            text-align: left;
            margin-top: 20px;
            font-size: 13px;
            color: #334155;
            line-height: 1.6;
        }}
        .steps ol {{ padding-left: 18px; }}
        .btn {{
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: #0f172a;
            color: #fff;
            border-radius: 10px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            border: none;
        }}
        .btn:hover {{ background: #1e293b; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge {'badge-open' if is_connected else 'badge-connecting'}">
            <span>●</span> {'WhatsApp Conectado' if is_connected else f'Status: {state}'}
        </div>
        <h1>Conectar WhatsApp</h1>
        <p class="subtitle">Instância: <strong>{instance_name}</strong><br>
        Integração oficial Club Maravilha</p>

        <div class="qr-container">
            {
                '<div style="color: #059669; font-weight: 600; font-size: 16px;">'
                '🎉 Aparelho pareado e pronto para envio de notificações!'
                '</div>'
                if is_connected else
                (qr_img_tag if base64_img else '<p style="color: #64748b;">Carregando QR Code...</p>')
            }
        </div>

        {'<div class="steps"><ol>'
         '<li>Abra o <strong>WhatsApp</strong> no seu celular.</li>'
         '<li>Toque em <strong>Aparelhos conectados</strong>.</li>'
         '<li>Toque em <strong>Conectar aparelho</strong> e aponte para o QR Code acima.</li>'
         '</ol></div>' if not is_connected else ''}

        <button class="btn" onclick="window.location.reload();">🔄 Atualizar Tela</button>
    </div>

    <script>
        // Auto-refresh a cada 3 segundos caso não esteja conectado
        {'setTimeout(() => { fetch("/api/v1/whatsapp/status").then(r => r.json()).then(d => { if(d.connected) window.location.reload(); else setTimeout(() => window.location.reload(), 3000); }); }, 3000);' if not is_connected else ''}
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.post("/send-test", summary="Dispara uma mensagem de teste para um número de WhatsApp")
async def send_test_message(payload: WhatsAppSendTestRequest) -> Dict[str, Any]:
    """Envia uma mensagem de teste imediata para validar a entrega real no aparelho."""
    provider = get_whatsapp_provider()
    normalized_phone = normalize_whatsapp_number(payload.phone)

    result = await provider.send_message(normalized_phone, payload.message)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha no envio via provedor: {result.get('error', 'Desconhecido')}"
        )

    return result
