"""
Feature 4 - Delay anti-ban da fila de WhatsApp (padrão Flow-Zap: 8 a 20 s entre envios).

Contrato (app/services/whatsapp_queue_service.py):
- WhatsAppQueueService sem delays explícitos usa settings.WHATSAPP_MIN_DELAY_SECONDS (8.0) e
  settings.WHATSAPP_MAX_DELAY_SECONDS (20.0).
- Após CADA tentativa de envio (sucesso, resposta "error" do provider ou exceção do provider) a fila
  aguarda `asyncio.sleep(random.uniform(min_delay, max_delay))` antes do próximo item.
"""
import asyncio
import random
from typing import Any, Dict, List

import pytest

from app.services.whatsapp_queue_service import MessagePriority, WhatsAppQueueService
from app.services.whatsapp_service import MockWhatsAppProvider


class ProviderComErro(MockWhatsAppProvider):
    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        return {"status": "error", "error": "WhatsApp desconectado"}


class ProviderQueLanca(MockWhatsAppProvider):
    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        raise RuntimeError("engine fora do ar")


@pytest.fixture
def sleeps(monkeypatch) -> List[float]:
    registrados: List[float] = []

    async def _sleep_falso(segundos, *args, **kwargs):
        registrados.append(segundos)

    monkeypatch.setattr(asyncio, "sleep", _sleep_falso)
    return registrados


def test_delays_padrao_da_fila_sao_8_a_20_segundos():
    fila = WhatsAppQueueService(provider=MockWhatsAppProvider())
    assert fila.min_delay == 8.0
    assert fila.max_delay == 20.0


async def test_cada_envio_aguarda_delay_aleatorio_entre_8_e_20s(sleeps, monkeypatch):
    sorteios = []
    uniform_real = random.uniform

    def _uniform(a, b):
        sorteios.append((a, b))
        return uniform_real(a, b)

    monkeypatch.setattr(random, "uniform", _uniform)
    provider = MockWhatsAppProvider()
    fila = WhatsAppQueueService(provider=provider)

    for i in range(3):
        await fila.enqueue(f"5575999990{i:03d}", f"msg {i}", priority=MessagePriority.NORMAL)
    for _ in range(3):
        await fila.process_one()

    assert len(provider.sent_messages) == 3
    assert sorteios == [(8.0, 20.0)] * 3
    assert len(sleeps) == 3
    assert all(8.0 <= s <= 20.0 for s in sleeps)


async def test_delay_tambem_apos_resposta_de_erro_do_provider(sleeps):
    fila = WhatsAppQueueService(provider=ProviderComErro())

    await fila.enqueue("5575999990001", "msg")
    await fila.process_one()

    assert len(sleeps) == 1
    assert 8.0 <= sleeps[0] <= 20.0


async def test_delay_tambem_apos_excecao_do_provider(sleeps):
    """Falhas em sequência não podem virar rajada de tentativas contra o WhatsApp."""
    fila = WhatsAppQueueService(provider=ProviderQueLanca())

    await fila.enqueue("5575999990001", "msg 1")
    await fila.enqueue("5575999990002", "msg 2")
    await fila.process_one()
    await fila.process_one()

    assert len(sleeps) == 2
    assert all(8.0 <= s <= 20.0 for s in sleeps)


async def test_delay_respeita_intervalo_customizado(sleeps):
    fila = WhatsAppQueueService(provider=MockWhatsAppProvider(), min_delay_seconds=3.0, max_delay_seconds=4.0)

    await fila.enqueue("5575999990001", "msg")
    await fila.process_one()

    assert len(sleeps) == 1
    assert 3.0 <= sleeps[0] <= 4.0
