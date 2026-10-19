"""
Endpoints da API v1 para Gestão de Faturas, Mensalidades, Geração Mensal e Baixa Manual.
"""
from datetime import date
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import hoje_clube
from app.core.config import settings
from app.core.database import get_db
from app.models.fatura import StatusFatura
from app.schemas.fatura import (
    BillingExecutionReport,
    FaturaBaixaManual,
    FaturaCreate,
    FaturaResponse,
    GeracaoFaturasRequest,
    GeracaoFaturasResponse,
    MarcarAtrasadasResponse,
    PaginatedFaturasResponse,
)
from app.services.billing_engine_service import BillingEngineService
from app.services.fatura_service import FaturaService

router = APIRouter()


@router.get("/", response_model=PaginatedFaturasResponse)
async def list_faturas(
    referencia_mes: Optional[str] = Query(None, description="Filtrar por mês AAAA-MM"),
    status: Optional[StatusFatura] = Query(None, description="Filtrar por status"),
    q: Optional[str] = Query(None, description="Busca por nome ou CPF do associado"),
    associado_id: Optional[uuid.UUID] = Query(None, description="Filtrar por associado"),
    page: int = Query(1, ge=1, description="Número da página (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Tamanho da página"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedFaturasResponse:
    """Lista faturas com filtros por associado, status, mês e busca textual paginada."""
    service = FaturaService(db)
    return await service.list_painel_faturas(
        referencia_mes=referencia_mes,
        status_filter=status,
        q=q,
        associado_id=associado_id,
        page=page,
        page_size=page_size,
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


@router.post("/gerar-mes", response_model=GeracaoFaturasResponse)
async def gerar_faturas_mes(
    payload: Optional[GeracaoFaturasRequest] = Body(None),
    db: AsyncSession = Depends(get_db)
) -> GeracaoFaturasResponse:
    """
    Gera faturas mensais em lote para todos os associados elegíveis do clube.
    Mês padrão: mês corrente do clube.
    """
    ref_mes = payload.referencia_mes if payload else None
    service = FaturaService(db)
    try:
        return await service.gerar_faturas_mes(ref_mes)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        )


@router.post("/marcar-atrasadas", response_model=MarcarAtrasadasResponse)
async def marcar_faturas_atrasadas(
    data_referencia: Optional[date] = Query(
        None,
        description="Data de referência para atraso (padrão: hoje do clube)"
    ),
    db: AsyncSession = Depends(get_db)
) -> MarcarAtrasadasResponse:
    """Atualiza faturas vencidas para o status ATRASADA."""
    if data_referencia is None:
        data_referencia = hoje_clube()
    service = FaturaService(db)
    atualizadas = await service.marcar_faturas_atrasadas(data_referencia)
    return MarcarAtrasadasResponse(
        data_referencia=data_referencia,
        atualizadas=atualizadas,
    )


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


@router.post("/{fatura_id}/baixa-manual", response_model=FaturaResponse)
async def baixa_manual(
    fatura_id: uuid.UUID,
    dados: FaturaBaixaManual,
    db: AsyncSession = Depends(get_db)
) -> FaturaResponse:
    """
    Registra a baixa manual de pagamento de uma fatura PENDENTE ou ATRASADA pela administração.
    """
    service = FaturaService(db)
    return await service.baixa_manual(fatura_id, dados)


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
