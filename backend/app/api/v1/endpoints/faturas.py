"""
Endpoints da API v1 para Gestão de Faturas e Mensalidades.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.fatura import Fatura, StatusFatura
from app.schemas.fatura import FaturaCreate, FaturaResponse

router = APIRouter()


@router.get("/", response_model=List[FaturaResponse])
async def list_faturas(
    associado_id: Optional[uuid.UUID] = Query(None, description="Filtrar por associado"),
    status: Optional[StatusFatura] = Query(None, description="Filtrar por status"),
    db: AsyncSession = Depends(get_db)
) -> List[FaturaResponse]:
    """Lista faturas com filtros opcionais por associado e status."""
    query = select(Fatura)
    if associado_id:
        query = query.where(Fatura.associado_id == associado_id)
    if status:
        query = query.where(Fatura.status == status)
    query = query.order_by(Fatura.data_vencimento.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=FaturaResponse, status_code=status.HTTP_201_CREATED)
async def create_fatura(
    data: FaturaCreate,
    db: AsyncSession = Depends(get_db)
) -> FaturaResponse:
    """
    Cria uma nova fatura/mensalidade.
    TODO(FASE-3-PIX): Gerar cobrança Pix dinâmica com txid e QR Code via Efí / Asaas.
    """
    fatura = Fatura(
        associado_id=data.associado_id,
        referencia_mes=data.referencia_mes,
        valor_base=data.valor_base,
        valor_convidados_excedentes=data.valor_convidados_excedentes,
        valor_desconto=data.valor_desconto,
        valor_total=data.valor_total,
        data_vencimento=data.data_vencimento,
        forma_pagamento=data.forma_pagamento,
        status=StatusFatura.PENDENTE,
    )
    db.add(fatura)
    await db.commit()
    await db.refresh(fatura)
    return fatura
