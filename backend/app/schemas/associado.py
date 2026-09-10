"""
Schemas Pydantic v2 para validação e serialização de Associados.
"""
import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.associado import StatusAssociado


class AssociadoBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150, example="Carlos Eduardo Silva")
    cpf: str = Field(..., min_length=11, max_length=14, example="123.456.789-00")
    whatsapp: str = Field(..., min_length=10, max_length=20, example="+5511999998888")
    email: EmailStr = Field(..., example="carlos.silva@exemplo.com")
    foto_url: Optional[str] = Field(None, example="https://storage.clubmaravilha.com.br/fotos/carlos.webp")
    observacoes: Optional[str] = None


class AssociadoCreate(AssociadoBase):
    pass


class AssociadoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    whatsapp: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    foto_url: Optional[str] = None
    status: Optional[StatusAssociado] = None
    limite_reservas_ativas: Optional[int] = Field(None, ge=1, le=5)
    observacoes: Optional[str] = None


class AssociadoResponse(AssociadoBase):
    id: uuid.UUID
    facial_id: Optional[str] = None
    status: StatusAssociado
    limite_reservas_ativas: int
    data_adesao: date
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
