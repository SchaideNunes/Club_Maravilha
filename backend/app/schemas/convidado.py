"""
Schemas Pydantic v2 para validação e serialização de Convidados.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.convidado import StatusConvidado


class ConvidadoBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150, example="Mariana Albuquerque")
    cpf: Optional[str] = Field(None, min_length=11, max_length=14, example="987.654.321-99")
    data_visita: date = Field(..., example="2026-09-15")


class ConvidadoCreate(ConvidadoBase):
    associado_titular_id: uuid.UUID


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
