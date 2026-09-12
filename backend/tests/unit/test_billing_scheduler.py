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
