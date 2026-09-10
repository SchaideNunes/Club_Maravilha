"""
Consolidação dos Schemas Pydantic v2 do Club Maravilha.
"""
from app.schemas.associado import (
    AssociadoBase,
    AssociadoCreate,
    AssociadoResponse,
    AssociadoUpdate,
)
from app.schemas.fatura import (
    FaturaBase,
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

__all__ = [
    "AssociadoBase",
    "AssociadoCreate",
    "AssociadoUpdate",
    "AssociadoResponse",
    "FaturaBase",
    "FaturaCreate",
    "FaturaResponse",
    "AgendamentoBase",
    "AgendamentoCreate",
    "AgendamentoResponse",
    "ConvidadoBase",
    "ConvidadoCreate",
    "ConvidadoResponse",
]
