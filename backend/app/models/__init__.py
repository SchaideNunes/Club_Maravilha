"""
Exportação consolidada dos modelos e enums do Club Maravilha para o SQLAlchemy e Alembic.
"""
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra
from app.models.convidado import Convidado, StatusConvidado, generate_qr_token

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "Associado",
    "StatusAssociado",
    "Fatura",
    "StatusFatura",
    "FormaPagamento",
    "AgendamentoQuadra",
    "TipoQuadra",
    "StatusAgendamento",
    "Convidado",
    "StatusConvidado",
    "generate_qr_token",
]
