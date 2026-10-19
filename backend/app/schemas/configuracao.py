"""
Schemas Pydantic v2 para as Configurações do clube (singleton) editáveis pelo painel.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from string import Formatter
from typing import Annotated, Any, Optional
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_serializer, field_validator
from app.models.configuracao import VARIAVEIS_TEMPLATE
from app.schemas.validators import rejeitar_null

# Horário HH:MM em 24h (00:00 a 23:59), sempre com dois dígitos
HORARIO_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"

_VARIAVEIS_FORMATADAS = ", ".join("{" + variavel + "}" for variavel in VARIAVEIS_TEMPLATE)


def validar_template(texto: str) -> str:
    """
    Valida a sintaxe de um template de mensagem (mesma gramática de `str.format`):
    - chaves balanceadas (uma chave literal deve ser escrita como `{{` ou `}}`);
    - somente variáveis de VARIAVEIS_TEMPLATE, sem campos vazios (`{}`), posicionais (`{0}`),
      acessos a atributo/índice (`{nome.x}`), conversão (`{nome!r}`) ou formato (`{nome:>10}`).
    Assim um erro de digitação (ex: `{nom}`) é barrado ao salvar, não quando a régua dispara.
    """
    try:
        partes = list(Formatter().parse(texto))
    except ValueError as erro:  # chave '{' ou '}' sem par
        raise ValueError(
            f"Template inválido: {erro}. Para usar uma chave literal escreva '{{{{' ou '}}}}'."
        ) from erro

    for _literal, campo, formato, conversao in partes:
        if campo is None:
            continue
        if campo == "" or campo.isdigit():
            raise ValueError(
                f"Template inválido: campo vazio ou posicional '{{{campo}}}'. Use apenas: {_VARIAVEIS_FORMATADAS}."
            )
        if campo not in VARIAVEIS_TEMPLATE:
            raise ValueError(
                f"Template inválido: variável desconhecida '{{{campo}}}'. Use apenas: {_VARIAVEIS_FORMATADAS}."
            )
        if conversao or formato:
            raise ValueError(
                f"Template inválido: '{{{campo}}}' não aceita conversão (!) nem formato (:). Use a variável pura."
            )
    return texto


# Template de mensagem: não pode ser vazio e só pode usar as variáveis conhecidas
TemplateMensagem = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=4096),
    AfterValidator(validar_template),
]

# Campos NOT NULL: podem ser omitidos no PATCH, mas não enviados como null (somente chave_pix aceita null)
CAMPOS_NAO_NULOS = (
    "valor_mensalidade",
    "franquia_convidados",
    "valor_convidado_extra",
    "horario_disparo",
    "automacao_ativa",
    "template_d_menos_3",
    "template_d0",
    "template_recibo",
    "template_d_mais_3",
    "template_d_mais_7",
)


class ConfiguracaoResponse(BaseModel):
    id: int
    valor_mensalidade: Decimal
    franquia_convidados: int
    valor_convidado_extra: Decimal
    chave_pix: Optional[str] = None
    horario_disparo: str
    automacao_ativa: bool
    template_d_menos_3: str
    template_d0: str
    template_recibo: str
    template_d_mais_3: str
    template_d_mais_7: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("valor_mensalidade", "valor_convidado_extra", mode="before")
    @classmethod
    def preparar_decimais(cls, v: Any) -> Any:
        return v

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        if "valor_mensalidade" in data and isinstance(data["valor_mensalidade"], (Decimal, float, int)):
            data["valor_mensalidade"] = f"{Decimal(str(data['valor_mensalidade'])):.2f}"
        if "valor_convidado_extra" in data and isinstance(data["valor_convidado_extra"], (Decimal, float, int)):
            data["valor_convidado_extra"] = f"{Decimal(str(data['valor_convidado_extra'])):.2f}"
        return data


class ConfiguracaoUpdate(BaseModel):
    """Atualização parcial: somente os campos enviados são alterados."""
    valor_mensalidade: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    franquia_convidados: Optional[int] = Field(None, ge=0)
    valor_convidado_extra: Optional[Decimal] = Field(None, ge=0, max_digits=10, decimal_places=2)
    chave_pix: Optional[str] = Field(None, max_length=150)
    horario_disparo: Optional[str] = Field(None, pattern=HORARIO_PATTERN, examples=["08:00"])
    automacao_ativa: Optional[bool] = None
    template_d_menos_3: Optional[TemplateMensagem] = None
    template_d0: Optional[TemplateMensagem] = None
    template_recibo: Optional[TemplateMensagem] = None
    template_d_mais_3: Optional[TemplateMensagem] = None
    template_d_mais_7: Optional[TemplateMensagem] = None

    @field_validator("chave_pix", mode="before")
    @classmethod
    def normalizar_chave_pix(cls, valor: Any) -> Optional[str]:
        if valor is None:
            return None
        if isinstance(valor, str):
            limpo = valor.strip()
            return limpo if limpo else None
        return valor

    @field_validator(*CAMPOS_NAO_NULOS)
    @classmethod
    def campos_obrigatorios_nao_aceitam_null(cls, valor: Any) -> Any:
        return rejeitar_null(valor)


class PreviewTemplateRequest(BaseModel):
    template: TemplateMensagem
    fatura_id: Optional[uuid.UUID] = None


class PreviewTemplateResponse(BaseModel):
    mensagem: str
