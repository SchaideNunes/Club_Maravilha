"""
Repositório de dados para a entidade de Associados.
Segue o princípio de isolamento de persistência da Clean Architecture.
"""
import calendar
from datetime import date
import re
from typing import Dict, List, Optional, Sequence, Tuple
import uuid
from sqlalchemy import func, or_, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.schemas.associado import (
    AssociadoCreate,
    AssociadoUpdate,
    ImportErrorDetail,
    SituacaoFinanceira,
)


class AssociadoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        associado_id: uuid.UUID,
        com_convidados: bool = False
    ) -> Optional[Associado]:
        """
        Busca o associado pelo ID. Com `com_convidados=True` carrega a relação de convidados
        (necessária para `Associado.convidados_usados_mes` refletir o mês corrente na API).
        """
        query = select(Associado).where(Associado.id == associado_id)
        if com_convidados:
            query = query.options(selectinload(Associado.convidados))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_cpf(self, cpf: str) -> Optional[Associado]:
        """Busca associado por CPF (aceita com ou sem máscara de pontuação)."""
        clean_cpf = re.sub(r"\D", "", cpf)
        query = select(Associado).where(
            or_(
                Associado.cpf == cpf,
                func.replace(func.replace(Associado.cpf, ".", ""), "-", "") == clean_cpf
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Associado]:
        """Busca associado por e-mail de forma estritamente case-insensitive."""
        query = select(Associado).where(func.lower(Associado.email) == email.lower().strip())
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def contar_convidados_mes(
        self,
        associado_ids: Sequence[uuid.UUID],
        ano: int,
        mes: int
    ) -> Dict[uuid.UUID, int]:
        """
        Retorna mapa {associado_id: total_convidados_ativos_no_mes} em uma ÚNICA query agregada.
        Ignora convites com status CANCELADO. Se a lista for vazia, não consulta o banco.
        """
        if not associado_ids:
            return {}

        _, last_day = calendar.monthrange(ano, mes)
        dt_inicio = date(ano, mes, 1)
        dt_fim = date(ano, mes, last_day)

        query = (
            select(Convidado.associado_titular_id, func.count(Convidado.id))
            .where(
                Convidado.associado_titular_id.in_(associado_ids),
                Convidado.data_visita >= dt_inicio,
                Convidado.data_visita <= dt_fim,
                Convidado.status != StatusConvidado.CANCELADO,
            )
            .group_by(Convidado.associado_titular_id)
        )
        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def situacoes_financeiras(
        self,
        associado_ids: Sequence[uuid.UUID],
        referencia_mes: str
    ) -> Dict[uuid.UUID, SituacaoFinanceira]:
        """
        Retorna mapa {associado_id: SituacaoFinanceira} derivado das faturas em aberto
        (PENDENTE/ATRASADA) com referencia_mes <= referencia_mes informado em UMA ÚNICA query.
        ATRASADA em qualquer mês <= ref prevalece sobre PENDENTE.
        Ids ausentes do retorno equivalem a EM_DIA.
        """
        if not associado_ids:
            return {}

        query = (
            select(Fatura.associado_id, Fatura.status)
            .where(
                Fatura.associado_id.in_(associado_ids),
                Fatura.status.in_([StatusFatura.PENDENTE, StatusFatura.ATRASADA]),
                Fatura.referencia_mes <= referencia_mes,
            )
        )
        result = await self.session.execute(query)
        situacoes: Dict[uuid.UUID, SituacaoFinanceira] = {}
        for assoc_id, status in result.all():
            if situacoes.get(assoc_id) == SituacaoFinanceira.ATRASADO:
                continue
            if status == StatusFatura.ATRASADA:
                situacoes[assoc_id] = SituacaoFinanceira.ATRASADO
            else:
                situacoes[assoc_id] = SituacaoFinanceira.PENDENTE
        return situacoes

    async def list_paginated(
        self,
        skip: int = 0,
        limit: int = 50,
        q: Optional[str] = None,
        status: Optional[StatusAssociado] = None,
        situacao: Optional[SituacaoFinanceira] = None,
        referencia_mes: Optional[str] = None,
    ) -> Tuple[List[Associado], int]:
        """
        Retorna lista paginada e total de registros com busca textual em Nome, CPF ou Email,
        e filtro por status cadastral ou situação financeira.
        Não carrega histórico de convidados para garantir alta performance e evitar N+1.
        """
        base_query = select(Associado)
        count_query = select(func.count(Associado.id))

        filters = []
        if status:
            filters.append(Associado.status == status)

        if q:
            term = f"%{q.strip()}%"
            q_digits = re.sub(r"\D", "", q.strip())
            q_conditions = [
                Associado.nome.ilike(term),
                Associado.cpf.like(term),
                Associado.email.ilike(term),
            ]
            if len(q_digits) >= 1:
                q_conditions.append(
                    func.replace(func.replace(Associado.cpf, ".", ""), "-", "").like(f"%{q_digits}%")
                )
            filters.append(or_(*q_conditions))

        if situacao:
            ref = referencia_mes or f"{date.today().year:04d}-{date.today().month:02d}"
            if situacao == SituacaoFinanceira.ATRASADO:
                subq_atrasada = (
                    select(Fatura.associado_id)
                    .where(
                        Fatura.status == StatusFatura.ATRASADA,
                        Fatura.referencia_mes <= ref,
                    )
                )
                filters.append(Associado.id.in_(subq_atrasada))
            elif situacao == SituacaoFinanceira.PENDENTE:
                subq_pendente = (
                    select(Fatura.associado_id)
                    .where(
                        Fatura.status == StatusFatura.PENDENTE,
                        Fatura.referencia_mes <= ref,
                    )
                )
                subq_atrasada = (
                    select(Fatura.associado_id)
                    .where(
                        Fatura.status == StatusFatura.ATRASADA,
                        Fatura.referencia_mes <= ref,
                    )
                )
                filters.append(Associado.id.in_(subq_pendente))
                filters.append(Associado.id.not_in(subq_atrasada))
            elif situacao == SituacaoFinanceira.EM_DIA:
                subq_abertas = (
                    select(Fatura.associado_id)
                    .where(
                        Fatura.status.in_([StatusFatura.PENDENTE, StatusFatura.ATRASADA]),
                        Fatura.referencia_mes <= ref,
                    )
                )
                filters.append(Associado.id.not_in(subq_abertas))

        if filters:
            base_query = base_query.where(*filters)
            count_query = count_query.where(*filters)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            base_query
            .offset(skip)
            .limit(limit)
            .order_by(Associado.nome.asc())
        )
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
            dia_vencimento=associado_in.dia_vencimento,
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
        # Garante a relação carregada caso o associado tenha vindo sem convidados
        if "convidados" in sa_inspect(associado).unloaded:
            await self.session.refresh(associado, attribute_names=["convidados"])
        return associado

    async def delete(self, associado_id: uuid.UUID) -> bool:
        associado = await self.get_by_id(associado_id)
        if not associado:
            return False
        await self.session.delete(associado)
        await self.session.flush()
        return True

    async def bulk_import(
        self,
        members: List[AssociadoCreate],
        atualizar_existentes: bool = False
    ) -> Tuple[int, int, int, List[ImportErrorDetail]]:
        """
        Insere ou atualiza múltiplos associados.
        - Se atualizar_existentes=False: CPF já cadastrado é ignorado.
        - Se atualizar_existentes=True: CPF já cadastrado é atualizado (preservando status e faturas).
        - Conflito de e-mail com outro associado é registrado como erro da linha.
        Retorna (total_importados, total_atualizados, total_ignorados, erros).
        """
        imported_count = 0
        updated_count = 0
        ignored_count = 0
        db_errors: List[ImportErrorDetail] = []

        for m in members:
            line_num = getattr(m, "_line_num", 0)
            existing_cpf = await self.get_by_cpf(m.cpf)

            if existing_cpf:
                if not atualizar_existentes:
                    ignored_count += 1
                    continue

                # Modo upsert: verifica se o e-mail pertence a OUTRO sócio
                existing_email = await self.get_by_email(m.email)
                if existing_email and existing_email.id != existing_cpf.id:
                    db_errors.append(ImportErrorDetail(
                        linha=line_num,
                        campo="email",
                        motivo=f"E-mail '{m.email}' já pertence a outro associado cadastrado."
                    ))
                    continue

                existing_cpf.nome = m.nome
                existing_cpf.whatsapp = m.whatsapp
                existing_cpf.email = m.email
                existing_cpf.dia_vencimento = m.dia_vencimento
                if m.foto_url is not None:
                    existing_cpf.foto_url = m.foto_url
                if m.observacoes is not None:
                    existing_cpf.observacoes = m.observacoes
                self.session.add(existing_cpf)
                updated_count += 1
            else:
                # Novo sócio: verifica se o e-mail já está em uso
                existing_email = await self.get_by_email(m.email)
                if existing_email:
                    db_errors.append(ImportErrorDetail(
                        linha=line_num,
                        campo="email",
                        motivo=f"E-mail '{m.email}' já pertence a outro associado cadastrado."
                    ))
                    continue

                associado = Associado(
                    nome=m.nome,
                    cpf=m.cpf,
                    whatsapp=m.whatsapp,
                    email=m.email,
                    foto_url=m.foto_url,
                    observacoes=m.observacoes,
                    dia_vencimento=m.dia_vencimento,
                    status=StatusAssociado.ATIVO,
                )
                self.session.add(associado)
                imported_count += 1

        await self.session.flush()
        return imported_count, updated_count, ignored_count, db_errors
