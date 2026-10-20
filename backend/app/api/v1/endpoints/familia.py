"""
Endpoints da API v1 para os Membros da Família (dependentes) do associado titular.
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.membro_familia import MembroFamiliaCreate, MembroFamiliaResponse, MembroFamiliaUpdate
from app.services.membro_familia_service import MembroFamiliaService

router = APIRouter()


@router.get("/", response_model=List[MembroFamiliaResponse])
async def listar_familia(associado_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> List[MembroFamiliaResponse]:
    """Lista os dependentes do associado em ordem alfabética."""
    return await MembroFamiliaService(db).listar(associado_id)


@router.post("/", response_model=MembroFamiliaResponse, status_code=status.HTTP_201_CREATED)
async def adicionar_membro_familia(
    associado_id: uuid.UUID,
    data: MembroFamiliaCreate,
    db: AsyncSession = Depends(get_db)
) -> MembroFamiliaResponse:
    """Cadastra um dependente com entrada gratuita, sem consumir a franquia de convidados."""
    return await MembroFamiliaService(db).criar(associado_id, data)


@router.patch("/{membro_id}", response_model=MembroFamiliaResponse)
async def atualizar_membro_familia(
    associado_id: uuid.UUID,
    membro_id: uuid.UUID,
    data: MembroFamiliaUpdate,
    db: AsyncSession = Depends(get_db)
) -> MembroFamiliaResponse:
    """Atualiza os dados de um dependente."""
    return await MembroFamiliaService(db).atualizar(associado_id, membro_id, data)


@router.delete("/{membro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remover_membro_familia(
    associado_id: uuid.UUID,
    membro_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Remove um dependente da família do associado."""
    await MembroFamiliaService(db).excluir(associado_id, membro_id)
