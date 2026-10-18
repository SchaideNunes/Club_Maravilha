"""
Modelo da tabela de Logs de Mensagens de WhatsApp (auditoria dos disparos).
Todo envio tentado pela régua de cobrança ou pelo painel gera um registro,
que também garante a idempotência da régua (uma etapa por fatura).
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UUID, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.associado import Associado
    from app.models.fatura import Fatura


class EtapaRegua(str, enum.Enum):
    D_MENOS_3 = "D_MENOS_3"
    D0 = "D0"
    RECIBO = "RECIBO"
    D_MAIS_3 = "D_MAIS_3"
    D_MAIS_7 = "D_MAIS_7"
    AVULSO = "AVULSO"
    TESTE = "TESTE"


class StatusEnvio(str, enum.Enum):
    SUCESSO = "SUCESSO"
    ERRO = "ERRO"


def _agora_utc() -> datetime:
    return datetime.now(timezone.utc)


class LogMensagem(Base, UUIDPrimaryKeyMixin):
    """
    Registro imutável de uma tentativa de envio de mensagem de WhatsApp.
    Os vínculos com associado e fatura são opcionais (mensagens avulsas e de teste)
    e viram NULL, preservando o histórico, se o registro de origem for excluído.
    """
    __tablename__ = "logs_mensagens"

    associado_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("associados.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    fatura_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("faturas.id", ondelete="SET NULL"),
        nullable=True
    )

    destinatario: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número de destino no padrão Baileys (somente dígitos com DDI 55)"
    )
    etapa: Mapped[EtapaRegua] = mapped_column(
        Enum(EtapaRegua, name="etapa_regua_enum"),
        nullable=False
    )
    mensagem: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Texto final enviado, com as variáveis do template já substituídas"
    )
    status: Mapped[StatusEnvio] = mapped_column(
        Enum(StatusEnvio, name="status_envio_enum"),
        nullable=False
    )
    erro: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Detalhe da falha quando o status é ERRO"
    )
    enviado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_agora_utc,
        server_default=func.now(),
        nullable=False,
        index=True
    )

    # Relacionamentos (somente leitura de contexto para a listagem de logs)
    associado: Mapped[Optional["Associado"]] = relationship("Associado")
    fatura: Mapped[Optional["Fatura"]] = relationship("Fatura")

    # Consulta de idempotência da régua: já houve envio desta etapa para esta fatura?
    __table_args__ = (
        Index("idx_log_fatura_etapa", "fatura_id", "etapa"),
    )

    def __repr__(self) -> str:
        return (
            f"<LogMensagem(id={self.id}, destinatario='{self.destinatario}', "
            f"etapa='{self.etapa}', status='{self.status}')>"
        )
