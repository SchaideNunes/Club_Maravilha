"""
Schemas Pydantic v2 para consulta dos Logs de Mensagens de WhatsApp.
"""
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.log_mensagem import EtapaRegua, StatusEnvio


class LogMensagemResponse(BaseModel):
    id: uuid.UUID
    associado_id: Optional[uuid.UUID] = None
    fatura_id: Optional[uuid.UUID] = None
    destinatario: str
    etapa: EtapaRegua
    mensagem: str
    status: StatusEnvio
    erro: Optional[str] = None
    enviado_em: datetime

    model_config = ConfigDict(from_attributes=True)
