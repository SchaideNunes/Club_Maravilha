"""
Repositório de dados para Convidados, controle de franquia de 8 e bilhetagem de excedentes.
"""
import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.convidado import Convidado, StatusConvidado


class ConvidadoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, convidado_id: uuid.UUID) -> Optional[Convidado]:
        query = select(Convidado).where(Convidado.id == convidado_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Optional[Convidado]:
        query = select(Convidado).where(Convidado.qr_code_token == token)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def contar_convites_no_mes(
        self,
        associado_id: uuid.UUID,
        ano: int,
        mes: int
    ) -> int:
        """
        Conta quantos convites ativos ou utilizados foram emitidos pelo titular
        para o mês de visita informado (excluindo os cancelados).
        """
        query = select(func.count()).select_from(Convidado).where(
            and_(
                Convidado.associado_titular_id == associado_id,
                Convidado.status != StatusConvidado.CANCELADO,
                extract("year", Convidado.data_visita) == ano,
                extract("month", Convidado.data_visita) == mes,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def list_convidados(
        self,
        associado_id: Optional[uuid.UUID] = None,
        data_visita: Optional[date] = None,
        status: Optional[StatusConvidado] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Convidado]:
        query = select(Convidado)
        if associado_id:
            query = query.where(Convidado.associado_titular_id == associado_id)
        if data_visita:
            query = query.where(Convidado.data_visita == data_visita)
        if status:
            query = query.where(Convidado.status == status)

        query = query.order_by(Convidado.data_visita.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_excedentes_nao_faturados(self, associado_id: uuid.UUID) -> List[Convidado]:
        """
        Retorna todos os convites excedentes (não gratuitos) que ainda não foram
        agregados a nenhuma fatura mensal Pix do titular.
        """
        query = select(Convidado).where(
            and_(
                Convidado.associado_titular_id == associado_id,
                Convidado.is_gratuito.is_(False),
                Convidado.fatura_agregada_id.is_(None),
                Convidado.status != StatusConvidado.CANCELADO
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, convidado: Convidado) -> Convidado:
        self.session.add(convidado)
        await self.session.flush()
        await self.session.refresh(convidado)
        return convidado

    async def update(self, convidado: Convidado) -> Convidado:
        self.session.add(convidado)
        await self.session.flush()
        await self.session.refresh(convidado)
        return convidado
