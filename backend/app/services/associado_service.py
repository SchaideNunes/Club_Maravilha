"""
Camada de serviço de negócio para gestão de Associados.
Centraliza validações, regras de domínio e chamadas de repositório.
"""
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.repositories.associado_repository import AssociadoRepository
from app.schemas.associado import AssociadoCreate, AssociadoUpdate


class AssociadoService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AssociadoRepository(session)
        self.session = session

    async def list_associados(
        self,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[StatusAssociado] = None
    ) -> List[Associado]:
        return await self.repository.list_all(skip=skip, limit=limit, status=status_filter)

    async def get_by_id(self, associado_id: uuid.UUID) -> Associado:
        associado = await self.repository.get_by_id(associado_id)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado."
            )
        return associado

    async def create_associado(self, data: AssociadoCreate) -> Associado:
        # Validação de unicidade de CPF
        existing_cpf = await self.repository.get_by_cpf(data.cpf)
        if existing_cpf:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um associado cadastrado com o CPF {data.cpf}."
            )

        # Validação de unicidade de Email
        existing_email = await self.repository.get_by_email(data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um associado cadastrado com o e-mail {data.email}."
            )

        associado = await self.repository.create(data)
        await self.session.commit()
        
        # TODO(FASE-2-CATRACA): Sincronizar criação na lista branca da catraca facial
        return associado

    async def update_associado(self, associado_id: uuid.UUID, data: AssociadoUpdate) -> Associado:
        associado = await self.get_by_id(associado_id)
        
        if data.email and data.email != associado.email:
            existing_email = await self.repository.get_by_email(data.email)
            if existing_email and existing_email.id != associado_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este e-mail já está sendo utilizado por outro associado."
                )

        updated = await self.repository.update(associado, data)
        await self.session.commit()

        # TODO(FASE-2-CATRACA): Se o status mudou para BLOQUEADO ou INADIMPLENTE, revogar acesso na catraca
        return updated
