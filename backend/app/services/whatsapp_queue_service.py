"""
Fila assíncrona anti-ban para WhatsApp com priorização e delay humanizado (Rate Limiting).
Evita bloqueio de chip e banimento por disparo em rajada (bursting).
"""
import asyncio
import enum
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from app.core.config import settings
from app.services.whatsapp_service import WhatsAppProvider, get_whatsapp_provider

logger = logging.getLogger(__name__)


class MessagePriority(enum.IntEnum):
    HIGH = 0     # Ex: Recibo digital pós-pagamento (prioridade máxima imediata)
    NORMAL = 1   # Ex: Régua matinal D-3, D-0, D+3, D+7


@dataclass(order=True)
class WhatsAppQueueItem:
    priority: int
    timestamp: float
    phone: str = field(compare=False)
    message: str = field(compare=False)


class WhatsAppQueueService:
    """
    Fila de mensagens com prioridade e rate limiting com jitter humanizado.
    Garante intervalo seguro entre disparos para mitigar banimento em APIs não oficiais.
    """

    def __init__(
        self,
        provider: Optional[WhatsAppProvider] = None,
        min_delay_seconds: Optional[float] = None,
        max_delay_seconds: Optional[float] = None,
    ) -> None:
        self.provider = provider or get_whatsapp_provider()
        self.min_delay = (
            min_delay_seconds
            if min_delay_seconds is not None
            else settings.WHATSAPP_MIN_DELAY_SECONDS
        )
        self.max_delay = (
            max_delay_seconds
            if max_delay_seconds is not None
            else settings.WHATSAPP_MAX_DELAY_SECONDS
        )
        self._queue: asyncio.PriorityQueue[WhatsAppQueueItem] = asyncio.PriorityQueue()
        self._is_running: bool = False
        self._worker_task: Optional[asyncio.Task] = None

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    async def enqueue(
        self,
        phone: str,
        message: str,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> None:
        """Enfileira uma mensagem com prioridade definida."""
        item = WhatsAppQueueItem(
            priority=int(priority),
            timestamp=time.time(),
            phone=phone,
            message=message
        )
        await self._queue.put(item)
        logger.info(
            f"[WhatsAppQueue] Mensagem enfileirada para {phone} (Prioridade={priority.name}). "
            f"Fila atual: {self._queue.qsize()} itens."
        )

    async def process_one(self) -> Optional[Dict[str, Any]]:
        """Consome e processa um único item da fila."""
        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

        result = None
        try:
            logger.info(f"[WhatsAppQueue] Despachando mensagem para {item.phone}...")
            result = await self.provider.send_message(item.phone, item.message)

            # Delay humanizado anti-ban (somente se min_delay > 0)
            if self.max_delay > 0:
                delay = random.uniform(self.min_delay, self.max_delay)
                logger.info(f"[WhatsAppQueue] Aguardando {delay:.2f}s (delay anti-ban)...")
                await asyncio.sleep(delay)
        except Exception as err:
            logger.error(f"[WhatsAppQueue] Erro ao processar mensagem para {item.phone}: {err}")
        finally:
            self._queue.task_done()

        return result

    async def start_worker(self) -> None:
        """Loop contínuo do consumidor da fila."""
        self._is_running = True
        logger.info("[WhatsAppQueue] Worker de mensagens iniciado.")
        while self._is_running:
            await self.process_one()

    async def stop_worker(self, task: Optional[asyncio.Task] = None) -> None:
        """Encerra o worker de forma graciosa."""
        self._is_running = False
        target_task = task or self._worker_task
        if target_task and not target_task.done():
            target_task.cancel()
            try:
                await target_task
            except asyncio.CancelledError:
                pass
        logger.info("[WhatsAppQueue] Worker de mensagens finalizado.")

    async def join(self) -> None:
        """Aguarda até que todos os itens da fila tenham sido processados."""
        await self._queue.join()


# Instância global reutilizável (Singleton da aplicação)
_global_queue: Optional[WhatsAppQueueService] = None


def get_global_whatsapp_queue() -> WhatsAppQueueService:
    global _global_queue
    if _global_queue is None:
        _global_queue = WhatsAppQueueService()
    return _global_queue


def set_global_whatsapp_queue(queue: WhatsAppQueueService) -> None:
    global _global_queue
    _global_queue = queue
