"""
Endpoints administrativos para a Central de Configurações e Pré-visualização de Templates.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.configuracao import (
    ConfiguracaoResponse,
    ConfiguracaoUpdate,
    PreviewTemplateRequest,
    PreviewTemplateResponse,
)
from app.services.configuracao_service import ConfiguracaoService

router = APIRouter()


@router.get("", response_model=ConfiguracaoResponse)
@router.get("/", response_model=ConfiguracaoResponse, include_in_schema=False)
async def get_configuracao(
    db: AsyncSession = Depends(get_db),
) -> ConfiguracaoResponse:
    """Retorna as configurações globais do clube (singleton)."""
    service = ConfiguracaoService(db)
    return await service.get_configuracao()


@router.patch("", response_model=ConfiguracaoResponse)
@router.patch("/", response_model=ConfiguracaoResponse, include_in_schema=False)
async def patch_configuracao(
    dados: ConfiguracaoUpdate,
    db: AsyncSession = Depends(get_db),
) -> ConfiguracaoResponse:
    """Atualização parcial das configurações do clube."""
    service = ConfiguracaoService(db)
    return await service.update_configuracao(dados)


@router.post("/preview-template", response_model=PreviewTemplateResponse)
async def preview_template(
    dados: PreviewTemplateRequest,
    db: AsyncSession = Depends(get_db),
) -> PreviewTemplateResponse:
    """Renderiza a pré-visualização de um template com dados reais ou fictícios."""
    service = ConfiguracaoService(db)
    mensagem = await service.preview_template(
        template=dados.template,
        fatura_id=dados.fatura_id,
    )
    return PreviewTemplateResponse(mensagem=mensagem)
