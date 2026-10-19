"""
Agendador de Tarefas em Segundo Plano (APScheduler) e Consumidor da Fila WhatsApp.
Executa a régua diária de cobrança em horário configurável e orquestra o worker anti-ban.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.clock import agora_clube
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.billing_engine_service import BillingEngineService
from app.services.fatura_service import FaturaService
from app.services.whatsapp_queue_service import get_global_whatsapp_queue

logger = logging.getLogger(__name__)

HORARIO_DISPARO_PADRAO = "08:00"
JOB_ID_REGUA = "regua_cobranca_diaria"
JOB_ID_RECUPERACAO = "regua_cobranca_recuperacao"

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


def criar_trigger_regua(horario_disparo: str) -> CronTrigger:
    """
    Cria um CronTrigger diário no horário fornecido ("HH:MM") respeitando
    o fuso horário da aplicação (settings.TIMEZONE).
    Lança ValueError se o formato for inválido.
    """
    if not isinstance(horario_disparo, str):
        raise ValueError("Horário de disparo deve ser uma string no formato HH:MM.")

    partes = horario_disparo.strip().split(":")
    if len(partes) != 2 or not partes[0].isdigit() or not partes[1].isdigit():
        raise ValueError(f"Formato de horário inválido: '{horario_disparo}'. Esperado HH:MM.")

    hora = int(partes[0])
    minuto = int(partes[1])

    if not (0 <= hora <= 23 and 0 <= minuto <= 59):
        raise ValueError(f"Horário fora dos limites válidos (00:00 - 23:59): '{horario_disparo}'.")

    tz = ZoneInfo(settings.TIMEZONE)
    return CronTrigger(hour=hora, minute=minuto, timezone=tz)


async def executar_rotina_diaria_cobranca() -> None:
    """Tarefa diária agendada: processa D-3, D-0, D+3 e D+7 com sessões isoladas para cada etapa."""
    logger.info("[Scheduler] Iniciando disparo automático da régua diária de cobrança...")

    # 1. Marcação de faturas atrasadas (sessão isolada)
    try:
        async with AsyncSessionLocal() as session:
            try:
                fatura_service = FaturaService(session)
                atualizadas = await fatura_service.marcar_faturas_atrasadas()
                logger.info(f"[Scheduler] Marcação de faturas atrasadas concluída: {atualizadas} faturas atualizadas.")
            except Exception as exc:
                await session.rollback()
                logger.error(f"[Scheduler] Falha na marcação de faturas atrasadas: {exc}", exc_info=True)
    except Exception as exc:
        logger.error(f"[Scheduler] Erro de conexão/sessão na marcação de faturas atrasadas: {exc}", exc_info=True)

    # 2. Execução da régua de cobrança (sessão isolada)
    try:
        async with AsyncSessionLocal() as session:
            try:
                engine = BillingEngineService(session=session)
                report = await engine.processar_regua_diaria()
                logger.info(
                    f"[Scheduler] Régua diária concluída com sucesso: "
                    f"{report.total_enfileirados} mensagens enfileiradas, "
                    f"{report.inadimplentes_atualizados} sócios marcados como inadimplentes."
                )
            except Exception as exc:
                await session.rollback()
                logger.error(f"[Scheduler] Falha na execução da régua de cobrança: {exc}", exc_info=True)
    except Exception as exc:
        logger.error(f"[Scheduler] Erro de conexão/sessão na régua de cobrança: {exc}", exc_info=True)


def agendar_recuperacao_se_necessario(horario_disparo: str) -> bool:
    """
    Verifica se o horário programado para hoje já passou de acordo com agora_clube().
    Se já passou, agenda uma execução de recuperação única em run_date = now + 60s.
    Retorna True se agendou a recuperação ou False caso contrário.
    """
    if scheduler is None:
        return False

    agora = agora_clube()
    partes = horario_disparo.strip().split(":")
    hora = int(partes[0])
    minuto = int(partes[1])
    horario_hoje = agora.replace(hour=hora, minute=minuto, second=0, microsecond=0)

    if agora > horario_hoje:
        run_date = agora + timedelta(seconds=60)
        scheduler.add_job(
            executar_rotina_diaria_cobranca,
            trigger="date",
            run_date=run_date,
            id=JOB_ID_RECUPERACAO,
            name="Recuperação da Régua Diária de Cobrança",
            replace_existing=True,
            misfire_grace_time=3600,
            coalesce=True,
            max_instances=1,
        )
        logger.info(
            f"[Scheduler] Horário de disparo de hoje ({horario_disparo}) já ultrapassado ({agora.strftime('%H:%M')}). "
            f"Recuperação agendada para {run_date}."
        )
        return True

    return False


def start_scheduler_and_worker(
    horario_disparo: str = HORARIO_DISPARO_PADRAO,
    agendar_recuperacao: bool = True,
) -> None:
    """Inicia o scheduler diário e o worker anti-ban da fila de WhatsApp."""
    global scheduler, worker_task

    trigger = criar_trigger_regua(horario_disparo)

    # 1. Inicia o worker assíncrono da fila anti-ban do WhatsApp
    queue = get_global_whatsapp_queue()
    worker_task = asyncio.create_task(queue.start_worker())
    logger.info("[Scheduler] Worker de fila WhatsApp iniciado com sucesso.")

    # 2. Configura o agendador diário
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        executar_rotina_diaria_cobranca,
        trigger=trigger,
        id=JOB_ID_REGUA,
        name="Régua Diária de Cobrança do Club Maravilha",
        replace_existing=True,
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )

    if agendar_recuperacao:
        agendar_recuperacao_se_necessario(horario_disparo)

    scheduler.start()
    logger.info(f"[Scheduler] APScheduler iniciado. Próximo disparo diário agendado para {horario_disparo}.")


def reagendar_regua(horario_disparo: str) -> bool:
    """
    Reagenda o job da régua de cobrança para um novo horário.
    Retorna True se alterado com sucesso ou False caso o scheduler não esteja rodando.
    """
    trigger = criar_trigger_regua(horario_disparo)

    if scheduler is None or not scheduler.running:
        logger.info("[Scheduler] Scheduler não está rodando; reagendamento ignorado.")
        return False

    scheduler.reschedule_job(JOB_ID_REGUA, trigger=trigger)
    logger.info(f"[Scheduler] Régua reagendada com sucesso para {horario_disparo}.")
    return True


async def sincronizar_horario_regua() -> str:
    """
    Lê o horário de disparo salvo na Configuracao do banco de dados e
    aplica o reagendamento no scheduler ativo.
    """
    async with AsyncSessionLocal() as session:
        config = await ConfiguracaoRepository(session).get_or_create()
        horario = config.horario_disparo or HORARIO_DISPARO_PADRAO

    reagendar_regua(horario)
    return horario


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
