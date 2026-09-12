"""
Repositório de dados para a entidade de Faturas / Mensalidades.
"""
import uuid
from datetime import date
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.fatura import Fatura, StatusFatura


class FaturaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, fatura_id: uuid.UUID) -> Optional[Fatura]:
        query = select(Fatura).where(Fatura.id == fatura_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_txid(self, txid: str) -> Optional[Fatura]:
        query = select(Fatura).where(Fatura.txid == txid)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_faturas(
        self,
        associado_id: Optional[uuid.UUID] = None,
        status: Optional[StatusFatura] = None,
        referencia_mes: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Fatura]:
        query = select(Fatura)
        if associado_id:
            query = query.where(Fatura.associado_id == associado_id)
        if status:
            query = query.where(Fatura.status == status)
        if referencia_mes:
            query = query.where(Fatura.referencia_mes == referencia_mes)
        query = query.offset(skip).limit(limit).order_by(Fatura.data_vencimento.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, fatura: Fatura) -> Fatura:
        self.session.add(fatura)
        await self.session.flush()
        await self.session.refresh(fatura)
        return fatura

    async def update(self, fatura: Fatura) -> Fatura:
        self.session.add(fatura)
        await self.session.flush()
        await self.session.refresh(fatura)
        return fatura

    async def get_faturas_para_regua(
        self,
        data_vencimento: date,
        campo_notificacao: str
    ) -> List[Fatura]:
        """
        Busca faturas pendentes com vencimento na data especificada e que ainda
        não receberam o disparo da régua (campo de timestamp nulo).
        Faz joinedload do associado para evitar N+1 queries.
        """
        col = getattr(Fatura, campo_notificacao)
        query = (
            select(Fatura)
            .options(joinedload(Fatura.associado))
            .where(
                Fatura.status.in_([StatusFatura.PENDENTE, StatusFatura.VENCIDO]),
                Fatura.data_vencimento == data_vencimento,
                col.is_(None)
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
