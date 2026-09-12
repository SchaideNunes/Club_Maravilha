"""
Endpoints da API v1 para Gestão de Convidados, Emissão de QR Codes e Catraca de Visitantes.
"""
import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.convidado import StatusConvidado
from app.schemas.convidado import (
    ConvidadoCreate,
    ConvidadoResponse,
    ConvidadoValidateQRRequest,
    ConvidadoValidateQRResponse,
    QuotaConvidadosResponse,
)
from app.services.convidado_service import ConvidadoService

router = APIRouter()


@router.post("/", response_model=ConvidadoResponse, status_code=status.HTTP_201_CREATED)
async def emitir_convite(
    data: ConvidadoCreate,
    db: AsyncSession = Depends(get_db)
) -> ConvidadoResponse:
    """
    Emite um convite de visitante com QR Code temporário.
    Aplica a cota gratuita de 8 convites mensais (do 9º em diante, gera taxa excedente de R$ 35,00).
    """
    service = ConvidadoService(db)
    return await service.emitir_convite(data)


@router.get("/cota/{associado_id}", response_model=QuotaConvidadosResponse)
async def consultar_cota(
    associado_id: uuid.UUID,
    ano: Optional[int] = Query(None, description="Ano da consulta (padrão: ano atual)"),
    mes: Optional[int] = Query(None, description="Mês da consulta 1-12 (padrão: mês atual)"),
    db: AsyncSession = Depends(get_db)
) -> QuotaConvidadosResponse:
    """Consulta a cota de convites disponíveis e excedentes de um associado titular."""
    hoje = date.today()
    ano_val = ano or hoje.year
    mes_val = mes or hoje.month
    service = ConvidadoService(db)
    return await service.consultar_cota(associado_id=associado_id, ano=ano_val, mes=mes_val)


@router.post("/validar-qr", response_model=ConvidadoValidateQRResponse)
async def validar_qr_catraca(
    data: ConvidadoValidateQRRequest,
    db: AsyncSession = Depends(get_db)
) -> ConvidadoValidateQRResponse:
    """
    Endpoint consumido pelo leitor de QR Code da catraca de visitantes.
    Valida token criptográfico, checa se a visita é no dia de hoje e registra o check-in.
    """
    service = ConvidadoService(db)
    return await service.validar_qr_catraca(token=data.token, data_leitura=data.data_leitura)


@router.get("/", response_model=List[ConvidadoResponse])
async def list_convidados(
    associado_id: Optional[uuid.UUID] = Query(None, description="Filtrar por associado titular"),
    data_visita: Optional[date] = Query(None, description="Filtrar por data de visita"),
    status: Optional[StatusConvidado] = Query(None, description="Filtrar por status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> List[ConvidadoResponse]:
    """Lista convites com filtros opcionais."""
    service = ConvidadoService(db)
    return await service.list_convidados(
        associado_id=associado_id,
        data_visita=data_visita,
        status_filter=status,
        skip=skip,
        limit=limit
    )


@router.get("/{convidado_id}", response_model=ConvidadoResponse)
async def get_convidado(
    convidado_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ConvidadoResponse:
    """Retorna detalhes de um convite específico."""
    service = ConvidadoService(db)
    return await service.get_by_id(convidado_id)


@router.post("/{convidado_id}/cancelar", response_model=ConvidadoResponse)
async def cancel_convite(
    convidado_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ConvidadoResponse:
    """Cancela um convite emitido que ainda não tenha sido bipado na catraca."""
    service = ConvidadoService(db)
    return await service.cancelar_convite(convidado_id)
