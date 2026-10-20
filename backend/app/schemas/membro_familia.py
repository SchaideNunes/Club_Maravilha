"""
Schemas Pydantic v2 dos Membros da Família (dependentes do titular).
"""
import uuid
from datetime import date, datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.cpf import validate_and_format_cpf
from app.models.membro_familia import Parentesco
from app.schemas.validators import rejeitar_null, texto_opcional, validar_data_nascimento


class MembroFamiliaBase(BaseModel):
    @field_validator("cpf", mode="before", check_fields=False)
    @classmethod
    def validar_cpf(cls, valor: Any) -> Optional[str]:
        """CPF opcional (crianças podem não ter); quando informado, precisa ser válido."""
        valor = texto_opcional(valor)
        if valor is None:
            return None
        return validate_and_format_cpf(str(valor))

    @field_validator("data_nascimento", check_fields=False)
    @classmethod
    def validar_nascimento(cls, valor: Optional[date]) -> Optional[date]:
        return validar_data_nascimento(valor)

    @field_validator("nome", mode="before", check_fields=False)
    @classmethod
    def normalizar_nome(cls, valor: Any) -> Any:
        return valor.strip() if isinstance(valor, str) else valor


class MembroFamiliaCreate(MembroFamiliaBase):
    nome: str = Field(..., min_length=3, max_length=150, example="Pedro Maravilha")
    parentesco: Parentesco
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    ativo: bool = True


class MembroFamiliaUpdate(MembroFamiliaBase):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    parentesco: Optional[Parentesco] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    ativo: Optional[bool] = None

    @field_validator("nome", "parentesco", "ativo")
    @classmethod
    def campos_obrigatorios_nao_aceitam_null(cls, valor: Any) -> Any:
        return rejeitar_null(valor)


class MembroFamiliaResponse(BaseModel):
    id: uuid.UUID
    associado_id: uuid.UUID
    nome: str
    parentesco: Parentesco
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    ativo: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
