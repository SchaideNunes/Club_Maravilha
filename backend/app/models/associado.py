"""
Modelo da tabela de Associados (Sócios do Clube).
"""
import enum
from datetime import date
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Date, Enum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.fatura import Fatura
    from app.models.agendamento import AgendamentoQuadra
    from app.models.convidado import Convidado


class StatusAssociado(str, enum.Enum):
    ATIVO = "ATIVO"
    INADIMPLENTE = "INADIMPLENTE"
    BLOQUEADO = "BLOQUEADO"


class Associado(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Entidade de Associado (~300 membros do Club Maravilha).
    Armazena dados cadastrais, status para liberação física na catraca
    e relacionamentos com faturas, agendamentos e convidados.
    """
    __tablename__ = "associados"

    nome: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    cpf: Mapped[str] = mapped_column(String(14), unique=True, index=True, nullable=False)
    whatsapp: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    
    # Foto e Identificador para integração com Catraca Facial (Lista Branca Offline)
    foto_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    facial_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True, index=True)
    
    # Status de Acesso e Regras de Negócio
    status: Mapped[StatusAssociado] = mapped_column(
        Enum(StatusAssociado, name="status_associado_enum"),
        default=StatusAssociado.ATIVO,
        nullable=False,
        index=True
    )
    limite_reservas_ativas: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
        comment="Limite máximo de agendamentos futuros simultâneos para evitar monopólio de quadras"
    )
    data_adesao: Mapped[date] = mapped_column(
        Date,
        server_default=func.current_date(),
        nullable=False
    )
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relacionamentos bidirecionais
    faturas: Mapped[List["Fatura"]] = relationship(
        "Fatura",
        back_populates="associado",
        cascade="all, delete-orphan",
        order_by="desc(Fatura.data_vencimento)"
    )
    agendamentos: Mapped[List["AgendamentoQuadra"]] = relationship(
        "AgendamentoQuadra",
        back_populates="associado",
        cascade="all, delete-orphan",
        order_by="desc(AgendamentoQuadra.data_inicio)"
    )
    convidados: Mapped[List["Convidado"]] = relationship(
        "Convidado",
        back_populates="associado_titular",
        cascade="all, delete-orphan",
        order_by="desc(Convidado.data_visita)"
    )

    def __repr__(self) -> str:
        return f"<Associado(id={self.id}, nome='{self.nome}', status='{self.status}')>"
