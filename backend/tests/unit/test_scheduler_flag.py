"""
Testes da flag SCHEDULER_ENABLED: o agendador (APScheduler) e o worker da fila anti-ban
só devem rodar em um processo, nunca em modo de teste nem quando desligados.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.main as main
from app.core.config import Settings, settings
from app.jobs.billing_scheduler import scheduler_habilitado


class _ConexaoFalsa:
    async def run_sync(self, funcao) -> None:  # não cria tabelas de verdade
        return None


class _TransacaoFalsa:
    async def __aenter__(self) -> _ConexaoFalsa:
        return _ConexaoFalsa()

    async def __aexit__(self, *excecao) -> bool:
        return False


class _EngineFalsa:
    def __init__(self) -> None:
        self.descartada = False

    def begin(self) -> _TransacaoFalsa:
        return _TransacaoFalsa()

    async def dispose(self) -> None:
        self.descartada = True


def test_scheduler_habilitado_por_padrao():
    assert Settings.model_fields["SCHEDULER_ENABLED"].default is True


@pytest.mark.parametrize(
    "ambiente,flag,esperado",
    [
        ("production", True, True),
        ("development", True, True),
        ("production", False, False),
        ("development", False, False),
        ("test", True, False),
        ("test", False, False),
    ],
)
def test_scheduler_habilitado(monkeypatch, ambiente, flag, esperado):
    monkeypatch.setattr(settings, "ENVIRONMENT", ambiente)
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", flag)

    assert scheduler_habilitado() is esperado


@pytest.mark.parametrize("flag", [True, False])
async def test_lifespan_so_inicia_e_encerra_o_scheduler_quando_habilitado(monkeypatch, flag):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SCHEDULER_ENABLED", flag)
    engine = _EngineFalsa()
    iniciar, encerrar = MagicMock(), AsyncMock()
    monkeypatch.setattr(main, "async_engine", engine)
    monkeypatch.setattr(main, "start_scheduler_and_worker", iniciar)
    monkeypatch.setattr(main, "stop_scheduler_and_worker", encerrar)

    async with main.lifespan(main.app):
        assert iniciar.called is flag

    assert encerrar.await_count == (1 if flag else 0)
    assert engine.descartada is True
