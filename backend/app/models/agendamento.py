"""
Modelo da tabela de Agendamentos de Quadras Esportivas com suporte a regras de concorrência.
"""
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.associado import Associado


class TipoQuadra(str, enum.Enum):
    TENIS_1 = "TENIS_1"
    TENIS_2 = "TENIS_2"
    BEACH_TENNIS_1 = "BEACH_TENNIS_1"
    BEACH_TENNIS_2 = "BEACH_TENNIS_2"
    FUTEBOL_SOCIETY = "FUTEBOL_SOCIETY"


class StatusAgendamento(str, enum.Enum):
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"
    CONCLUIDO = "CONCLUIDO"
    NO_SHOW = "NO_SHOW"


class AgendamentoQuadra(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Entidade de Reserva de Quadra Esportiva.
    Regras de Negócio associadas:
    1. Sócios inadimplentes ou bloqueados não podem reservar.
    2. Cada sócio possui teto de reservas ativas simultâneas (padrão: 2).
    3. Concorrência atômica: bloqueia sobreposição de horários na mesma quadra.
    """
    __tablename__ = "agendamentos_quadras"

    associado_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("associados.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    quadra: Mapped[TipoQuadra] = mapped_column(
        Enum(TipoQuadra, name="tipo_quadra_enum"),
        nullable=False,
        index=True
    )
    
    data_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    data_fim: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    status: Mapped[StatusAgendamento] = mapped_column(
        Enum(StatusAgendamento, name="status_agendamento_enum"),
        default=StatusAgendamento.CONFIRMADO,
        nullable=False,
        index=True
    )
    observacoes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relacionamento
    associado: Mapped["Associado"] = relationship("Associado", back_populates="agendamentos")

    # Índice composto para otimizar busca de disponibilidade e checagem de sobreposição de horários
    __table_args__ = (
        Index("idx_quadra_horario", "quadra", "data_inicio", "data_fim"),
    )

    def __repr__(self) -> str:
        return (
            f"<AgendamentoQuadra(id={self.id}, quadra='{self.quadra}', "
            f"inicio='{self.data_inicio}', status='{self.status}')>"
        )
