"""
Endpoints da API v1 para Agendamento de Quadras Esportivas.
Utiliza a arquitetura em camadas delegando lógica para AgendamentoService.
"""
import uuid
from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.agendamento import StatusAgendamento, TipoQuadra
from app.schemas.agendamento import (
    AgendamentoCreate,
    AgendamentoResponse,
    DisponibilidadeDiaResponse,
)
from app.services.agendamento_service import AgendamentoService

router = APIRouter()


@router.get("/", response_model=List[AgendamentoResponse])
async def list_agendamentos(
    quadra: Optional[TipoQuadra] = Query(None, description="Filtrar por tipo de quadra"),
    data_inicio: Optional[datetime] = Query(None, description="A partir de data/hora"),
    data_fim: Optional[datetime] = Query(None, description="Até data/hora"),
    associado_id: Optional[uuid.UUID] = Query(None, description="Filtrar por associado"),
    status: Optional[StatusAgendamento] = Query(None, description="Filtrar por status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[AgendamentoResponse]:
    """Lista agendamentos de quadras com filtros opcionais para a grade visual."""
    service = AgendamentoService(db)
    return await service.list_agendamentos(
        quadra=quadra,
        data_inicio=data_inicio,
        data_fim=data_fim,
        associado_id=associado_id,
        status_filter=status,
        skip=skip,
        limit=limit
    )


@router.get("/disponibilidade", response_model=DisponibilidadeDiaResponse)
async def consultar_disponibilidade(
    quadra: TipoQuadra = Query(..., description="Quadra desejada"),
    data: date = Query(..., description="Data para consulta da grade (AAAA-MM-DD)"),
    db: AsyncSession = Depends(get_db)
) -> DisponibilidadeDiaResponse:
    """
    Retorna a grade diária completa de slots (06:00 às 22:00) indicando
    horários livres e ocupados para a quadra selecionada.
    """
    service = AgendamentoService(db)
    return await service.get_disponibilidade_dia(quadra=quadra, data_consulta=data)


@router.post("/", response_model=AgendamentoResponse, status_code=status.HTTP_201_CREATED)
async def create_agendamento(
    data: AgendamentoCreate,
    db: AsyncSession = Depends(get_db)
) -> AgendamentoResponse:
    """
    Cria uma reserva de quadra com concorrência atômica (SELECT ... FOR UPDATE).
    Aplica travas de inadimplência, teto de 2 reservas ativas simultâneas e integridade.
    """
    service = AgendamentoService(db)
    return await service.create_agendamento(data)


@router.get("/{agendamento_id}", response_model=AgendamentoResponse)
async def get_agendamento(
    agendamento_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> AgendamentoResponse:
    """Retorna detalhes de uma reserva específica."""
    service = AgendamentoService(db)
    return await service.get_by_id(agendamento_id)


@router.post("/{agendamento_id}/cancelar", response_model=AgendamentoResponse)
async def cancel_agendamento(
    agendamento_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> AgendamentoResponse:
    """
    Cancela uma reserva confirmada, respeitando a política de antecedência mínima de 2 horas.
    """
    service = AgendamentoService(db)
    return await service.cancel_agendamento(agendamento_id)
