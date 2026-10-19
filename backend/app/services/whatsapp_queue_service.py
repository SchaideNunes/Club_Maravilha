"""
Fila assíncrona anti-ban para WhatsApp com priorização e delay humanizado (Rate Limiting).
Evita bloqueio de chip e banimento por disparo em rajada (bursting).
Registra auditoria de disparos (LogMensagem) quando log_context é fornecido.
"""
import asyncio
from dataclasses import dataclass, field
import enum
import logging
import random
import re
import time
from typing import Any, Dict, Optional, Set, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.phone import sanitize_whatsapp_number
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.services.whatsapp_service import (
    StatusConexaoWhatsApp,
    WhatsAppProvider,
    get_whatsapp_provider,
)

logger = logging.getLogger(__name__)


class MessagePriority(enum.IntEnum):
    HIGH = 0     # Ex: Recibo digital pós-pagamento (prioridade máxima imediata)
    NORMAL = 1   # Ex: Régua matinal D-3, D-0, D+3, D+7


@dataclass
class LogContext:
    etapa: EtapaRegua
    associado_id: Optional[uuid.UUID] = None
    fatura_id: Optional[uuid.UUID] = None


@dataclass(order=True)
class WhatsAppQueueItem:
    priority: int
    timestamp: float
    phone: str = field(compare=False)
    message: str = field(compare=False)
    log_context: Optional[LogContext] = field(default=None, compare=False)
    attempts: int = field(default=0, compare=False)


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
        session_factory: Optional[async_sessionmaker[AsyncSession]] = None,
        disconnect_retry_delay: float = 30.0,
        max_disconnect_retries: int = 5,
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
        self.session_factory = session_factory or AsyncSessionLocal
        self.disconnect_retry_delay = disconnect_retry_delay
        self.max_disconnect_retries = max_disconnect_retries
        self._queue: asyncio.PriorityQueue[WhatsAppQueueItem] = asyncio.PriorityQueue()
        self._pending_keys: Set[Tuple[uuid.UUID, EtapaRegua]] = set()
        self._is_running: bool = False
        self._worker_task: Optional[asyncio.Task] = None

    @property
    def qsize(self) -> int:
        return self._queue.qsize()

    def is_pending(self, fatura_id: uuid.UUID, etapa: EtapaRegua) -> bool:
        """Verifica se uma etapa para determinada fatura já está pendente na fila."""
        return (fatura_id, etapa) in self._pending_keys

    async def enqueue(
        self,
        phone: str,
        message: str,
        priority: MessagePriority = MessagePriority.NORMAL,
        log_context: Optional[LogContext] = None,
    ) -> bool:
        """Enfileira uma mensagem com prioridade e contexto de log opcionais. Retorna True se enfileirada, False se duplicada."""
        if log_context and log_context.fatura_id and log_context.etapa:
            key = (log_context.fatura_id, log_context.etapa)
            if key in self._pending_keys:
                logger.info(
                    f"[WhatsAppQueue] Mensagem para fatura {log_context.fatura_id} na etapa {log_context.etapa} "
                    f"já está pendente na fila. Ignorando duplicata."
                )
                return False
            self._pending_keys.add(key)

        item = WhatsAppQueueItem(
            priority=int(priority),
            timestamp=time.time(),
            phone=phone,
            message=message,
            log_context=log_context,
        )
        await self._queue.put(item)
        logger.info(
            f"[WhatsAppQueue] Mensagem enfileirada para {phone} (Prioridade={priority.name}). "
            f"Fila atual: {self._queue.qsize()} itens."
        )
        return True

    async def process_one(self) -> Optional[Dict[str, Any]]:
        """Consome e processa um único item da fila."""
        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

        # 1. Antes do send, consulta o status da conexão com o WhatsApp
        try:
            status_conn = await self.provider.get_connection_status()
            is_conectado = (
                isinstance(status_conn, dict)
                and status_conn.get("status") == StatusConexaoWhatsApp.CONECTADO.value
            )
        except Exception as exc:
            logger.warning(f"[WhatsAppQueue] Falha ao verificar conexão: {exc}")
            is_conectado = False

        if not is_conectado:
            if item.attempts < self.max_disconnect_retries:
                item.attempts += 1
                logger.warning(
                    f"[WhatsAppQueue] WhatsApp desconectado. Devolvendo item de {item.phone} à fila "
                    f"(tentativa {item.attempts}/{self.max_disconnect_retries})."
                )
                await self._queue.put(item)
                self._queue.task_done()
                if self.disconnect_retry_delay > 0:
                    await asyncio.sleep(self.disconnect_retry_delay)
                return None
            else:
                logger.error(
                    f"[WhatsAppQueue] WhatsApp desconectado após {item.attempts} tentativas. "
                    f"Registrando erro definitivo para {item.phone}."
                )
                erro_msg = f"WhatsApp desconectado após {item.attempts} tentativas de espera"
                try:
                    if item.log_context is not None:
                        await self._gravar_log(item, erro_msg)
                        if item.log_context.fatura_id and item.log_context.etapa:
                            self._pending_keys.discard((item.log_context.fatura_id, item.log_context.etapa))
                finally:
                    self._queue.task_done()
                return {"status": "error", "error": erro_msg, "code": "WHATSAPP_DESCONECTADO"}

        result = None
        erro_msg: Optional[str] = None
        try:
            try:
                logger.info(f"[WhatsAppQueue] Despachando mensagem para {item.phone}...")
                result = await self.provider.send_message(item.phone, item.message)
                if isinstance(result, dict) and result.get("status") == "error":
                    if result.get("code") == "WHATSAPP_DESCONECTADO":
                        if item.attempts < self.max_disconnect_retries:
                            item.attempts += 1
                            logger.warning(
                                f"[WhatsAppQueue] Resposta WHATSAPP_DESCONECTADO. Devolvendo item à fila "
                                f"(tentativa {item.attempts}/{self.max_disconnect_retries})."
                            )
                            await self._queue.put(item)
                            self._queue.task_done()
                            if self.disconnect_retry_delay > 0:
                                await asyncio.sleep(self.disconnect_retry_delay)
                            return result

                    erro_msg = str(result.get("error") or "Erro retornado pelo provedor WhatsApp")
            except Exception as err:
                logger.error(f"[WhatsAppQueue] Erro ao processar mensagem para {item.phone}: {err}")
                erro_msg = str(err)
            finally:
                # Grava log, descarta chave pendente e marca task_done ANTES do sleep anti-ban
                if item.log_context is not None:
                    try:
                        await self._gravar_log(item, erro_msg)
                    except Exception as err:
                        logger.error(f"[WhatsAppQueue] Falha ao registrar LogMensagem: {err}", exc_info=True)
                    if item.log_context.fatura_id and item.log_context.etapa:
                        self._pending_keys.discard((item.log_context.fatura_id, item.log_context.etapa))

                self._queue.task_done()
        finally:
            # Sleep anti-ban isolado por fora do bloco de registro e finalização do item
            if self.max_delay > 0:
                delay = random.uniform(self.min_delay, self.max_delay)
                logger.info(f"[WhatsAppQueue] Aguardando {delay:.2f}s (delay anti-ban)...")
                await asyncio.sleep(delay)

        return result

    async def _gravar_log(self, item: WhatsAppQueueItem, erro_msg: Optional[str]) -> None:
        """Grava registro de auditoria na tabela logs_mensagens."""
        try:
            try:
                destinatario = sanitize_whatsapp_number(item.phone)
            except Exception:
                destinatario = re.sub(r"\D", "", str(item.phone))

            status = StatusEnvio.ERRO if erro_msg else StatusEnvio.SUCESSO
            log = LogMensagem(
                associado_id=item.log_context.associado_id,
                fatura_id=item.log_context.fatura_id,
                destinatario=destinatario,
                etapa=item.log_context.etapa,
                mensagem=item.message,
                status=status,
                erro=erro_msg,
            )
            async with self.session_factory() as session:
                session.add(log)
                await session.commit()
        except Exception as err:
            logger.error(f"[WhatsAppQueue] Falha ao registrar LogMensagem: {err}", exc_info=True)

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
