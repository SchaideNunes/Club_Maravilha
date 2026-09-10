"""
Endpoints da API v1 para Controle de Convidados e Emissão de QR Code.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado, generate_qr_token
from app.schemas.convidado import ConvidadoCreate, ConvidadoResponse

router = APIRouter()


@router.get("/", response_model=List[ConvidadoResponse])
async def list_convidados(
    associado_id: Optional[uuid.UUID] = Query(None, description="Filtrar por associado titular"),
    data_visita: Optional[date] = Query(None, description="Filtrar por data da visita"),
    db: AsyncSession = Depends(get_db)
) -> List[ConvidadoResponse]:
    """Lista convidados emitidos."""
    query = select(Convidado)
    if associado_id:
        query = query.where(Convidado.associado_titular_id == associado_id)
    if data_visita:
        query = query.where(Convidado.data_visita == data_visita)
    query = query.order_by(Convidado.data_visita.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=ConvidadoResponse, status_code=status.HTTP_201_CREATED)
async def emitir_convite(
    data: ConvidadoCreate,
    db: AsyncSession = Depends(get_db)
) -> ConvidadoResponse:
    """
    Emite um convite de visitante com QR Code temporário para acesso na catraca.
    Regra da Cota de 8:
    - Primeiros 8 convites no mês da visita são gratuitos (is_gratuito=True).
    - A partir do 9º convite, é cobrada taxa de convite excedente (R$ 35,00)
      a ser agregada na próxima fatura Pix mensal do titular.
    """
    # 1. Verifica titular
    associado_res = await db.execute(
        select(Associado).where(Associado.id == data.associado_titular_id)
    )
    associado = associado_res.scalar_one_or_none()
    if not associado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associado titular não encontrado.")
    if associado.status != StatusAssociado.ATIVO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Associado não pode emitir convites. Status: {associado.status}."
        )

    # 2. Contabiliza convites emitidos no mesmo mês da visita
    mes_visita = data.data_visita.month
    ano_visita = data.data_visita.year
    
    count_query = select(func.count(Convidado.id)).where(
        Convidado.associado_titular_id == data.associado_titular_id,
        extract("month", Convidado.data_visita) == mes_visita,
        extract("year", Convidado.data_visita) == ano_visita,
        Convidado.status != StatusConvidado.CANCELADO
    )
    total_mes = (await db.execute(count_query)).scalar() or 0

    # 3. Aplica regra de franquia de 8
    is_gratuito = total_mes < settings.FRANQUIA_CONVITES_MENSAL
    valor_cobrado = Decimal("0.00") if is_gratuito else Decimal(str(settings.VALOR_CONVITE_EXCEDENTE))

    convidado = Convidado(
        associado_titular_id=data.associado_titular_id,
        nome=data.nome,
        cpf=data.cpf,
        data_visita=data.data_visita,
        qr_code_token=generate_qr_token(),
        status=StatusConvidado.EMITIDO,
        is_gratuito=is_gratuito,
        valor_cobrado=valor_cobrado,
    )
    db.add(convidado)
    await db.commit()
    await db.refresh(convidado)
    return convidado
