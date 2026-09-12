"""
Modelo da tabela de Convidados com controle da franquia de 8 convites mensais e QR Code temporário.
"""
import enum
import secrets
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.associado import Associado
    from app.models.fatura import Fatura


class StatusConvidado(str, enum.Enum):
    EMITIDO = "EMITIDO"
    UTILIZADO = "UTILIZADO"
    EXPIRADO = "EXPIRADO"
    CANCELADO = "CANCELADO"


def generate_qr_token() -> str:
    """Gera um token criptográfico seguro de 32 bytes em hexadecimal (64 caracteres) para o QR Code."""
    return secrets.token_hex(32)


class Convidado(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Entidade de Convite para Visitante.
    Regras de Negócio associadas:
    1. Cada titular tem franquia de até 8 convites mensais gratuitos (reinicia no dia 1º).
    2. A partir do 9º convite no mês corrente, o convite é emitido com is_gratuito=False
       e acumula taxa (R$ 35,00) que é somada na próxima fatura Pix mensal do titular.
    3. Emissão de QR Code temporário para liberação exclusiva no dia marcado.
    """
    __tablename__ = "convidados"

    associado_titular_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("associados.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    cpf: Mapped[Optional[str]] = mapped_column(String(14), nullable=True, index=True)
    data_visita: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Token seguro gerado para leitura ótica na catraca
    qr_code_token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        default=generate_qr_token,
        nullable=False,
        index=True
    )
    
    status: Mapped[StatusConvidado] = mapped_column(
        Enum(StatusConvidado, name="status_convidado_enum"),
        default=StatusConvidado.EMITIDO,
        nullable=False,
        index=True
    )
    
    # Regra da Franquia de 8 e Cobrança Agregada
    is_gratuito: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Indica se o convite foi emitido dentro da franquia gratuita de 8 do mês"
    )
    valor_cobrado: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Valor cobrado se for excedente (ex: R$ 35.00)"
    )
    
    # Vínculo com a fatura onde a cobrança foi agregada
    fatura_agregada_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("faturas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Fatura mensal em que este convite excedente foi cobrado"
    )
    
    check_in_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Momento exato em que o QR Code foi bipado na catraca de visitantes"
    )

    # Relacionamentos
    associado_titular: Mapped["Associado"] = relationship("Associado", back_populates="convidados")
    fatura_agregada: Mapped[Optional["Fatura"]] = relationship("Fatura", back_populates="convidados_faturados")

    def __repr__(self) -> str:
        return (
            f"<Convidado(id={self.id}, nome='{self.nome}', data='{self.data_visita}', "
            f"gratuito={self.is_gratuito}, status='{self.status}')>"
        )
