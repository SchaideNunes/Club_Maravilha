"""
Schemas Pydantic v2 dos Planos de mensalidade.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.validators import rejeitar_null


class PlanoCreate(BaseModel):
    nome: str = Field(..., min_length=2, max_length=80, example="Familiar")
    descricao: Optional[str] = Field(None, max_length=500)
    valor_mensalidade: Decimal = Field(..., ge=0, max_digits=10, decimal_places=2, example="220.00")

    @field_validator("nome", mode="before")
    @classmethod
    def normalizar_nome(cls, valor: Any) -> Any:
        return valor.strip() if isinstance(valor, str) else valor


class PlanoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=80)
    descricao: Optional[str] = Field(None, max_length=500)
    valor_mensalidade: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    ativo: Optional[bool] = None

    @field_validator("nome", mode="before")
    @classmethod
    def normalizar_nome(cls, valor: Any) -> Any:
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("nome", "valor_mensalidade", "ativo")
    @classmethod
    def campos_obrigatorios_nao_aceitam_null(cls, valor: Any) -> Any:
        return rejeitar_null(valor)


class PlanoResumo(BaseModel):
    """Plano embutido na resposta do associado."""
    id: uuid.UUID
    nome: str
    valor_mensalidade: Decimal

    model_config = ConfigDict(from_attributes=True)


class PlanoResponse(PlanoResumo):
    descricao: Optional[str] = None
    ativo: bool
    total_associados: int = Field(default=0, description="Sócios não inativos vinculados ao plano")
    created_at: datetime
    updated_at: datetime
