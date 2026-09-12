"""
Endpoints da API v1 para Gestão de Associados e Importação de Planilhas.
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.associado import StatusAssociado
from app.schemas.associado import (
    AssociadoCreate,
    AssociadoResponse,
    AssociadoUpdate,
    ImportAssociadosResult,
    PaginatedAssociadosResponse,
)
from app.services.associado_service import AssociadoService

router = APIRouter()


@router.get("/", response_model=PaginatedAssociadosResponse)
async def list_associados(
    q: Optional[str] = Query(None, description="Busca textual por nome, CPF ou email"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    status: Optional[StatusAssociado] = Query(None, description="Filtrar por status"),
    db: AsyncSession = Depends(get_db)
) -> PaginatedAssociadosResponse:
    """Lista associados com busca textual e paginação completa."""
    service = AssociadoService(db)
    return await service.list_paginated(
        page=page,
        page_size=page_size,
        q=q,
        status_filter=status
    )


@router.post("/", response_model=AssociadoResponse, status_code=status.HTTP_201_CREATED)
async def create_associado(
    data: AssociadoCreate,
    db: AsyncSession = Depends(get_db)
) -> AssociadoResponse:
    """Cadastra um novo associado no Club Maravilha."""
    service = AssociadoService(db)
    return await service.create_associado(data)


@router.post("/importar", response_model=ImportAssociadosResult, status_code=status.HTTP_200_OK)
async def importar_planilha_associados(
    file: UploadFile = File(..., description="Arquivo de planilha .xlsx ou .csv"),
    db: AsyncSession = Depends(get_db)
) -> ImportAssociadosResult:
    """
    Importa sócios em lote a partir de arquivo Excel (.xlsx) ou CSV.
    Valida CPFs matematicamente, normaliza telefones e ignora registros duplicados.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo inválido: nome do arquivo ausente."
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio."
        )

    service = AssociadoService(db)
    return await service.import_associados_planilha(content, file.filename)


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


@router.delete("/{associado_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_associado(
    associado_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove um associado do clube."""
    service = AssociadoService(db)
    await service.delete_associado(associado_id)
