"""
Testes unitários do registro de LogMensagem pela fila anti-ban do WhatsApp (Feature 3).

Contrato (app/services/whatsapp_queue_service.py):
- `LogContext` (dataclass): etapa: EtapaRegua, associado_id: Optional[UUID] = None,
  fatura_id: Optional[UUID] = None.
- `WhatsAppQueueService(provider=None, min_delay_seconds=None, max_delay_seconds=None,
  session_factory=None)`: `session_factory` é um async_sessionmaker usado para gravar o
  LogMensagem; quando omitido usa `app.core.database.AsyncSessionLocal`.
- `enqueue(phone, message, priority=NORMAL, log_context=None)`: itens com `log_context`
  geram UM LogMensagem no momento do envio (process_one), nunca no enfileiramento:
  SUCESSO quando o provider responde sem `status == "error"`; ERRO (com `erro` preenchido)
  quando o provider lança exceção ou responde `status == "error"`.
  `destinatario` = telefone higienizado (somente dígitos, DDI 55).
- Itens sem `log_context` continuam sem gerar log (compatibilidade com a régua atual).
"""
import uuid
from typing import Any, Dict

import pytest
from sqlalchemy import func, select

from app.models.associado import Associado, StatusAssociado
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.services.whatsapp_queue_service import (
    LogContext,
    MessagePriority,
    WhatsAppQueueService,
)
from app.services.whatsapp_service import MockWhatsAppProvider, WhatsAppProvider
from tests.conftest import TestingSessionLocal


class ProviderQueFalha(MockWhatsAppProvider):
    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        raise RuntimeError("engine offline")


class ProviderQueRespondeErro(MockWhatsAppProvider):
    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        return {"status": "error", "error": "numero sem whatsapp"}


def _fila(provider: WhatsAppProvider) -> WhatsAppQueueService:
    return WhatsAppQueueService(
        provider=provider,
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
        session_factory=TestingSessionLocal,
    )


async def _associado(db_session) -> Associado:
    socio = Associado(
        nome="Socio Log",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="socio_log@clube.com",
        status=StatusAssociado.ATIVO,
    )
    db_session.add(socio)
    await db_session.commit()
    return socio


async def _logs():
    async with TestingSessionLocal() as s:
        return list((await s.execute(select(LogMensagem))).scalars().all())


async def test_envio_com_log_context_grava_log_sucesso_somente_no_envio(db_session):
    socio = await _associado(db_session)
    provider = MockWhatsAppProvider()
    fila = _fila(provider)

    await fila.enqueue(
        phone="+55 (75) 99999-0001",
        message="Recibo de teste",
        priority=MessagePriority.HIGH,
        log_context=LogContext(etapa=EtapaRegua.RECIBO, associado_id=socio.id),
    )
    assert await _logs() == []  # enfileirar não é enviar

    await fila.process_one()

    logs = await _logs()
    assert len(logs) == 1
    log = logs[0]
    assert log.etapa == EtapaRegua.RECIBO
    assert log.status == StatusEnvio.SUCESSO
    assert log.erro is None
    assert log.destinatario == "5575999990001"
    assert log.mensagem == "Recibo de teste"
    assert log.associado_id == socio.id
    assert log.fatura_id is None
    assert len(provider.sent_messages) == 1


@pytest.mark.parametrize("provider_cls", [ProviderQueFalha, ProviderQueRespondeErro])
async def test_falha_no_envio_grava_log_erro(db_session, provider_cls):
    socio = await _associado(db_session)
    fila = _fila(provider_cls())

    await fila.enqueue(
        phone="5575999990001",
        message="Recibo com falha",
        priority=MessagePriority.HIGH,
        log_context=LogContext(etapa=EtapaRegua.RECIBO, associado_id=socio.id),
    )
    await fila.process_one()

    logs = await _logs()
    assert len(logs) == 1
    assert logs[0].status == StatusEnvio.ERRO
    assert logs[0].erro  # detalhe da falha preenchido


async def test_envio_sem_log_context_nao_grava_log():
    fila = _fila(MockWhatsAppProvider())

    await fila.enqueue(phone="5575999990001", message="Lembrete legado")
    await fila.process_one()

    async with TestingSessionLocal() as s:
        total = (await s.execute(select(func.count(LogMensagem.id)))).scalar_one()
    assert total == 0


def test_log_context_campos_opcionais():
    ctx = LogContext(etapa=EtapaRegua.TESTE)
    assert ctx.associado_id is None
    assert ctx.fatura_id is None
    fatura_id = uuid.uuid4()
    assert LogContext(etapa=EtapaRegua.RECIBO, fatura_id=fatura_id).fatura_id == fatura_id
