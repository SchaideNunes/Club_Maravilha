"""
Endpoints da API v1 para Gestão de Faturas, Mensalidades e Pix Dinâmico.
"""
import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.fatura import StatusFatura
from app.schemas.fatura import BillingExecutionReport, FaturaCreate, FaturaResponse
from app.services.billing_engine_service import BillingEngineService
from app.services.fatura_service import FaturaService

router = APIRouter()


@router.get("/", response_model=List[FaturaResponse])
async def list_faturas(
    associado_id: Optional[uuid.UUID] = Query(None, description="Filtrar por associado"),
    status: Optional[StatusFatura] = Query(None, description="Filtrar por status"),
    referencia_mes: Optional[str] = Query(None, description="Filtrar por mês AAAA-MM"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[FaturaResponse]:
    """Lista faturas com filtros por associado, status e mês de referência."""
    service = FaturaService(db)
    return await service.list_faturas(
        associado_id=associado_id,
        status_filter=status,
        referencia_mes=referencia_mes,
        skip=skip,
        limit=limit
    )


@router.post("/", response_model=FaturaResponse, status_code=status.HTTP_201_CREATED)
async def create_fatura(
    data: FaturaCreate,
    db: AsyncSession = Depends(get_db)
) -> FaturaResponse:
    """
    Cria uma nova fatura/mensalidade com geração de Pix dinâmico (txid exclusivo e QR Code).
    """
    service = FaturaService(db)
    return await service.create_fatura(data)


@router.post("/executar-regua", response_model=BillingExecutionReport)
async def executar_regua_cobranca(
    data_referencia: Optional[date] = Query(
        None,
        description="Data de referência para disparo da régua (padrão: hoje)"
    ),
    db: AsyncSession = Depends(get_db)
) -> BillingExecutionReport:
    """
    Executa sob demanda ou via scheduler a régua de cobrança diária:
    D-3 (aviso amigável), D-0 (Pix Copia e Cola matinal),
    D+3 (cobrança de atraso) e D+7 (alerta de bloqueio de catraca e transição para inadimplente).
    Todas as mensagens são enfileiradas de forma segura com jitter anti-ban.
    """
    engine = BillingEngineService(session=db)
    return await engine.processar_regua_diaria(data_referencia=data_referencia)


@router.get("/{fatura_id}", response_model=FaturaResponse)
async def get_fatura(
    fatura_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> FaturaResponse:
    """Recupera detalhes de uma fatura específica incluindo o Pix Copia e Cola."""
    service = FaturaService(db)
    return await service.get_by_id(fatura_id)


@router.post("/{fatura_id}/cancelar", response_model=FaturaResponse)
async def cancel_fatura(
    fatura_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Cancela uma fatura que ainda esteja com status PENDENTE."""
    service = FaturaService(db)
    return await service.cancel_fatura(fatura_id)


@router.post("/{fatura_id}/simular-pagamento", response_model=Dict[str, Any])
async def simular_pagamento_pix(
    fatura_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Simula a liquidação instantânea de uma fatura Pix em ambiente de teste ou homologação.
    Dispara o fluxo real de produção:
    1. Baixa da fatura no PostgreSQL para status PAGO.
    2. Gravação da data/hora exata do pagamento.
    3. Reativação automática do associado (se inadimplente -> ATIVO).
    4. Enfileiramento com PRIORIDADE MÁXIMA do recibo digital via WhatsApp.
    5. Disparo de sincronização imediata com a catraca física.
    """
    service = FaturaService(db)
    fatura = await service.get_by_id(fatura_id)
    payload = {
        "evento": "pix_recebido_simulado",
        "txid": fatura.txid,
        "valor": str(fatura.valor_total),
    }
    return await service.process_pix_webhook(payload, secret_token=settings.PIX_WEBHOOK_SECRET)
