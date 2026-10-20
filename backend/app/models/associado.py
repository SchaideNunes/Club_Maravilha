"""
Modelo da tabela de Associados (Sócios do Clube).
"""
import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, Date, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.clock import hoje_clube
from app.core.config import settings
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.convidado import StatusConvidado

if TYPE_CHECKING:
    from app.models.fatura import Fatura
    from app.models.agendamento import AgendamentoQuadra
    from app.models.convidado import Convidado
    from app.models.membro_familia import MembroFamilia
    from app.models.plano import Plano


class StatusAssociado(str, enum.Enum):
    ATIVO = "ATIVO"
    INADIMPLENTE = "INADIMPLENTE"
    BLOQUEADO = "BLOQUEADO"
    # Desligado do clube: o cadastro e o histórico são preservados, mas o sócio não recebe
    # faturas nem lembretes, não entra na catraca e some da listagem padrão
    INATIVO = "INATIVO"


class Sexo(str, enum.Enum):
    MASCULINO = "MASCULINO"
    FEMININO = "FEMININO"
    OUTRO = "OUTRO"


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

    # Dados pessoais
    data_nascimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    rg: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    sexo: Mapped[Optional[Sexo]] = mapped_column(Enum(Sexo, native_enum=False, length=20), nullable=True)
    profissao: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Endereço
    cep: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)
    logradouro: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    numero: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    complemento: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    bairro: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    cidade: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    uf: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)

    # Plano de mensalidade (sem plano: vale Configuracao.valor_mensalidade)
    plano_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("planos.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    # Inativação (substitui a exclusão para preservar o histórico financeiro)
    data_inativacao: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    motivo_inativacao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relacionamentos bidirecionais
    plano: Mapped[Optional["Plano"]] = relationship("Plano", lazy="joined")
    membros_familia: Mapped[List["MembroFamilia"]] = relationship(
        "MembroFamilia",
        back_populates="associado",
        cascade="all, delete-orphan",
        order_by="MembroFamilia.nome",
    )
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
        hoje = hoje_clube()
        return self.contar_convidados_no_mes(hoje.year, hoje.month)

    def __repr__(self) -> str:
        return f"<Associado(id={self.id}, nome='{self.nome}', status='{self.status}')>"
