"""
Testes unitários para o agendador de tarefas em segundo plano (billing_scheduler).
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.jobs.billing_scheduler import (
    start_scheduler_and_worker,
    stop_scheduler_and_worker,
    executar_rotina_diaria_cobranca,
)


@pytest.mark.asyncio
async def test_executar_rotina_diaria_cobranca():
    with patch("app.jobs.billing_scheduler.BillingEngineService") as MockEngine:
        instance = MockEngine.return_value
        instance.processar_regua_diaria = AsyncMock()
        mock_report = AsyncMock()
        mock_report.total_enfileirados = 5
        mock_report.inadimplentes_atualizados = 1
        instance.processar_regua_diaria.return_value = mock_report

        await executar_rotina_diaria_cobranca()
        instance.processar_regua_diaria.assert_called_once()


@pytest.mark.asyncio
async def test_start_and_stop_scheduler_and_worker():
    start_scheduler_and_worker()
    await stop_scheduler_and_worker()


# ==============================================================================
# Feature 4 - Horário configurável da régua (Configuracao.horario_disparo) com timezone do clube
#
# Contrato (app/jobs/billing_scheduler.py):
# - HORARIO_DISPARO_PADRAO = "08:00"; JOB_ID_REGUA = "regua_cobranca_diaria".
# - criar_trigger_regua(horario_disparo: "HH:MM") -> CronTrigger(hour, minute, timezone=ZoneInfo(settings.TIMEZONE));
#   formato/valor inválido -> ValueError.
# - start_scheduler_and_worker(horario_disparo=HORARIO_DISPARO_PADRAO): agenda o job JOB_ID_REGUA com esse trigger.
# - reagendar_regua(horario_disparo) -> bool: troca o trigger do job (True); False se o scheduler não está rodando.
#   Deve ser chamada sempre que a Configuracao.horario_disparo mudar.
# - async sincronizar_horario_regua() -> str: lê a Configuracao (AsyncSessionLocal + get_or_create),
#   chama reagendar_regua(horario) e devolve o horário lido.
# ==============================================================================
from unittest.mock import MagicMock  # noqa: E402

import app.jobs.billing_scheduler as billing_scheduler  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.repositories.configuracao_repository import ConfiguracaoRepository  # noqa: E402


def _campos(trigger) -> dict:
    return {campo.name: str(campo) for campo in trigger.fields}


def test_constantes_do_agendamento():
    assert billing_scheduler.HORARIO_DISPARO_PADRAO == "08:00"
    assert billing_scheduler.JOB_ID_REGUA == "regua_cobranca_diaria"


@pytest.mark.parametrize("horario,hora,minuto", [("19:05", "19", "5"), ("08:00", "8", "0"), ("00:30", "0", "30")])
def test_criar_trigger_regua_usa_horario_e_timezone_do_clube(horario, hora, minuto):
    trigger = billing_scheduler.criar_trigger_regua(horario)

    campos = _campos(trigger)
    assert campos["hour"] == hora
    assert campos["minute"] == minuto
    assert str(trigger.timezone) == settings.TIMEZONE


@pytest.mark.parametrize("horario", ["25:00", "12:60", "8h", "", "abc", "12:5:00"])
def test_criar_trigger_regua_rejeita_horario_invalido(horario):
    with pytest.raises(ValueError):
        billing_scheduler.criar_trigger_regua(horario)


async def test_start_agenda_a_regua_no_horario_informado():
    start_scheduler_and_worker("07:30")
    try:
        job = billing_scheduler.scheduler.get_job(billing_scheduler.JOB_ID_REGUA)
        assert job is not None
        campos = _campos(job.trigger)
        assert (campos["hour"], campos["minute"]) == ("7", "30")
        assert str(job.trigger.timezone) == settings.TIMEZONE
    finally:
        await stop_scheduler_and_worker()


async def test_start_sem_horario_usa_o_padrao():
    start_scheduler_and_worker()
    try:
        job = billing_scheduler.scheduler.get_job(billing_scheduler.JOB_ID_REGUA)
        campos = _campos(job.trigger)
        assert (campos["hour"], campos["minute"]) == ("8", "0")
    finally:
        await stop_scheduler_and_worker()


async def test_reagendar_regua_troca_o_horario_do_job():
    start_scheduler_and_worker("08:00")
    try:
        assert billing_scheduler.reagendar_regua("21:15") is True
        job = billing_scheduler.scheduler.get_job(billing_scheduler.JOB_ID_REGUA)
        campos = _campos(job.trigger)
        assert (campos["hour"], campos["minute"]) == ("21", "15")
        assert str(job.trigger.timezone) == settings.TIMEZONE
    finally:
        await stop_scheduler_and_worker()


async def test_reagendar_regua_sem_scheduler_rodando_retorna_false():
    start_scheduler_and_worker()
    await stop_scheduler_and_worker()

    assert billing_scheduler.reagendar_regua("10:00") is False


async def test_reagendar_regua_rejeita_horario_invalido():
    start_scheduler_and_worker()
    try:
        with pytest.raises(ValueError):
            billing_scheduler.reagendar_regua("99:99")
        job = billing_scheduler.scheduler.get_job(billing_scheduler.JOB_ID_REGUA)
        assert (_campos(job.trigger)["hour"], _campos(job.trigger)["minute"]) == ("8", "0")
    finally:
        await stop_scheduler_and_worker()


async def test_sincronizar_horario_regua_le_a_configuracao(db_session, monkeypatch):
    from tests.conftest import TestingSessionLocal

    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.horario_disparo = "06:45"
    await db_session.commit()

    reagendar = MagicMock(return_value=True)
    monkeypatch.setattr(billing_scheduler, "AsyncSessionLocal", TestingSessionLocal)
    monkeypatch.setattr(billing_scheduler, "reagendar_regua", reagendar)

    horario = await billing_scheduler.sincronizar_horario_regua()

    assert horario == "06:45"
    reagendar.assert_called_once_with("06:45")
