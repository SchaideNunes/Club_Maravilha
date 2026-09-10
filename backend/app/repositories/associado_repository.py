"""
Repositório de dados para a entidade de Associados.
Segue o princípio de isolamento de persistência da Clean Architecture.
"""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.schemas.associado import AssociadoCreate, AssociadoUpdate


class AssociadoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, associado_id: uuid.UUID) -> Optional[Associado]:
        query = select(Associado).where(Associado.id == associado_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_cpf(self, cpf: str) -> Optional[Associado]:
        query = select(Associado).where(Associado.cpf == cpf)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Associado]:
        query = select(Associado).where(Associado.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[StatusAssociado] = None
    ) -> List[Associado]:
        query = select(Associado)
        if status:
            query = query.where(Associado.status == status)
        query = query.offset(skip).limit(limit).order_by(Associado.nome)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, associado_in: AssociadoCreate) -> Associado:
        associado = Associado(
            nome=associado_in.nome,
            cpf=associado_in.cpf,
            whatsapp=associado_in.whatsapp,
            email=associado_in.email,
            foto_url=associado_in.foto_url,
            observacoes=associado_in.observacoes,
            status=StatusAssociado.ATIVO,
        )
        self.session.add(associado)
        await self.session.flush()
        await self.session.refresh(associado)
        return associado

    async def update(self, associado: Associado, update_data: AssociadoUpdate) -> Associado:
        data_dict = update_data.model_dump(exclude_unset=True)
        for field, value in data_dict.items():
            setattr(associado, field, value)
        self.session.add(associado)
        await self.session.flush()
        await self.session.refresh(associado)
        return associado
