"""
Endpoints da API v1 para Agendamento de Quadras Esportivas.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.schemas.agendamento import AgendamentoCreate, AgendamentoResponse

router = APIRouter()


@router.get("/", response_model=List[AgendamentoResponse])
async def list_agendamentos(
    quadra: Optional[TipoQuadra] = Query(None, description="Filtrar por tipo de quadra"),
    data_inicio: Optional[datetime] = Query(None, description="A partir de data/hora"),
    db: AsyncSession = Depends(get_db)
) -> List[AgendamentoResponse]:
    """Lista agendamentos de quadras com filtros opcionais para a grade visual."""
    query = select(AgendamentoQuadra).where(AgendamentoQuadra.status == StatusAgendamento.CONFIRMADO)
    if quadra:
        query = query.where(AgendamentoQuadra.quadra == quadra)
    if data_inicio:
        query = query.where(AgendamentoQuadra.data_inicio >= data_inicio)
    query = query.order_by(AgendamentoQuadra.data_inicio.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=AgendamentoResponse, status_code=status.HTTP_201_CREATED)
async def create_agendamento(
    data: AgendamentoCreate,
    db: AsyncSession = Depends(get_db)
) -> AgendamentoResponse:
    """
    Reserva um horário de quadra para um associado.
    Aplica travas de segurança:
    1. Associado deve existir e estar ATIVO.
    2. Associado não pode ter faturas vencidas em aberto.
    3. Horário na mesma quadra não pode conflitar com outra reserva confirmada.
    """
    # 1. Verifica status do associado
    associado_res = await db.execute(select(Associado).where(Associado.id == data.associado_id))
    associado = associado_res.scalar_one_or_none()
    if not associado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associado não encontrado.")
    if associado.status != StatusAssociado.ATIVO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Associado não pode reservar quadras. Status cadastral: {associado.status}."
        )

    # 2. Verifica se possui faturas vencidas
    faturas_vencidas = await db.execute(
        select(Fatura).where(
            and_(
                Fatura.associado_id == data.associado_id,
                Fatura.status == StatusFatura.VENCIDO
            )
        )
    )
    if faturas_vencidas.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reserva bloqueada: associado possui mensalidade vencida em aberto."
        )

    # 3. Verifica sobreposição de horários na quadra
    # TODO(FASE-5-QUADRAS): Implementar SELECT FOR UPDATE para trava de concorrência atômica estrita
    conflito_query = select(AgendamentoQuadra).where(
        and_(
            AgendamentoQuadra.quadra == data.quadra,
            AgendamentoQuadra.status == StatusAgendamento.CONFIRMADO,
            AgendamentoQuadra.data_inicio < data.data_fim,
            AgendamentoQuadra.data_fim > data.data_inicio
        )
    )
    conflito = (await db.execute(conflito_query)).scalar_one_or_none()
    if conflito:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horário indisponível. Já existe uma reserva confirmada para este período na quadra selecionada."
        )

    agendamento = AgendamentoQuadra(
        associado_id=data.associado_id,
        quadra=data.quadra,
        data_inicio=data.data_inicio,
        data_fim=data.data_fim,
        observacoes=data.observacoes,
        status=StatusAgendamento.CONFIRMADO
    )
    db.add(agendamento)
    await db.commit()
    await db.refresh(agendamento)
    return agendamento
