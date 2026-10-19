"""
Testes da configuração do provedor de WhatsApp: factory estrita, validação/aviso no startup e
delays anti-ban padrão do briefing.

Feature 4 (contrato atualizado): o padrão de produção de WHATSAPP_PROVIDER passa a ser BAILEYS (motor
próprio em ./whatsapp-engine); o provedor legado EVOLUTION_API foi removido e agora é rejeitado como
desconhecido. A suíte de testes força MOCK (tests/conftest.py) para nunca falar com o engine.
"""
import logging
from unittest.mock import MagicMock

import pytest

import app.main as main
from app.core.config import Settings, settings
from app.services.whatsapp_service import (
    BaileysWhatsAppProvider,
    MockWhatsAppProvider,
    check_whatsapp_provider_on_startup,
    get_whatsapp_provider,
)


def test_provedor_padrao_de_producao_e_baileys():
    assert Settings.model_fields["WHATSAPP_PROVIDER"].default == "BAILEYS"


def test_suite_de_testes_roda_com_provedor_mock():
    assert settings.WHATSAPP_PROVIDER == "MOCK"
    assert isinstance(get_whatsapp_provider(), MockWhatsAppProvider)


def test_delays_anti_ban_padrao_seguem_o_briefing():
    assert Settings.model_fields["WHATSAPP_MIN_DELAY_SECONDS"].default == 8.0
    assert Settings.model_fields["WHATSAPP_MAX_DELAY_SECONDS"].default == 20.0


@pytest.mark.parametrize(
    "valor,classe",
    [
        ("MOCK", MockWhatsAppProvider),
        ("mock", MockWhatsAppProvider),
        ("TEST", MockWhatsAppProvider),
        ("  Mock  ", MockWhatsAppProvider),
        ("BAILEYS", BaileysWhatsAppProvider),
        ("baileys", BaileysWhatsAppProvider),
    ],
)
def test_factory_reconhece_os_provedores_aceitos(valor, classe):
    assert isinstance(get_whatsapp_provider(valor), classe)


@pytest.mark.parametrize("valor", ["EVOLUTION_API", "EVOLUTION", "evolution-api", "qualquer", "123"])
def test_factory_rejeita_provedor_desconhecido(valor):
    with pytest.raises(ValueError, match="desconhecido"):
        get_whatsapp_provider(valor)


def test_factory_sem_argumento_usa_o_provedor_configurado(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", "MOCK")
    assert isinstance(get_whatsapp_provider(), MockWhatsAppProvider)

    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", "BAILEYS")
    assert isinstance(get_whatsapp_provider(), BaileysWhatsAppProvider)


@pytest.mark.parametrize("configurado", ["", "EVOLUTION_API"])
def test_factory_rejeita_configuracao_vazia_ou_desconhecida(monkeypatch, configurado):
    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", configurado)

    with pytest.raises(ValueError, match="desconhecido"):
        get_whatsapp_provider()


# ------------------------------------------------------------------------------
# Validação e aviso no startup
# ------------------------------------------------------------------------------
def test_startup_avisa_quando_mock_em_producao(monkeypatch, caplog):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", "MOCK")

    with caplog.at_level(logging.WARNING):
        check_whatsapp_provider_on_startup()

    avisos = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(avisos) == 1
    assert "WHATSAPP_PROVIDER=MOCK" in avisos[0].getMessage()
    assert "nenhuma mensagem será enviada" in avisos[0].getMessage()


@pytest.mark.parametrize(
    "ambiente,provedor",
    [
        ("development", "MOCK"),
        ("test", "MOCK"),
        ("production", "BAILEYS"),
    ],
)
def test_startup_nao_avisa_fora_do_caso_mock_em_producao(monkeypatch, caplog, ambiente, provedor):
    monkeypatch.setattr(settings, "ENVIRONMENT", ambiente)
    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", provedor)

    with caplog.at_level(logging.WARNING):
        check_whatsapp_provider_on_startup()

    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_startup_falha_com_provedor_desconhecido(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", "PROVEDOR_INVALIDO")

    with pytest.raises(ValueError, match="PROVEDOR_INVALIDO"):
        check_whatsapp_provider_on_startup()


async def test_lifespan_valida_o_provedor_antes_de_tocar_no_banco(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", "PROVEDOR_INVALIDO")
    engine = MagicMock()  # qualquer uso indicaria que o banco foi acessado antes da validação
    monkeypatch.setattr(main, "async_engine", engine)

    with pytest.raises(ValueError, match="desconhecido"):
        async with main.lifespan(main.app):
            pass

    engine.begin.assert_not_called()
