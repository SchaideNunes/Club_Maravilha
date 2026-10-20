"""
Camada de serviço dos Membros da Família (dependentes do titular).
"""
from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.membro_familia import MembroFamilia
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.membro_familia_repository import MembroFamiliaRepository
from app.schemas.membro_familia import MembroFamiliaCreate, MembroFamiliaUpdate


class MembroFamiliaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = MembroFamiliaRepository(session)
        self.associado_repo = AssociadoRepository(session)

    async def _garantir_titular(self, associado_id: uuid.UUID) -> None:
        if not await self.associado_repo.get_by_id(associado_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associado não encontrado.")

    async def _get_or_404(self, associado_id: uuid.UUID, membro_id: uuid.UUID) -> MembroFamilia:
        membro = await self.repository.get_do_associado(associado_id, membro_id)
        if not membro:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membro da família não encontrado.")
        return membro

    async def _garantir_cpf_livre(
        self, associado_id: uuid.UUID, cpf: str, membro_id: Optional[uuid.UUID] = None
    ) -> None:
        existente = await self.repository.get_por_cpf(associado_id, cpf)
        if existente and existente.id != membro_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"O CPF {cpf} já está cadastrado na família deste associado.",
            )

    async def listar(self, associado_id: uuid.UUID) -> List[MembroFamilia]:
        await self._garantir_titular(associado_id)
        return await self.repository.list_by_associado(associado_id)

    async def criar(self, associado_id: uuid.UUID, data: MembroFamiliaCreate) -> MembroFamilia:
        await self._garantir_titular(associado_id)
        if data.cpf:
            await self._garantir_cpf_livre(associado_id, data.cpf)
        membro = await self.repository.create(associado_id, **data.model_dump())
        await self.session.commit()
        return membro

    async def atualizar(
        self, associado_id: uuid.UUID, membro_id: uuid.UUID, data: MembroFamiliaUpdate
    ) -> MembroFamilia:
        membro = await self._get_or_404(associado_id, membro_id)
        campos = data.model_dump(exclude_unset=True)
        if campos.get("cpf"):
            await self._garantir_cpf_livre(associado_id, campos["cpf"], membro_id)
        membro = await self.repository.update(membro, campos)
        await self.session.commit()
        return membro

    async def excluir(self, associado_id: uuid.UUID, membro_id: uuid.UUID) -> None:
        membro = await self._get_or_404(associado_id, membro_id)
        await self.repository.delete(membro)
        await self.session.commit()
