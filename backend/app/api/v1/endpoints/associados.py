"""
Endpoints da API v1 para Gestão de Associados.
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.associado import StatusAssociado
from app.schemas.associado import (
    AssociadoCreate,
    AssociadoResponse,
    AssociadoUpdate,
)
from app.services.associado_service import AssociadoService

router = APIRouter()


@router.get("/", response_model=List[AssociadoResponse])
async def list_associados(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[StatusAssociado] = Query(None, description="Filtrar por status"),
    db: AsyncSession = Depends(get_db)
) -> List[AssociadoResponse]:
    """Lista associados cadastrados com paginação e filtro por status."""
    service = AssociadoService(db)
    return await service.list_associados(skip=skip, limit=limit, status_filter=status)


@router.post("/", response_model=AssociadoResponse, status_code=status.HTTP_201_CREATED)
async def create_associado(
    data: AssociadoCreate,
    db: AsyncSession = Depends(get_db)
) -> AssociadoResponse:
    """Cadastra um novo associado no Club Maravilha."""
    service = AssociadoService(db)
    return await service.create_associado(data)


@router.get("/{associado_id}", response_model=AssociadoResponse)
async def get_associado(
    associado_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> AssociadoResponse:
    """Recupera os detalhes de um associado pelo ID."""
    service = AssociadoService(db)
    return await service.get_by_id(associado_id)


@router.patch("/{associado_id}", response_model=AssociadoResponse)
async def update_associado(
    associado_id: uuid.UUID,
    data: AssociadoUpdate,
    db: AsyncSession = Depends(get_db)
) -> AssociadoResponse:
    """Atualiza dados cadastrais ou status de um associado."""
    service = AssociadoService(db)
    return await service.update_associado(associado_id, data)
