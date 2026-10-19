"""
Schemas Pydantic v2 para validação e serialização de Convidados.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.core.cpf import validate_and_format_cpf
from app.models.convidado import StatusConvidado


def _validar_cpf_opcional(valor: Any) -> Optional[str]:
    if valor is None:
        return None
    if isinstance(valor, str) and not valor.strip():
        return None
    return validate_and_format_cpf(str(valor))


class ConvidadoBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150, example="Mariana Albuquerque")
    cpf: Optional[str] = Field(None, min_length=11, max_length=14, example="987.654.321-99")
    data_visita: date = Field(..., example="2026-09-15")

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf(cls, valor: Any) -> Optional[str]:
        return _validar_cpf_opcional(valor)


class ConvidadoCreate(ConvidadoBase):
    associado_titular_id: uuid.UUID

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf_create(cls, valor: Any) -> Optional[str]:
        return _validar_cpf_opcional(valor)


class ConvidadoAssociadoCreate(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150)
    cpf: Optional[str] = None
    data_visita: Optional[date] = None

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_cpf_associado(cls, valor: Any) -> Optional[str]:
        return _validar_cpf_opcional(valor)


class ConvidadoResponse(ConvidadoBase):
    id: uuid.UUID
    associado_titular_id: uuid.UUID
    qr_code_token: str
    status: StatusConvidado
    is_gratuito: bool
    valor_cobrado: Decimal
    fatura_agregada_id: Optional[uuid.UUID] = None
    check_in_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdicionarConvidadoResponse(BaseModel):
    convidado: ConvidadoResponse
    is_gratuito: bool
    tipo: Literal["GRATUITO", "EXCEDENTE"]
    convidados_usados_mes: int
    franquia: int
    excedentes_mes: int
    valor_taxa_extra: Decimal
    aviso: Optional[str] = None


class QuotaConvidadosResponse(BaseModel):
    associado_id: uuid.UUID
    mes_referencia: str
    franquia_total: int
    utilizados: int
    restantes: int
    excedentes_emitidos: int
    valor_unitario_excedente: Decimal


class ConvidadoValidateQRRequest(BaseModel):
    token: str = Field(..., min_length=10, max_length=64, description="Token de 64 caracteres lido do QR Code")
    data_leitura: Optional[date] = Field(None, description="Data da leitura (padrão: hoje)")


class ConvidadoValidateQRResponse(BaseModel):
    valido: bool
    mensagem: str
    convidado: Optional[ConvidadoResponse] = None
