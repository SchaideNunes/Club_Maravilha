"""
Exportação consolidada dos modelos e enums do Club Maravilha para o SQLAlchemy e Alembic.
"""
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.associado import Associado, Sexo, StatusAssociado
from app.models.plano import Plano
from app.models.membro_familia import MembroFamilia, Parentesco
from app.models.fatura import Fatura, FormaPagamento, StatusFatura
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra
from app.models.convidado import Convidado, StatusConvidado, generate_qr_token
from app.models.configuracao import Configuracao
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.models.usuario_admin import UsuarioAdmin

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "Associado",
    "StatusAssociado",
    "Sexo",
    "Plano",
    "MembroFamilia",
    "Parentesco",
    "Fatura",
    "StatusFatura",
    "FormaPagamento",
    "AgendamentoQuadra",
    "TipoQuadra",
    "StatusAgendamento",
    "Convidado",
    "StatusConvidado",
    "generate_qr_token",
    "Configuracao",
    "LogMensagem",
    "EtapaRegua",
    "StatusEnvio",
    "UsuarioAdmin",
]
