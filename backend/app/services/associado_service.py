"""
Camada de serviço de negócio para gestão de Associados.
Centraliza validações, regras de domínio e chamadas de repositório.
"""
from datetime import date
import math
from typing import Iterable, List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.schemas.associado import (
    AssociadoCreate,
    AssociadoResponse,
    AssociadoUpdate,
    ImportAssociadosResult,
    PaginatedAssociadosResponse,
    SituacaoFinanceira,
)
from app.services.excel_import_service import parse_excel_or_csv_bytes


def calcular_situacao_financeira(status_faturas: Iterable[StatusFatura]) -> SituacaoFinanceira:
    """
    Deriva a situação financeira do associado a partir do status de suas faturas:
    - Pelo menos uma ATRASADA => ATRASADO
    - Sem atrasos, mas pelo menos uma PENDENTE => PENDENTE
    - Demais casos (vazio, somente PAGAS ou CANCELADAS) => EM_DIA
    """
    status_list = list(status_faturas)
    if any(s == StatusFatura.ATRASADA for s in status_list):
        return SituacaoFinanceira.ATRASADO
    if any(s == StatusFatura.PENDENTE for s in status_list):
        return SituacaoFinanceira.PENDENTE
    return SituacaoFinanceira.EM_DIA


class AssociadoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = AssociadoRepository(session)
        self.configuracao_repo = ConfiguracaoRepository(session)

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        q: Optional[str] = None,
        status_filter: Optional[StatusAssociado] = None,
        situacao: Optional[SituacaoFinanceira] = None,
    ) -> PaginatedAssociadosResponse:
        """Retorna associados com paginação, busca textual e agregação de convidados e situação financeira."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        hoje = date.today()
        ref_mes = f"{hoje.year:04d}-{hoje.month:02d}"
        skip = (page - 1) * page_size

        items, total = await self.repository.list_paginated(
            skip=skip,
            limit=page_size,
            q=q,
            status=status_filter,
            situacao=situacao,
            referencia_mes=ref_mes,
        )

        cfg = await self.configuracao_repo.get_or_create()
        franquia = cfg.franquia_convidados

        item_ids = [item.id for item in items]
        convidados_map = await self.repository.contar_convidados_mes(item_ids, ano=hoje.year, mes=hoje.month)
        situacoes_map = await self.repository.situacoes_financeiras(item_ids, referencia_mes=ref_mes)

        resp_items: List[AssociadoResponse] = []
        for item in items:
            data = AssociadoResponse.model_validate(item).model_dump()
            data["franquia_convidados"] = franquia
            data["convidados_usados_mes"] = convidados_map.get(item.id, 0)
            data["situacao_financeira"] = situacoes_map.get(item.id, SituacaoFinanceira.EM_DIA)
            resp_items.append(AssociadoResponse.model_validate(data))

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedAssociadosResponse(
            items=resp_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_by_id(self, associado_id: uuid.UUID) -> Associado:
        """Busca o associado pelo ID para operações internas."""
        associado = await self.repository.get_by_id(associado_id, com_convidados=True)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado."
            )
        return associado

    async def get_associado_detalhe(self, associado_id: uuid.UUID) -> AssociadoResponse:
        """Retorna detalhes completos do associado sem carregar o histórico de convidados."""
        associado = await self.repository.get_by_id(associado_id, com_convidados=False)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado."
            )

        cfg = await self.configuracao_repo.get_or_create()
        hoje = date.today()
        ref_mes = f"{hoje.year:04d}-{hoje.month:02d}"

        convidados_map = await self.repository.contar_convidados_mes([associado.id], ano=hoje.year, mes=hoje.month)
        situacoes_map = await self.repository.situacoes_financeiras([associado.id], referencia_mes=ref_mes)

        data = AssociadoResponse.model_validate(associado).model_dump()
        data["franquia_convidados"] = cfg.franquia_convidados
        data["convidados_usados_mes"] = convidados_map.get(associado.id, 0)
        data["situacao_financeira"] = situacoes_map.get(associado.id, SituacaoFinanceira.EM_DIA)
        return AssociadoResponse.model_validate(data)

    async def create_associado(self, data: AssociadoCreate) -> AssociadoResponse:
        # Validação de unicidade de CPF (409 Conflict)
        existing_cpf = await self.repository.get_by_cpf(data.cpf)
        if existing_cpf:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe um associado cadastrado com o CPF {data.cpf}."
            )

        # Validação de unicidade de Email (409 Conflict)
        existing_email = await self.repository.get_by_email(data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe um associado cadastrado com o e-mail {data.email}."
            )

        associado = await self.repository.create(data)
        await self.session.commit()

        cfg = await self.configuracao_repo.get_or_create()
        resp_data = AssociadoResponse.model_validate(associado).model_dump()
        resp_data["franquia_convidados"] = cfg.franquia_convidados
        resp_data["convidados_usados_mes"] = 0
        resp_data["situacao_financeira"] = SituacaoFinanceira.EM_DIA
        return AssociadoResponse.model_validate(resp_data)

    async def update_associado(self, associado_id: uuid.UUID, data: AssociadoUpdate) -> AssociadoResponse:
        associado = await self.repository.get_by_id(associado_id, com_convidados=False)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado."
            )

        if data.email and data.email.lower().strip() != associado.email.lower().strip():
            existing_email = await self.repository.get_by_email(data.email)
            if existing_email and existing_email.id != associado_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Este e-mail já está sendo utilizado por outro associado."
                )

        updated = await self.repository.update(associado, data)
        await self.session.commit()

        cfg = await self.configuracao_repo.get_or_create()
        hoje = date.today()
        ref_mes = f"{hoje.year:04d}-{hoje.month:02d}"

        convidados_map = await self.repository.contar_convidados_mes([updated.id], ano=hoje.year, mes=hoje.month)
        situacoes_map = await self.repository.situacoes_financeiras([updated.id], referencia_mes=ref_mes)

        resp_data = AssociadoResponse.model_validate(updated).model_dump()
        resp_data["franquia_convidados"] = cfg.franquia_convidados
        resp_data["convidados_usados_mes"] = convidados_map.get(updated.id, 0)
        resp_data["situacao_financeira"] = situacoes_map.get(updated.id, SituacaoFinanceira.EM_DIA)
        return AssociadoResponse.model_validate(resp_data)

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
        filename: str,
        atualizar_existentes: bool = False
    ) -> ImportAssociadosResult:
        """
        Processa arquivo .xlsx ou .csv em lote, insere ou atualiza sócios
        e gera relatório completo da importação.
        """
        try:
            valid_rows, parse_errors = parse_excel_or_csv_bytes(file_bytes, filename)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc)
            )

        imported, updated, ignored, db_errors = await self.repository.bulk_import(
            valid_rows,
            atualizar_existentes=atualizar_existentes
        )
        await self.session.commit()

        all_errors = parse_errors + db_errors
        all_errors.sort(key=lambda e: e.linha)

        total_lidos = getattr(valid_rows, "total_lidos", len(valid_rows) + len(parse_errors))

        return ImportAssociadosResult(
            total_lidos=total_lidos,
            total_importados=imported,
            total_atualizados=updated,
            total_ignorados_duplicados=ignored,
            erros=all_errors
        )
