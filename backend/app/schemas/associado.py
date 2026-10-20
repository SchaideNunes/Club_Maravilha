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
from app.models.associado import Sexo, StatusAssociado
from app.schemas.plano import PlanoResumo
from app.schemas.validators import (
    normalizar_cep,
    normalizar_uf,
    rejeitar_null,
    texto_opcional,
    validar_data_nascimento,
)


class SituacaoFinanceira(str, enum.Enum):
    EM_DIA = "EM_DIA"
    PENDENTE = "PENDENTE"
    ATRASADO = "ATRASADO"


CAMPOS_TEXTO_OPCIONAIS = (
    "rg",
    "profissao",
    "cep",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "uf",
    "observacoes",
)


class DadosCadastrais(BaseModel):
    """Dados pessoais e endereço da ficha do sócio (todos opcionais)."""
    data_nascimento: Optional[date] = None
    rg: Optional[str] = Field(None, max_length=20)
    sexo: Optional[Sexo] = None
    profissao: Optional[str] = Field(None, max_length=100)
    cep: Optional[str] = Field(None, max_length=10, example="44001-000")
    logradouro: Optional[str] = Field(None, max_length=150)
    numero: Optional[str] = Field(None, max_length=10)
    complemento: Optional[str] = Field(None, max_length=80)
    bairro: Optional[str] = Field(None, max_length=80)
    cidade: Optional[str] = Field(None, max_length=80)
    uf: Optional[str] = Field(None, max_length=2, example="BA")
    observacoes: Optional[str] = None

    @field_validator(*CAMPOS_TEXTO_OPCIONAIS, mode="before")
    @classmethod
    def textos_em_branco_viram_null(cls, valor: Any) -> Any:
        return texto_opcional(valor)

    @field_validator("cep")
    @classmethod
    def validar_cep(cls, valor: Optional[str]) -> Optional[str]:
        return normalizar_cep(valor)

    @field_validator("uf")
    @classmethod
    def validar_uf(cls, valor: Optional[str]) -> Optional[str]:
        return normalizar_uf(valor)

    @field_validator("data_nascimento")
    @classmethod
    def validar_nascimento(cls, valor: Optional[date]) -> Optional[date]:
        return validar_data_nascimento(valor)


class AssociadoBase(DadosCadastrais):
    nome: str = Field(..., min_length=3, max_length=150, example="Carlos Eduardo Silva")
    cpf: str = Field(..., example="123.456.789-00")
    whatsapp: str = Field(..., min_length=10, max_length=20, example="+5511999998888")
    email: EmailStr = Field(..., example="carlos.silva@exemplo.com")
    foto_url: Optional[str] = Field(None, example="https://storage.clubmaravilha.com.br/fotos/carlos.webp")


class AssociadoCreate(AssociadoBase):
    plano_id: Optional[uuid.UUID] = None
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


class AssociadoUpdate(DadosCadastrais):
    nome: Optional[str] = Field(None, min_length=3, max_length=150)
    whatsapp: Optional[str] = Field(None, min_length=10, max_length=20)
    email: Optional[EmailStr] = None
    foto_url: Optional[str] = None
    status: Optional[StatusAssociado] = None
    limite_reservas_ativas: Optional[int] = Field(None, ge=1, le=5)
    dia_vencimento: Optional[int] = Field(None, ge=1, le=31)
    # null desvincula o plano (o sócio volta a pagar a mensalidade padrão das configurações)
    plano_id: Optional[uuid.UUID] = None

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
    plano: Optional[PlanoResumo] = None
    data_inativacao: Optional[date] = None
    motivo_inativacao: Optional[str] = None
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


class InativarAssociadoRequest(BaseModel):
    motivo: Optional[str] = Field(None, max_length=255, example="Mudou de cidade")

    @field_validator("motivo", mode="before")
    @classmethod
    def motivo_em_branco_vira_null(cls, valor: Any) -> Any:
        return texto_opcional(valor)


class InativacaoAssociadoResponse(BaseModel):
    associado: AssociadoResponse
    faturas_canceladas: int = Field(description="Faturas pendentes ainda não vencidas que foram canceladas")
    convites_cancelados: int = Field(description="Convites emitidos para visitas a partir de hoje")
    reservas_canceladas: int = Field(description="Reservas de quadra futuras confirmadas")
