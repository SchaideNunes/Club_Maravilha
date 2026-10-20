"""
Endpoints da API v1 para os Planos de mensalidade (categorias de sócios).
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.plano import PlanoCreate, PlanoResponse, PlanoUpdate
from app.services.plano_service import PlanoService

router = APIRouter()


@router.get("/", response_model=List[PlanoResponse])
async def listar_planos(
    ativo: Optional[bool] = Query(None, description="Filtrar planos ativos (true) ou desativados (false)"),
    db: AsyncSession = Depends(get_db)
) -> List[PlanoResponse]:
    """Lista os planos em ordem alfabética com a quantidade de sócios vinculados."""
    return await PlanoService(db).listar(ativo=ativo)


@router.post("/", response_model=PlanoResponse, status_code=status.HTTP_201_CREATED)
async def criar_plano(data: PlanoCreate, db: AsyncSession = Depends(get_db)) -> PlanoResponse:
    """Cadastra um plano. Valor 0 representa sócios isentos."""
    return await PlanoService(db).criar(data)


@router.patch("/{plano_id}", response_model=PlanoResponse)
async def atualizar_plano(
    plano_id: uuid.UUID,
    data: PlanoUpdate,
    db: AsyncSession = Depends(get_db)
) -> PlanoResponse:
    """Atualiza nome, descrição, valor ou ativa/desativa o plano (vale para as próximas faturas)."""
    return await PlanoService(db).atualizar(plano_id, data)


@router.delete("/{plano_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_plano(plano_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Exclui um plano que nunca foi usado; planos com sócios devem ser desativados."""
    await PlanoService(db).excluir(plano_id)
