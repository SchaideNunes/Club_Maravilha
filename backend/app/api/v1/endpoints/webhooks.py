"""
Endpoint de Webhook para confirmação instantânea de pagamentos Pix (< 2s).
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.fatura_service import FaturaService

router = APIRouter()


@router.post("/pix", status_code=status.HTTP_200_OK)
async def webhook_pix_payment(
    request: Request,
    payload: Dict[str, Any],
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret"),
    token: Optional[str] = Query(None, description="Token de autenticação alternativo via query string"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Recebe notificação instantânea do gateway Pix (Efí / Asaas / Mercado Pago).
    Valida a assinatura de segurança, atualiza a fatura para PAGO em menos de 2 segundos
    e reativa o associado caso estivesse com status INADIMPLENTE.
    """
    secret_token = x_webhook_secret or token
    service = FaturaService(db)
    return await service.process_pix_webhook(payload, secret_token)
