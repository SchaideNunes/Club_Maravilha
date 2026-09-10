"""
Schemas Pydantic v2 para validação e serialização de Agendamentos de Quadras.
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.agendamento import StatusAgendamento, TipoQuadra


class AgendamentoBase(BaseModel):
    quadra: TipoQuadra
    data_inicio: datetime
    data_fim: datetime
    observacoes: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_horarios(self) -> "AgendamentoBase":
        if self.data_fim <= self.data_inicio:
            raise ValueError("A data/hora de término deve ser posterior à data/hora de início.")
        return self


class AgendamentoCreate(AgendamentoBase):
    associado_id: uuid.UUID


class AgendamentoResponse(AgendamentoBase):
    id: uuid.UUID
    associado_id: uuid.UUID
    status: StatusAgendamento
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
