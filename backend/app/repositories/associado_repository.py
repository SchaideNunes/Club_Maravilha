"""
Repositório de dados para a entidade de Associados.
Segue o princípio de isolamento de persistência da Clean Architecture.
"""
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
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

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        q: Optional[str] = None,
        status: Optional[StatusAssociado] = None
    ) -> Tuple[List[Associado], int]:
        """
        Retorna lista paginada e total de registros com busca textual em Nome, CPF ou Email.
        """
        base_query = select(Associado)
        count_query = select(func.count(Associado.id))

        filters = []
        if status:
            filters.append(Associado.status == status)
        if q:
            import re
            term = f"%{q.strip()}%"
            q_digits = re.sub(r"\D", "", q.strip())
            q_conditions = [
                Associado.nome.ilike(term),
                Associado.cpf.like(term),
                Associado.email.ilike(term),
            ]
            if len(q_digits) >= 3:
                q_conditions.append(
                    func.replace(func.replace(Associado.cpf, ".", ""), "-", "").like(f"%{q_digits}%")
                )
            filters.append(or_(*q_conditions))

        if filters:
            base_query = base_query.where(*filters)
            count_query = count_query.where(*filters)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = base_query.offset(skip).limit(limit).order_by(Associado.nome.asc())
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

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

    async def delete(self, associado_id: uuid.UUID) -> bool:
        associado = await self.get_by_id(associado_id)
        if not associado:
            return False
        await self.session.delete(associado)
        await self.session.flush()
        return True

    async def bulk_import(self, members: List[AssociadoCreate]) -> Tuple[int, int]:
        """
        Insere múltiplos associados, ignorando duplicatas de CPF ou e-mail já cadastradas.
        Retorna (total_importados, total_ignorados).
        """
        imported_count = 0
        ignored_count = 0

        for m in members:
            # Verifica existência por CPF ou Email
            existing_cpf = await self.get_by_cpf(m.cpf)
            if existing_cpf:
                ignored_count += 1
                continue

            existing_email = await self.get_by_email(m.email)
            if existing_email:
                ignored_count += 1
                continue

            associado = Associado(
                nome=m.nome,
                cpf=m.cpf,
                whatsapp=m.whatsapp,
                email=m.email,
                foto_url=m.foto_url,
                observacoes=m.observacoes,
                status=StatusAssociado.ATIVO,
            )
            self.session.add(associado)
            imported_count += 1

        await self.session.flush()
        return imported_count, ignored_count
