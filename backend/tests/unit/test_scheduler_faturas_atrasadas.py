"""
Testes da integração da marcação de atraso com a rotina diária do scheduler (Feature 3).

Contrato: `app.jobs.billing_scheduler.executar_rotina_diaria_cobranca` chama
`FaturaService(session).marcar_faturas_atrasadas()` ANTES da régua
(`BillingEngineService.processar_regua_diaria`). Falha na marcação é registrada em log e
não impede a régua de rodar.
"""
from unittest.mock import AsyncMock, MagicMock, patch

from app.jobs.billing_scheduler import executar_rotina_diaria_cobranca


def _relatorio():
    relatorio = MagicMock()
    relatorio.total_enfileirados = 0
    relatorio.inadimplentes_atualizados = 0
    return relatorio


async def test_rotina_diaria_marca_atrasadas_antes_da_regua():
    ordem = []
    with patch("app.jobs.billing_scheduler.FaturaService") as MockFatura, \
         patch("app.jobs.billing_scheduler.BillingEngineService") as MockEngine:
        MockFatura.return_value.marcar_faturas_atrasadas = AsyncMock(
            side_effect=lambda *a, **k: ordem.append("atrasadas") or 2
        )
        MockEngine.return_value.processar_regua_diaria = AsyncMock(
            side_effect=lambda *a, **k: ordem.append("regua") or _relatorio()
        )

        await executar_rotina_diaria_cobranca()

    assert ordem == ["atrasadas", "regua"]


async def test_falha_na_marcacao_nao_impede_a_regua():
    with patch("app.jobs.billing_scheduler.FaturaService") as MockFatura, \
         patch("app.jobs.billing_scheduler.BillingEngineService") as MockEngine:
        MockFatura.return_value.marcar_faturas_atrasadas = AsyncMock(side_effect=RuntimeError("db fora"))
        MockEngine.return_value.processar_regua_diaria = AsyncMock(return_value=_relatorio())

        await executar_rotina_diaria_cobranca()

        MockEngine.return_value.processar_regua_diaria.assert_awaited_once()
