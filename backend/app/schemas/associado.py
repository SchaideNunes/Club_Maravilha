"""
Schemas Pydantic v2 para validação e serialização de Associados.
"""
import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.core.config import settings
from app.core.phone import sanitize_whatsapp_number
from app.models.associado import StatusAssociado


class AssociadoBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150, example="Carlos Eduardo Silva")
    cpf: str = Field(..., min_length=11, max_length=14, example="123.456.789-00")
    whatsapp: str = Field(..., min_length=10, max_length=20, example="+5511999998888")
    email: EmailStr = Field(..., example="carlos.silva@exemplo.com")
    foto_url: Optional[str] = Field(None, example="https://storage.clubmaravilha.com.br/fotos/carlos.webp")
    observacoes: Optional[str] = None


class AssociadoCreate(AssociadoBase):
    dia_vencimento: int = Field(
        default=settings.DIA_VENCIMENTO_PADRAO,
        ge=1,
        le=31,
        description="Dia do mês em que a mensalidade vence",
    )

    @field_validator("whatsapp")
    @classmethod
    def higienizar_whatsapp(cls, valor: str) -> str:
        """Grava o WhatsApp no padrão Baileys: somente dígitos com DDI 55."""
        return sanitize_whatsapp_number(valor)


class AssociadoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    whatsapp: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    foto_url: Optional[str] = None
    status: Optional[StatusAssociado] = None
    limite_reservas_ativas: Optional[int] = Field(None, ge=1, le=5)
    dia_vencimento: Optional[int] = Field(None, ge=1, le=31)
    observacoes: Optional[str] = None

    @field_validator("whatsapp")
    @classmethod
    def higienizar_whatsapp(cls, valor: Optional[str]) -> str:
        """Grava o WhatsApp no padrão Baileys; o campo é obrigatório no banco, então não aceita null."""
        if valor is None:
            raise ValueError("O WhatsApp não pode ser nulo.")
        return sanitize_whatsapp_number(valor)

    @field_validator("dia_vencimento")
    @classmethod
    def dia_vencimento_nao_nulo(cls, valor: Optional[int]) -> int:
        """O dia de vencimento é obrigatório no banco: pode ser omitido, mas não enviado como null."""
        if valor is None:
            raise ValueError("O dia de vencimento não pode ser nulo.")
        return valor


class AssociadoResponse(AssociadoBase):
    id: uuid.UUID
    facial_id: Optional[str] = None
    status: StatusAssociado
    limite_reservas_ativas: int
    data_adesao: date
    dia_vencimento: int
    convidados_usados_mes: int = Field(
        default=0,
        description="Convites de visitantes usados pelo sócio no mês corrente (exceto cancelados)",
    )
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAssociadosResponse(BaseModel):
    items: List[AssociadoResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ImportErrorDetail(BaseModel):
    linha: int
    campo: str
    motivo: str


class ImportAssociadosResult(BaseModel):
    total_lidos: int
    total_importados: int
    total_ignorados_duplicados: int
    erros: List[ImportErrorDetail]
