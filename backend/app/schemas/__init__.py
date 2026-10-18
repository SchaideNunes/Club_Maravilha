"""
Consolidação dos Schemas Pydantic v2 do Club Maravilha.
"""
from app.schemas.associado import (
    AssociadoBase,
    AssociadoCreate,
    AssociadoResponse,
    AssociadoUpdate,
    PaginatedAssociadosResponse,
    ImportErrorDetail,
    ImportAssociadosResult,
)
from app.schemas.fatura import (
    FaturaBase,
    FaturaBaixaManual,
    FaturaCreate,
    FaturaResponse,
)
from app.schemas.agendamento import (
    AgendamentoBase,
    AgendamentoCreate,
    AgendamentoResponse,
)
from app.schemas.convidado import (
    ConvidadoBase,
    ConvidadoCreate,
    ConvidadoResponse,
)
from app.schemas.configuracao import (
    ConfiguracaoResponse,
    ConfiguracaoUpdate,
)
from app.schemas.log_mensagem import LogMensagemResponse

__all__ = [
    "AssociadoBase",
    "AssociadoCreate",
    "AssociadoUpdate",
    "AssociadoResponse",
    "PaginatedAssociadosResponse",
    "ImportErrorDetail",
    "ImportAssociadosResult",
    "FaturaBase",
    "FaturaBaixaManual",
    "FaturaCreate",
    "FaturaResponse",
    "AgendamentoBase",
    "AgendamentoCreate",
    "AgendamentoResponse",
    "ConvidadoBase",
    "ConvidadoCreate",
    "ConvidadoResponse",
    "ConfiguracaoResponse",
    "ConfiguracaoUpdate",
    "LogMensagemResponse",
]
