"""
Modelo da tabela de Mensalidades / Faturas com suporte a Pix Dinâmico e Webhooks.
"""
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, JSON, UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.associado import Associado
    from app.models.convidado import Convidado


class StatusFatura(str, enum.Enum):
    PENDENTE = "PENDENTE"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"
    VENCIDO = "VENCIDO"


class FormaPagamento(str, enum.Enum):
    PIX = "PIX"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    DINHEIRO = "DINHEIRO"
    BOLETO = "BOLETO"


class Fatura(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Entidade de Fatura / Mensalidade.
    Contempla o valor base da mensalidade somado aos convidados excedentes,
    geração de Pix dinâmico com txid exclusivo e auditoria de webhooks.
    """
    __tablename__ = "faturas"

    associado_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("associados.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    referencia_mes: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        index=True,
        comment="Mês de referência no formato AAAA-MM (Ex: 2026-09)"
    )
    
    # Composição de Valores Financeiros
    valor_base: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Valor da mensalidade padrão"
    )
    valor_convidados_excedentes: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="Soma das taxas de convidados que excederam a franquia de 8 no mês anterior"
    )
    valor_desconto: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    valor_total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Valor final líquido da fatura (base + excedentes - desconto)"
    )
    
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    data_pagamento: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data e hora exata da liquidação confirmada via Webhook"
    )
    
    status: Mapped[StatusFatura] = mapped_column(
        Enum(StatusFatura, name="status_fatura_enum"),
        default=StatusFatura.PENDENTE,
        nullable=False,
        index=True
    )
    forma_pagamento: Mapped[FormaPagamento] = mapped_column(
        Enum(FormaPagamento, name="forma_pagamento_enum"),
        default=FormaPagamento.PIX,
        nullable=False
    )
    
    # Integração Pix Dinâmico
    txid: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
        comment="Identificador único da transação Pix para conciliação automática"
    )
    pix_copia_cola: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pix_qr_code_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Auditoria de Webhook Instantâneo
    metadata_webhook: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
        comment="Payload JSON bruto retornado pelo gateway de pagamento"
    )

    # Rastreabilidade e Idempotência da Régua de Cobrança (WhatsApp)
    notificado_d_minus_3_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do envio do aviso amigável D-3"
    )
    notificado_d_zero_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do envio matinal do Pix Copia e Cola no dia do vencimento D-0"
    )
    notificado_d_plus_3_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora da notificação de atraso D+3"
    )
    notificado_d_plus_7_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do alerta de bloqueio e transição para inadimplente D+7"
    )
    notificado_pos_pagamento_em: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data/hora do envio de recibo e confirmação de catraca liberada"
    )

    # Relacionamentos
    associado: Mapped["Associado"] = relationship("Associado", back_populates="faturas")
    convidados_faturados: Mapped[List["Convidado"]] = relationship(
        "Convidado",
        back_populates="fatura_agregada"
    )

    def __repr__(self) -> str:
        return f"<Fatura(id={self.id}, mes='{self.referencia_mes}', valor={self.valor_total}, status='{self.status}')>"
