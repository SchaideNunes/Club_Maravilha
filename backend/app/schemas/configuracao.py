"""
Schemas Pydantic v2 para as Configurações do clube (singleton) editáveis pelo painel.
"""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Horário HH:MM em 24h (00:00 a 23:59), sempre com dois dígitos
HORARIO_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"

# Template de mensagem: não pode ser vazio (as variáveis são descritas em VARIAVEIS_TEMPLATE)
TemplateMensagem = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


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
