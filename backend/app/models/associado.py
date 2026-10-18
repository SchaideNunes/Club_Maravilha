"""
Modelo da tabela de Associados (Sócios do Clube).
"""
import enum
from datetime import date
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, Date, Enum, Integer, String, Text, func
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.config import settings
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.convidado import StatusConvidado

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
    __table_args__ = (
        CheckConstraint(
            "dia_vencimento >= 1 AND dia_vencimento <= 31",
            name="ck_associados_dia_vencimento",
        ),
    )

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
    dia_vencimento: Mapped[int] = mapped_column(
        Integer,
        default=settings.DIA_VENCIMENTO_PADRAO,
        nullable=False,
        comment="Dia do mês (1-31) em que a mensalidade do sócio vence"
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

    def contar_convidados_no_mes(self, ano: int, mes: int) -> int:
        """
        Conta os convites do titular cuja visita cai no mês informado (convites
        CANCELADOS não consomem a franquia).

        Opera sobre a relação `convidados`, que precisa estar carregada
        (ex: `selectinload(Associado.convidados)`) para evitar IO implícito.
        """
        return sum(
            1
            for convidado in self.convidados
            if convidado.status != StatusConvidado.CANCELADO
            and convidado.data_visita.year == ano
            and convidado.data_visita.month == mes
        )

    @property
    def convidados_usados_mes(self) -> int:
        """
        Convites usados pelo titular no mês corrente (exposto na API).
        Retorna 0 sem disparar lazy-load quando a relação `convidados` não foi
        carregada, o que torna seguro serializar o modelo em contexto assíncrono.
        """
        if "convidados" in sa_inspect(self).unloaded:
            return 0
        hoje = date.today()
        return self.contar_convidados_no_mes(hoje.year, hoje.month)

    def __repr__(self) -> str:
        return f"<Associado(id={self.id}, nome='{self.nome}', status='{self.status}')>"
