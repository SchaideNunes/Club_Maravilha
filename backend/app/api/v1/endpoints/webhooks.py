"""
Endpoint de Webhook para confirmação instantânea de pagamentos Pix (< 2-3s).
"""
from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura

router = APIRouter()


@router.post("/pix", status_code=status.HTTP_200_OK)
async def webhook_pix_payment(
    request: Request,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Recebe notificação instantânea do gateway Pix (Efí / Asaas / Mercado Pago).
    Atualiza a fatura para PAGO em menos de 2 segundos, reativa associado se inadimplente
    e agenda disparo de recibo pelo WhatsApp.
    """
    # TODO(FASE-3-PIX): Validar assinatura criptográfica HMAC nos headers do request
    
    # Exemplo genérico de extração de txid ou pix_id do payload
    txid = payload.get("txid") or payload.get("pix", [{}])[0].get("txid")
    if not txid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload de webhook inválido: txid ausente."
        )

    # Localiza a fatura vinculada
    result = await db.execute(select(Fatura).where(Fatura.txid == txid))
    fatura = result.scalar_one_or_none()
    if not fatura:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fatura com txid {txid} não encontrada."
        )

    # Atualiza status da fatura
    fatura.status = StatusFatura.PAGO
    fatura.data_pagamento = datetime.now(timezone.utc)
    fatura.metadata_webhook = payload
    
    # Se o associado estava com status INADIMPLENTE, reativa para ATIVO
    associado_res = await db.execute(select(Associado).where(Associado.id == fatura.associado_id))
    associado = associado_res.scalar_one_or_none()
    if associado and associado.status == StatusAssociado.INADIMPLENTE:
        associado.status = StatusAssociado.ATIVO

    await db.commit()

    # TODO(FASE-2-CATRACA): Enviar comando de sincronização imediata para a catraca facial
    # TODO(FASE-4-WHATSAPP): Enviar recibo automático e aviso de liberação no WhatsApp do associado

    return {"status": "success", "message": "Fatura liquidada e associado liberado com sucesso."}
