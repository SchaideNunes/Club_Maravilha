"""
Camada de serviço de negócio para gestão de Associados.
Centraliza validações, regras de domínio e chamadas de repositório.
"""
import math
import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.repositories.associado_repository import AssociadoRepository
from app.schemas.associado import (
    AssociadoCreate,
    AssociadoResponse,
    AssociadoUpdate,
    ImportAssociadosResult,
    PaginatedAssociadosResponse,
)
from app.services.excel_import_service import parse_excel_or_csv_bytes


class AssociadoService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AssociadoRepository(session)
        self.session = session

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        q: Optional[str] = None,
        status_filter: Optional[StatusAssociado] = None
    ) -> PaginatedAssociadosResponse:
        """Retorna associados com paginação e busca textual estruturada."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        skip = (page - 1) * page_size
        items, total = await self.repository.list_paginated(
            skip=skip,
            limit=page_size,
            q=q,
            status=status_filter
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedAssociadosResponse(
            items=[AssociadoResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    async def get_by_id(self, associado_id: uuid.UUID) -> Associado:
        associado = await self.repository.get_by_id(associado_id)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado."
            )
        return associado

    async def create_associado(self, data: AssociadoCreate) -> Associado:
        # Normaliza e valida CPF matematicamente
        try:
            from app.services.excel_import_service import validate_and_format_cpf
            data.cpf = validate_and_format_cpf(data.cpf)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)
            )

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

    async def delete_associado(self, associado_id: uuid.UUID) -> None:
        """Remove o associado do clube."""
        deleted = await self.repository.delete(associado_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado para exclusão."
            )
        await self.session.commit()

    async def import_associados_planilha(
        self,
        file_bytes: bytes,
        filename: str
    ) -> ImportAssociadosResult:
        """
        Processa arquivo .xlsx ou .csv em lote, insere novos sócios
        e ignora duplicados sem quebrar a transação.
        """
        try:
            valid_rows, parse_errors = parse_excel_or_csv_bytes(file_bytes, filename)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)
            )

        imported_count, ignored_count = await self.repository.bulk_import(valid_rows)
        await self.session.commit()

        return ImportAssociadosResult(
            total_lidos=len(valid_rows) + len(parse_errors),
            total_importados=imported_count,
            total_ignorados_duplicados=ignored_count,
            erros=parse_errors
        )
