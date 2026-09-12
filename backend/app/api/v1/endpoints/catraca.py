"""
Endpoints da API v1 para Integração com a Catraca Facial e Acesso (Rede Local).
Fornece sincronização de Lista Branca (Offline Whitelist), trigger imediato e recepção de eventos.
"""
from datetime import date
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.catraca_service import CatracaService

router = APIRouter()


@router.get("/whitelist", status_code=status.HTTP_200_OK)
async def get_turnstile_whitelist(
    data: Optional[date] = Query(None, description="Data da whitelist (padrão: hoje)"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retorna a lista de pessoas autorizadas para acesso:
    1. Associados com status ATIVO que possuem facial_id e sem mensalidades vencidas.
    2. Convidados com status EMITIDO cuja data_visita seja a data consultada (com qr_token).
    A catraca faz download periódico deste payload para sua memória flash/RAM offline.
    """
    service = CatracaService(db)
    return await service.get_whitelist(data_consulta=data)


@router.post("/sync", status_code=status.HTTP_200_OK)
async def trigger_turnstile_sync(
    reason: str = Query("manual_trigger", description="Motivo do disparo de sincronização"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Dispara sinal de sincronização imediata para o leitor/catraca facial.
    Chamado automaticamente no pós-pagamento Pix ou sob demanda.
    """
    service = CatracaService(db)
    return await service.notify_turnstile_sync(reason=reason)


@router.post("/events", status_code=status.HTTP_200_OK)
async def receive_turnstile_event(
    event: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Recebe evento de passagem física na catraca:
    - QR Code de visitante: valida e marca o convite como UTILIZADO com data/hora de check-in.
    - Facial ID de sócio: audita passagem.
    """
    service = CatracaService(db)
    return await service.process_turnstile_event(event)
