"""
Agendador de Tarefas em Segundo Plano (APScheduler) e Consumidor da Fila WhatsApp.
Executa a régua diária de cobrança às 08:00 e orquestra o worker anti-ban.
"""
import asyncio
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.billing_engine_service import BillingEngineService
from app.services.fatura_service import FaturaService
from app.services.whatsapp_queue_service import get_global_whatsapp_queue

logger = logging.getLogger(__name__)

# Instâncias globais gerenciadas pelo ciclo de vida da aplicação
scheduler: Optional[AsyncIOScheduler] = None
worker_task: Optional[asyncio.Task] = None


def scheduler_habilitado() -> bool:
    """
    Indica se este processo deve rodar o agendador e o worker da fila de WhatsApp:
    nunca no modo de teste e somente com SCHEDULER_ENABLED ligado, para que apenas um
    processo dispare a régua de cobrança e consuma a fila anti-ban.
    """
    return settings.ENVIRONMENT != "test" and settings.SCHEDULER_ENABLED


async def executar_rotina_diaria_cobranca() -> None:
    """Tarefa diária agendada: processa D-3, D-0, D+3 e D+7."""
    logger.info("[Scheduler] Iniciando disparo automático da régua diária de cobrança (08:00)...")
    async with AsyncSessionLocal() as session:
        try:
            fatura_service = FaturaService(session)
            atualizadas = await fatura_service.marcar_faturas_atrasadas()
            logger.info(f"[Scheduler] Marcação de faturas atrasadas concluída: {atualizadas} faturas atualizadas.")
        except Exception as exc:
            logger.error(f"[Scheduler] Falha na marcação de faturas atrasadas: {exc}", exc_info=True)

        try:
            engine = BillingEngineService(session=session)
            report = await engine.processar_regua_diaria()
            logger.info(
                f"[Scheduler] Régua diária concluída com sucesso: "
                f"{report.total_enfileirados} mensagens enfileiradas, "
                f"{report.inadimplentes_atualizados} sócios marcados como inadimplentes."
            )
        except Exception as exc:
            logger.error(f"[Scheduler] Falha na execução da régua de cobrança: {exc}", exc_info=True)


def start_scheduler_and_worker() -> None:
    """Inicia o scheduler diário e o worker anti-ban da fila de WhatsApp."""
    global scheduler, worker_task

    # 1. Inicia o worker assíncrono da fila anti-ban do WhatsApp
    queue = get_global_whatsapp_queue()
    worker_task = asyncio.create_task(queue.start_worker())
    logger.info("[Scheduler] Worker de fila WhatsApp iniciado com sucesso.")

    # 2. Configura o agendador diário para as 08:00
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        executar_rotina_diaria_cobranca,
        trigger=CronTrigger(hour=8, minute=0),
        id="regua_cobranca_diaria",
        name="Régua Diária de Cobrança do Club Maravilha",
        replace_existing=True
    )
    scheduler.start()
    logger.info("[Scheduler] APScheduler iniciado. Próximo disparo diário agendado para 08:00.")


async def stop_scheduler_and_worker() -> None:
    """Encerra graciosamente o scheduler e o consumidor da fila."""
    global scheduler, worker_task

    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] APScheduler encerrado.")

    if worker_task:
        queue = get_global_whatsapp_queue()
        await queue.stop_worker(worker_task)
        logger.info("[Scheduler] Worker de fila WhatsApp encerrado.")
