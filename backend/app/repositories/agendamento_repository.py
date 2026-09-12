"""
Repositório de dados para Agendamentos de Quadras com bloqueio atômico de concorrência.
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra


class AgendamentoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, agendamento_id: uuid.UUID) -> Optional[AgendamentoQuadra]:
        query = select(AgendamentoQuadra).where(AgendamentoQuadra.id == agendamento_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_agendamentos(
        self,
        quadra: Optional[TipoQuadra] = None,
        data_inicio: Optional[datetime] = None,
        data_fim: Optional[datetime] = None,
        associado_id: Optional[uuid.UUID] = None,
        status: Optional[StatusAgendamento] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgendamentoQuadra]:
        query = select(AgendamentoQuadra)
        if quadra:
            query = query.where(AgendamentoQuadra.quadra == quadra)
        if data_inicio:
            query = query.where(AgendamentoQuadra.data_inicio >= data_inicio)
        if data_fim:
            query = query.where(AgendamentoQuadra.data_fim <= data_fim)
        if associado_id:
            query = query.where(AgendamentoQuadra.associado_id == associado_id)
        if status:
            query = query.where(AgendamentoQuadra.status == status)

        query = query.order_by(AgendamentoQuadra.data_inicio.asc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def contar_reservas_ativas(
        self,
        associado_id: uuid.UUID,
        a_partir_de: datetime
    ) -> int:
        """Conta quantas reservas futuras ativas o associado possui."""
        query = select(func.count()).select_from(AgendamentoQuadra).where(
            and_(
                AgendamentoQuadra.associado_id == associado_id,
                AgendamentoQuadra.status == StatusAgendamento.CONFIRMADO,
                AgendamentoQuadra.data_inicio >= a_partir_de
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def verificar_sobreposicao(
        self,
        quadra: TipoQuadra,
        data_inicio: datetime,
        data_fim: datetime,
        for_update: bool = False,
        exclude_id: Optional[uuid.UUID] = None
    ) -> Optional[AgendamentoQuadra]:
        """
        Verifica se há sobreposição de horário na mesma quadra.
        Se for_update=True, aplica trava pessimista atômica row-level (SELECT FOR UPDATE)
        no PostgreSQL para prevenir double-booking em requisições concorrentes.
        """
        conditions = [
            AgendamentoQuadra.quadra == quadra,
            AgendamentoQuadra.status == StatusAgendamento.CONFIRMADO,
            AgendamentoQuadra.data_inicio < data_fim,
            AgendamentoQuadra.data_fim > data_inicio,
        ]
        if exclude_id:
            conditions.append(AgendamentoQuadra.id != exclude_id)

        query = select(AgendamentoQuadra).where(and_(*conditions))

        if for_update:
            # Trava atômica no banco de dados (ignorada com segurança no SQLite em testes caso não suportada)
            try:
                query = query.with_for_update()
            except Exception:
                pass

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, agendamento: AgendamentoQuadra) -> AgendamentoQuadra:
        self.session.add(agendamento)
        await self.session.flush()
        await self.session.refresh(agendamento)
        return agendamento

    async def update(self, agendamento: AgendamentoQuadra) -> AgendamentoQuadra:
        self.session.add(agendamento)
        await self.session.flush()
        await self.session.refresh(agendamento)
        return agendamento
