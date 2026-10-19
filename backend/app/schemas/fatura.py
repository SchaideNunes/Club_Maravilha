"""
Schemas Pydantic v2 para validação e serialização de Faturas/Mensalidades.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.core import clock
from app.models.fatura import FormaPagamento, StatusFatura, calcular_valor_total_fatura

# Tolerância para a diferença de relógio entre o navegador da administração e o servidor
TOLERANCIA_RELOGIO = timedelta(minutes=5)


class FaturaBase(BaseModel):
    referencia_mes: str = Field(..., pattern=r"^\d{4}-\d{2}$", example="2026-09")
    valor_base: Decimal = Field(..., gt=0, example=Decimal("150.00"))
    valor_convidados_excedentes: Decimal = Field(default=Decimal("0.00"), ge=0)
    valor_desconto: Decimal = Field(default=Decimal("0.00"), ge=0)
    data_vencimento: date
    forma_pagamento: FormaPagamento = FormaPagamento.PIX


class FaturaCreate(FaturaBase):
    associado_id: uuid.UUID
    valor_total: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description=(
            "Valor líquido (base + excedentes - desconto). Quando omitido é calculado; "
            "quando informado precisa ser coerente com os demais valores."
        ),
        examples=["150.00"],
    )

    @model_validator(mode="after")
    def validar_valor_total(self) -> "FaturaCreate":
        total_calculado = calcular_valor_total_fatura(
            self.valor_base,
            self.valor_convidados_excedentes,
            self.valor_desconto,
        )
        if total_calculado <= 0:
            raise ValueError("O valor total da fatura deve ser maior que zero (desconto excede os valores cobrados).")
        if self.valor_total is None:
            self.valor_total = total_calculado
        elif self.valor_total != total_calculado:
            raise ValueError(
                f"valor_total ({self.valor_total}) incoerente: base + excedentes - desconto = {total_calculado}."
            )
        return self


class FaturaBaixaManual(BaseModel):
    """Dados da baixa manual de uma fatura pela administração (PIX, CARTAO ou DINHEIRO)."""
    forma_pagamento: FormaPagamento
    data_pagamento: Optional[datetime] = Field(
        default=None,
        description="Momento do pagamento (não pode estar no futuro); quando omitido, o servidor usa o instante atual",
    )

    @field_validator("data_pagamento")
    @classmethod
    def data_pagamento_nao_pode_ser_futura(cls, valor: Optional[datetime]) -> Optional[datetime]:
        """Datas sem fuso horário são tratadas como UTC, como no restante da API."""
        if valor is None:
            return valor
        instante = valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
        agora = clock.agora_clube().astimezone(timezone.utc)
        if instante > agora + TOLERANCIA_RELOGIO:
            raise ValueError("A data do pagamento não pode estar no futuro.")
        return valor


class FaturaResponse(FaturaBase):
    id: uuid.UUID
    associado_id: uuid.UUID
    valor_total: Decimal
    convites_usados: int = 0
    convites_extras: int = 0
    lembretes_ativos: bool = True
    data_pagamento: Optional[datetime] = None
    status: StatusFatura
    txid: Optional[str] = None
    pix_copia_cola: Optional[str] = None
    pix_qr_code_url: Optional[str] = None
    metadata_webhook: Optional[Dict[str, Any]] = None
    notificado_d_minus_3_em: Optional[datetime] = None
    notificado_d_zero_em: Optional[datetime] = None
    notificado_d_plus_3_em: Optional[datetime] = None
    notificado_d_plus_7_em: Optional[datetime] = None
    notificado_pos_pagamento_em: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BillingExecutionReport(BaseModel):
    data_referencia: date
    d_minus_3_enviados: int = 0
    d_zero_enviados: int = 0
    d_plus_3_enviados: int = 0
    d_plus_7_enviados: int = 0
    inadimplentes_atualizados: int = 0
    total_enfileirados: int = 0
    erros: list[str] = []


class GeracaoFaturasRequest(BaseModel):
    """Payload opcional para disparo de geração de faturas de um mês."""
    referencia_mes: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Mês de referência no formato AAAA-MM (ex: 2026-11)",
    )


class GeracaoFaturasResponse(BaseModel):
    """Resultado da geração em lote de faturas do mês."""
    referencia_mes: str
    criadas: int
    ja_existentes: int
    total: int


class MarcarAtrasadasResponse(BaseModel):
    """Resultado da rotina de marcação de faturas atrasadas."""
    data_referencia: date
    atualizadas: int


class FaturaPainelItemResponse(BaseModel):
    """Item resumido da fatura para listagem paginada no painel administrativo."""
    id: uuid.UUID
    associado_id: uuid.UUID
    associado_nome: str
    referencia_mes: str
    data_vencimento: date
    valor_base: Decimal
    valor_convidados_excedentes: Decimal
    valor_desconto: Decimal
    valor_total: Decimal
    convites_usados: int
    convites_extras: int
    status: StatusFatura
    forma_pagamento: Optional[FormaPagamento] = None
    data_pagamento: Optional[datetime] = None
    lembretes_ativos: bool

    model_config = ConfigDict(from_attributes=True)


class PaginatedFaturasResponse(BaseModel):
    """Resposta paginada da listagem de faturas."""
    items: list[FaturaPainelItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

