"""
Schemas Pydantic v2 para validação e serialização de Faturas/Mensalidades.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.fatura import FormaPagamento, StatusFatura


class FaturaBase(BaseModel):
    referencia_mes: str = Field(..., pattern=r"^\d{4}-\d{2}$", example="2026-09")
    valor_base: Decimal = Field(..., gt=0, example=Decimal("150.00"))
    valor_convidados_excedentes: Decimal = Field(default=Decimal("0.00"), ge=0)
    valor_desconto: Decimal = Field(default=Decimal("0.00"), ge=0)
    valor_total: Decimal = Field(..., gt=0, example=Decimal("150.00"))
    data_vencimento: date
    forma_pagamento: FormaPagamento = FormaPagamento.PIX


class FaturaCreate(FaturaBase):
    associado_id: uuid.UUID


class FaturaResponse(FaturaBase):
    id: uuid.UUID
    associado_id: uuid.UUID
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
