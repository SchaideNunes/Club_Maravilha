"""
Repositório de dados dos Membros da Família (dependentes do titular).
"""
from typing import List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.membro_familia import MembroFamilia


class MembroFamiliaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_associado(self, associado_id: uuid.UUID) -> List[MembroFamilia]:
        query = (
            select(MembroFamilia)
            .where(MembroFamilia.associado_id == associado_id)
            .order_by(MembroFamilia.nome)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_do_associado(self, associado_id: uuid.UUID, membro_id: uuid.UUID) -> Optional[MembroFamilia]:
        """Busca o dependente garantindo que ele pertence ao titular informado."""
        query = select(MembroFamilia).where(
            MembroFamilia.id == membro_id,
            MembroFamilia.associado_id == associado_id,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_por_cpf(self, associado_id: uuid.UUID, cpf: str) -> Optional[MembroFamilia]:
        query = select(MembroFamilia).where(
            MembroFamilia.associado_id == associado_id,
            MembroFamilia.cpf == cpf,
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, associado_id: uuid.UUID, **campos) -> MembroFamilia:
        membro = MembroFamilia(associado_id=associado_id, **campos)
        self.session.add(membro)
        await self.session.flush()
        await self.session.refresh(membro)
        return membro

    async def update(self, membro: MembroFamilia, campos: dict) -> MembroFamilia:
        for campo, valor in campos.items():
            setattr(membro, campo, valor)
        await self.session.flush()
        await self.session.refresh(membro)
        return membro

    async def delete(self, membro: MembroFamilia) -> None:
        await self.session.delete(membro)
        await self.session.flush()
