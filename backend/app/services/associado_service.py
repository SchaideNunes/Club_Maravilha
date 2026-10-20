"""
Camada de serviço de negócio para gestão de Associados.
Centraliza validações, regras de domínio e chamadas de repositório.
"""
from datetime import date, timezone
import math
from pathlib import Path
import time
from typing import Iterable, List, Optional, Sequence, Tuple
import uuid
from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import clock
from app.core.clock import hoje_clube
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.repositories.plano_repository import PlanoRepository
from app.schemas.associado import (
    AssociadoCreate,
    AssociadoResponse,
    AssociadoUpdate,
    ImportAssociadosResult,
    InativacaoAssociadoResponse,
    PaginatedAssociadosResponse,
    SituacaoFinanceira,
)
from app.services.excel_import_service import parse_excel_or_csv_bytes
from app.services import foto_service


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
        self.plano_repo = PlanoRepository(session)

    async def _enriquecer_associados(self, associados: Sequence[Associado]) -> List[AssociadoResponse]:
        """
        Enriquece associados com franquia configurada, convidados do mês corrente
        e situação financeira em queries agregadas batch, eliminando duplicações.
        """
        if not associados:
            return []

        cfg = await self.configuracao_repo.get_or_create()
        franquia = cfg.franquia_convidados
        hoje = hoje_clube()
        ref_mes = f"{hoje.year:04d}-{hoje.month:02d}"

        item_ids = [item.id for item in associados]
        convidados_map = await self.repository.contar_convidados_mes(item_ids, ano=hoje.year, mes=hoje.month)
        situacoes_map = await self.repository.situacoes_financeiras(item_ids, referencia_mes=ref_mes)

        resp_items: List[AssociadoResponse] = []
        for item in associados:
            data = AssociadoResponse.model_validate(item).model_dump()
            data["franquia_convidados"] = franquia
            data["convidados_usados_mes"] = convidados_map.get(item.id, 0)
            data["situacao_financeira"] = situacoes_map.get(item.id, SituacaoFinanceira.EM_DIA)
            resp_items.append(AssociadoResponse.model_validate(data))
        return resp_items

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

        hoje = hoje_clube()
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

        resp_items = await self._enriquecer_associados(items)
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

        enriquecidos = await self._enriquecer_associados([associado])
        return enriquecidos[0]

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

        await self._validar_plano(data.plano_id)

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

        if "status" in data.model_fields_set:
            if data.status == StatusAssociado.INATIVO:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Para desligar o associado use a ação de inativar.",
                )
            if associado.status == StatusAssociado.INATIVO:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Associado inativo: use a ação de reativar.",
                )

        if "plano_id" in data.model_fields_set:
            await self._validar_plano(data.plano_id, plano_atual_id=associado.plano_id)

        updated = await self.repository.update(associado, data)
        await self.session.commit()

        enriquecidos = await self._enriquecer_associados([updated])
        return enriquecidos[0]

    async def _validar_plano(self, plano_id: Optional[uuid.UUID], plano_atual_id: Optional[uuid.UUID] = None) -> None:
        """
        Novos vínculos só podem usar planos ativos. Manter o plano atual é sempre permitido,
        mesmo que ele tenha sido desativado depois.
        """
        if plano_id is None or plano_id == plano_atual_id:
            return
        plano = await self.plano_repo.get_by_id(plano_id)
        if not plano or not plano.ativo:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Plano informado não existe ou está desativado.",
            )

    async def _get_or_404(self, associado_id: uuid.UUID, for_update: bool = False) -> Associado:
        associado = await self.repository.get_by_id(associado_id, for_update=for_update)
        if not associado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associado não encontrado.")
        return associado

    async def inativar_associado(
        self, associado_id: uuid.UUID, motivo: Optional[str] = None
    ) -> InativacaoAssociadoResponse:
        """
        Desliga o sócio sem apagar nada: faturas vencidas continuam em aberto como dívida, e só o
        que ainda está por vir é cancelado (faturas pendentes não vencidas, convites e reservas futuras).
        """
        associado = await self._get_or_404(associado_id, for_update=True)
        if associado.status == StatusAssociado.INATIVO:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O associado já está inativo.")

        hoje = hoje_clube()
        faturas = await self.session.execute(
            update(Fatura)
            .where(
                Fatura.associado_id == associado_id,
                Fatura.status == StatusFatura.PENDENTE,
                Fatura.data_vencimento >= hoje,
            )
            .values(status=StatusFatura.CANCELADO)
        )
        convites = await self.session.execute(
            update(Convidado)
            .where(
                Convidado.associado_titular_id == associado_id,
                Convidado.status == StatusConvidado.EMITIDO,
                Convidado.data_visita >= hoje,
            )
            .values(status=StatusConvidado.CANCELADO)
        )
        reservas = await self.session.execute(
            update(AgendamentoQuadra)
            .where(
                AgendamentoQuadra.associado_id == associado_id,
                AgendamentoQuadra.status == StatusAgendamento.CONFIRMADO,
                AgendamentoQuadra.data_inicio >= clock.agora_clube().astimezone(timezone.utc),
            )
            .values(status=StatusAgendamento.CANCELADO)
        )

        associado.status = StatusAssociado.INATIVO
        associado.data_inativacao = hoje
        associado.motivo_inativacao = motivo
        await self.session.commit()
        await self.session.refresh(associado)

        return InativacaoAssociadoResponse(
            associado=(await self._enriquecer_associados([associado]))[0],
            faturas_canceladas=faturas.rowcount,
            convites_cancelados=convites.rowcount,
            reservas_canceladas=reservas.rowcount,
        )

    async def reativar_associado(self, associado_id: uuid.UUID) -> AssociadoResponse:
        """
        Traz o sócio de volta como ATIVO. Se ainda houver dívida antiga, a régua diária volta a
        tratá-lo normalmente (inclusive marcando-o como inadimplente).
        """
        associado = await self._get_or_404(associado_id, for_update=True)
        if associado.status != StatusAssociado.INATIVO:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="O associado não está inativo.")

        associado.status = StatusAssociado.ATIVO
        associado.data_inativacao = None
        associado.motivo_inativacao = None
        await self.session.commit()
        await self.session.refresh(associado)
        return (await self._enriquecer_associados([associado]))[0]

    async def atualizar_foto(self, associado_id: uuid.UUID, conteudo: bytes) -> AssociadoResponse:
        associado = await self._get_or_404(associado_id)
        extensao = foto_service.detectar_formato(conteudo)
        if extensao is None:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Formato de imagem não suportado. Envie uma foto JPG, PNG ou WEBP.",
            )

        foto_service.salvar_foto(associado_id, conteudo, extensao)
        # O parâmetro de versão força o navegador a buscar a foto nova em vez da que está em cache
        associado.foto_url = f"/api/v1/associados/{associado_id}/foto?v={int(time.time())}"
        await self.session.commit()
        await self.session.refresh(associado)
        return (await self._enriquecer_associados([associado]))[0]

    async def remover_foto(self, associado_id: uuid.UUID) -> None:
        associado = await self._get_or_404(associado_id)
        foto_service.remover_foto(associado_id)
        associado.foto_url = None
        await self.session.commit()

    async def obter_foto(self, associado_id: uuid.UUID) -> Tuple[Path, str]:
        foto = foto_service.localizar_foto(associado_id)
        if foto is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="O associado não possui foto.")
        return foto

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
