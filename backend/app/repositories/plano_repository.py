"""
Repositório de dados dos Planos de mensalidade.
"""
from typing import Dict, List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.plano import Plano


class PlanoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, plano_id: uuid.UUID) -> Optional[Plano]:
        return await self.session.get(Plano, plano_id)

    async def get_by_nome(self, nome: str) -> Optional[Plano]:
        """Busca plano pelo nome de forma case-insensitive."""
        query = select(Plano).where(func.lower(Plano.nome) == nome.strip().lower())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(self, ativo: Optional[bool] = None) -> List[Plano]:
        query = select(Plano).order_by(Plano.nome)
        if ativo is not None:
            query = query.where(Plano.ativo == ativo)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def contar_associados(self, plano_ids: List[uuid.UUID]) -> Dict[uuid.UUID, int]:
        """Conta, em uma única query, os sócios não inativos de cada plano."""
        if not plano_ids:
            return {}
        query = (
            select(Associado.plano_id, func.count(Associado.id))
            .where(
                Associado.plano_id.in_(plano_ids),
                Associado.status != StatusAssociado.INATIVO,
            )
            .group_by(Associado.plano_id)
        )
        result = await self.session.execute(query)
        return dict(result.all())

    async def possui_associados(self, plano_id: uuid.UUID) -> bool:
        """True se algum sócio (em qualquer status, inclusive inativo) usa o plano."""
        query = select(Associado.id).where(Associado.plano_id == plano_id).limit(1)
        result = await self.session.execute(query)
        return result.first() is not None

    async def create(self, **campos) -> Plano:
        plano = Plano(**campos)
        self.session.add(plano)
        await self.session.flush()
        await self.session.refresh(plano)
        return plano

    async def update(self, plano: Plano, campos: dict) -> Plano:
        for campo, valor in campos.items():
            setattr(plano, campo, valor)
        await self.session.flush()
        await self.session.refresh(plano)
        return plano

    async def delete(self, plano: Plano) -> None:
        await self.session.delete(plano)
        await self.session.flush()
