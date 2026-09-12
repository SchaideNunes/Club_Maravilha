"""
Serviço de Negócio para Agendamento de Quadras com Concorrência Atômica.
Garante bloqueios contra double-booking, inadimplência e respeito ao teto de reservas.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra
from app.models.associado import StatusAssociado
from app.models.fatura import StatusFatura
from app.repositories.agendamento_repository import AgendamentoRepository
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.schemas.agendamento import (
    AgendamentoCreate,
    DisponibilidadeDiaResponse,
    SlotDisponibilidade,
)


class AgendamentoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.agendamento_repo = AgendamentoRepository(session)
        self.associado_repo = AssociadoRepository(session)
        self.fatura_repo = FaturaRepository(session)

    async def get_by_id(self, agendamento_id: uuid.UUID) -> AgendamentoQuadra:
        agendamento = await self.agendamento_repo.get_by_id(agendamento_id)
        if not agendamento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agendamento não encontrado."
            )
        return agendamento

    async def list_agendamentos(
        self,
        quadra: Optional[TipoQuadra] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        associado_id: Optional[uuid.UUID] = None,
        status_filter: Optional[StatusAgendamento] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgendamentoQuadra]:
        return await self.agendamento_repo.list_agendamentos(
            quadra=quadra,
            data_inicio=data_inicio,
            data_fim=data_fim,
            associado_id=associado_id,
            status=status_filter,
            skip=skip,
            limit=limit
        )

    async def create_agendamento(self, data: AgendamentoCreate) -> AgendamentoQuadra:
        """
        Cria uma reserva de quadra aplicando travas atômicas e validações de integridade:
        1. Associado deve existir e estar ATIVO.
        2. Associado não pode ter faturas com status VENCIDO.
        3. Horário deve ser futuro.
        4. Teto de reservas ativas simultâneas respeitado.
        5. Bloqueio atômico com verificação de sobreposição (SELECT ... FOR UPDATE).
        """
        # 1. Validação do Associado
        associado = await self.associado_repo.get_by_id(data.associado_id)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado."
            )
        if associado.status != StatusAssociado.ATIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Associado não pode reservar quadras. Status cadastral: {associado.status}."
            )

        # 2. Validação contra Inadimplência Financeira
        faturas_vencidas = await self.fatura_repo.list_faturas(
            associado_id=data.associado_id,
            status=StatusFatura.VENCIDO
        )
        if faturas_vencidas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Reserva bloqueada: associado possui mensalidade vencida em aberto."
            )

        # 3. Validação de Horário Futuro
        agora = datetime.now(timezone.utc)
        # Converte para timezone-aware se necessário
        inicio = data.data_inicio if data.data_inicio.tzinfo else data.data_inicio.replace(tzinfo=timezone.utc)
        fim = data.data_fim if data.data_fim.tzinfo else data.data_fim.replace(tzinfo=timezone.utc)

        if inicio < agora:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível reservar horários retroativos no passado."
            )

        # 4. Teto de Reservas Ativas Simultâneas
        reservas_ativas = await self.agendamento_repo.contar_reservas_ativas(
            associado_id=data.associado_id,
            a_partir_de=agora
        )
        teto = associado.limite_reservas_ativas or settings.LIMITE_RESERVAS_SIMULTANEAS_PADRAO
        if reservas_ativas >= teto:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Limite de reservas ativas atingido ({reservas_ativas}/{teto}). "
                    "Conclua ou cancele um agendamento anterior para reservar novamente."
                )
            )

        # 5. Trava Atômica de Concorrência contra Double-Booking
        conflito = await self.agendamento_repo.verificar_sobreposicao(
            quadra=data.quadra,
            data_inicio=inicio,
            data_fim=fim,
            for_update=True
        )
        if conflito:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Horário indisponível. Já existe uma reserva confirmada para este período na quadra selecionada."
            )

        agendamento = AgendamentoQuadra(
            associado_id=data.associado_id,
            quadra=data.quadra,
            data_inicio=inicio,
            data_fim=fim,
            observacoes=data.observacoes,
            status=StatusAgendamento.CONFIRMADO
        )

        created = await self.agendamento_repo.create(agendamento)
        await self.session.commit()
        await self.session.refresh(created)
        return created

    async def cancel_agendamento(self, agendamento_id: uuid.UUID) -> AgendamentoQuadra:
        """
        Cancela um agendamento confirmado, respeitando a política de antecedência mínima de 2 horas.
        """
        agendamento = await self.get_by_id(agendamento_id)
        if agendamento.status != StatusAgendamento.CONFIRMADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não é possível cancelar agendamento com status '{agendamento.status}'."
            )

        agora = datetime.now(timezone.utc)
        inicio = (
            agendamento.data_inicio
            if agendamento.data_inicio.tzinfo
            else agendamento.data_inicio.replace(tzinfo=timezone.utc)
        )
        segundos_restantes = (inicio - agora).total_seconds()

        # Antecedência mínima de 2 horas (7200 segundos)
        if segundos_restantes < 2 * 3600:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cancelamento permitido apenas com antecedência mínima de 2 horas do início da partida."
            )

        agendamento.status = StatusAgendamento.CANCELADO
        await self.session.commit()
        await self.session.refresh(agendamento)
        return agendamento

    async def get_disponibilidade_dia(
        self,
        quadra: TipoQuadra,
        data_consulta: date
    ) -> DisponibilidadeDiaResponse:
        """
        Retorna a grade de slots de 60 minutos entre 06:00 e 22:00 para a data informada,
        indicando disponibilidade ou ID da reserva existente.
        """
        inicio_dia = datetime.combine(data_consulta, time(6, 0), tzinfo=timezone.utc)
        fim_dia = datetime.combine(data_consulta, time(22, 0), tzinfo=timezone.utc)

        agendamentos = await self.agendamento_repo.list_agendamentos(
            quadra=quadra,
            data_inicio=inicio_dia,
            data_fim=fim_dia,
            status=StatusAgendamento.CONFIRMADO
        )

        slots: List[SlotDisponibilidade] = []
        cursor = inicio_dia
        while cursor < fim_dia:
            slot_fim = cursor + timedelta(hours=1)
            # Verifica se há reserva interceptando este slot
            reserva_ocupada = next(
                (
                    ag for ag in agendamentos
                    if (
                        (ag.data_inicio if ag.data_inicio.tzinfo else ag.data_inicio.replace(tzinfo=timezone.utc)) < slot_fim
                        and (ag.data_fim if ag.data_fim.tzinfo else ag.data_fim.replace(tzinfo=timezone.utc)) > cursor
                    )
                ),
                None
            )
            slots.append(
                SlotDisponibilidade(
                    data_inicio=cursor,
                    data_fim=slot_fim,
                    disponivel=reserva_ocupada is None,
                    agendamento_id=reserva_ocupada.id if reserva_ocupada else None
                )
            )
            cursor = slot_fim

        return DisponibilidadeDiaResponse(
            quadra=quadra,
            data=inicio_dia,
            slots=slots
        )
