"""
Schemas Pydantic v2 para validação e serialização de Associados.
"""
import enum
import uuid
from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, PrivateAttr, field_validator
from app.core.config import settings
from app.core.cpf import validate_and_format_cpf
from app.core.phone import sanitize_whatsapp_number
from app.models.associado import StatusAssociado
from app.schemas.validators import rejeitar_null


class SituacaoFinanceira(str, enum.Enum):
    EM_DIA = "EM_DIA"
    PENDENTE = "PENDENTE"
    ATRASADO = "ATRASADO"


class AssociadoBase(BaseModel):
    nome: str = Field(..., min_length=3, max_length=150, example="Carlos Eduardo Silva")
    cpf: str = Field(..., example="123.456.789-00")
    whatsapp: str = Field(..., min_length=10, max_length=20, example="+5511999998888")
    email: EmailStr = Field(..., example="carlos.silva@exemplo.com")
    foto_url: Optional[str] = Field(None, example="https://storage.clubmaravilha.com.br/fotos/carlos.webp")
    observacoes: Optional[str] = None


class AssociadoCreate(AssociadoBase):
    _line_num: int = PrivateAttr(default=0)
    dia_vencimento: int = Field(
        default=settings.DIA_VENCIMENTO_PADRAO,
        ge=1,
        le=31,
        description="Dia do mês em que a mensalidade vence",
    )

    @field_validator("cpf", mode="before")
    @classmethod
    def validar_e_normalizar_cpf(cls, valor: Any) -> str:
        """Valida matematicamente o CPF (módulo 11) e normaliza para 000.000.000-00."""
        if valor is None:
            raise ValueError("CPF é obrigatório e não pode ser vazio.")
        return validate_and_format_cpf(str(valor))

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, valor: Any) -> Any:
        """Normaliza e-mail para minúsculas garantindo unicidade case-insensitive."""
        if isinstance(valor, str):
            return valor.strip().lower()
        return valor

    @field_validator("whatsapp")
    @classmethod
    def higienizar_whatsapp(cls, valor: str) -> str:
        """Grava o WhatsApp no padrão Baileys: somente dígitos com DDI 55."""
        return sanitize_whatsapp_number(valor)


# Campos NOT NULL: podem ser omitidos no PATCH, mas não enviados como null (foto_url e observacoes aceitam null)
CAMPOS_ATUALIZAVEIS_NAO_NULOS = (
    "nome",
    "whatsapp",
    "email",
    "status",
    "limite_reservas_ativas",
    "dia_vencimento",
)


class AssociadoUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    whatsapp: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    foto_url: Optional[str] = None
    status: Optional[StatusAssociado] = None
    limite_reservas_ativas: Optional[int] = Field(None, ge=1, le=5)
    dia_vencimento: Optional[int] = Field(None, ge=1, le=31)
    observacoes: Optional[str] = None

    @field_validator(*CAMPOS_ATUALIZAVEIS_NAO_NULOS)
    @classmethod
    def campos_obrigatorios_nao_aceitam_null(cls, valor: Any) -> Any:
        return rejeitar_null(valor)

    @field_validator("email", mode="before")
    @classmethod
    def normalizar_email(cls, valor: Any) -> Any:
        if isinstance(valor, str):
            return valor.strip().lower()
        return valor

    @field_validator("whatsapp")
    @classmethod
    def higienizar_whatsapp(cls, valor: str) -> str:
        """Grava o WhatsApp no padrão Baileys: somente dígitos com DDI 55."""
        return sanitize_whatsapp_number(valor)


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
    franquia_convidados: int = Field(
        default=8,
        description="Franquia de convidados do sócio no mês corrente (obtida de Configuracao)",
    )
    situacao_financeira: SituacaoFinanceira = Field(
        default=SituacaoFinanceira.EM_DIA,
        description="Situação financeira atual derivada das faturas em aberto",
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
    total_atualizados: int = Field(
        default=0,
        description="Total de associados existentes atualizados via upsert",
    )
    total_ignorados_duplicados: int
    erros: List[ImportErrorDetail]
