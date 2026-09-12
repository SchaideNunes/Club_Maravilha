"""
Testes unitários para a Fila Anti-Ban do WhatsApp com Rate Limiting.
"""
import pytest
import asyncio
from app.services.whatsapp_service import MockWhatsAppProvider
from app.services.whatsapp_queue_service import (
    WhatsAppQueueService,
    WhatsAppQueueItem,
    MessagePriority,
)


@pytest.mark.asyncio
async def test_whatsapp_queue_processes_items_sequentially():
    mock_provider = MockWhatsAppProvider()
    queue_service = WhatsAppQueueService(
        provider=mock_provider,
        min_delay_seconds=0.0,  # Zero delay para testes rápidos
        max_delay_seconds=0.0,
    )

    # Inicia worker em segundo plano
    worker_task = asyncio.create_task(queue_service.start_worker())

    # Enfileira 3 mensagens normais
    await queue_service.enqueue(
        phone="11911112222",
        message="Mensagem 1",
        priority=MessagePriority.NORMAL
    )
    await queue_service.enqueue(
        phone="11933334444",
        message="Mensagem 2",
        priority=MessagePriority.NORMAL
    )
    await queue_service.enqueue(
        phone="11955556666",
        message="Mensagem 3",
        priority=MessagePriority.NORMAL
    )

    # Aguarda esvaziamento da fila
    await queue_service.join()

    # Finaliza o worker
    await queue_service.stop_worker(worker_task)

    assert len(mock_provider.sent_messages) == 3
    assert mock_provider.sent_messages[0]["message"] == "Mensagem 1"
    assert mock_provider.sent_messages[1]["message"] == "Mensagem 2"
    assert mock_provider.sent_messages[2]["message"] == "Mensagem 3"


@pytest.mark.asyncio
async def test_whatsapp_queue_high_priority_preempts_normal():
    """Mensagens prioritárias (ex: recibo pós-pagamento) saem na frente da fila."""
    mock_provider = MockWhatsAppProvider()
    queue_service = WhatsAppQueueService(
        provider=mock_provider,
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
    )

    # Enfileira mensagem normal sem o worker ativo ainda
    await queue_service.enqueue(
        phone="11911112222",
        message="Cobrança Rotina D-0",
        priority=MessagePriority.NORMAL
    )
    # Enfileira mensagem de alta prioridade (recibo instantâneo)
    await queue_service.enqueue(
        phone="11999998888",
        message="Recibo Imediato Pix",
        priority=MessagePriority.HIGH
    )

    worker_task = asyncio.create_task(queue_service.start_worker())
    await queue_service.join()
    await queue_service.stop_worker(worker_task)

    assert len(mock_provider.sent_messages) == 2
    # Recibo de alta prioridade deve ter sido processado primeiro!
    assert mock_provider.sent_messages[0]["message"] == "Recibo Imediato Pix"
    assert mock_provider.sent_messages[1]["message"] == "Cobrança Rotina D-0"
