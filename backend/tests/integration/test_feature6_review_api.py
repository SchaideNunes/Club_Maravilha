"""
Testes de integração para as correções obrigatórias de code review da Feature 6 (Agente 3).

Itens cobertos:
Item 1: configuracao_service - reagendar_regua lança exceção -> capturada sem relançar, PATCH responde 200 e horário salvo.
Item 5: configuracao schema/service - chave_pix com espaços vira None; preview sem chave usa placeholder [CHAVE PIX NÃO CONFIGURADA].
Item 6: whatsapp endpoint - teste-envio com rate limiter (5 req/min por admin) -> 6º POST retorna 429 com Retry-After e sem envio extra.
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.v1.endpoints.whatsapp import get_provider
from app.core.rate_limit import teste_envio_rate_limiter
from app.main import app
from app.models.configuracao import Configuracao
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.whatsapp_service import MockWhatsAppProvider

API_CONFIG = "/api/v1/configuracao"
API_WHATSAPP = "/api/v1/whatsapp"


class ProviderContador(MockWhatsAppProvider):
    """Provedor para auditar envios reais disparados."""

    def __init__(self) -> None:
        super().__init__()
        self.total_envios = 0

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        self.total_envios += 1
        return await super().send_message(phone, message)


# ==============================================================================
# Item 1: Resiliência no reagendamento da régua de cobrança
# ==============================================================================
@pytest.mark.asyncio
async def test_patch_horario_disparo_reagendar_com_erro_responde_200_e_salva_horario(
    async_client: AsyncClient,
    db_session,
    monkeypatch,
):
    """
    Quando o scheduler falha ao reagendar a régua após a alteração do horário,
    o serviço deve logar a exceção e responder 200 com o novo horário gravado.
    """
    repo = ConfiguracaoRepository(db_session)
    config = await repo.get_or_create()
    config.horario_disparo = "08:00"
    await db_session.commit()

    def falha_reagendar(novo_horario: str):
        raise RuntimeError("Falha simulada no scheduler do APScheduler")

    from app.jobs import billing_scheduler
    monkeypatch.setattr(billing_scheduler, "reagendar_regua", falha_reagendar)

    res = await async_client.patch(
        API_CONFIG,
        json={"horario_disparo": "11:45"},
    )

    assert res.status_code == 200
    dados = res.json()
    assert dados["horario_disparo"] == "11:45"

    # Confirma persistência via GET e via banco
    persistido = (await async_client.get(API_CONFIG)).json()
    assert persistido["horario_disparo"] == "11:45"

    db_session.expire_all()
    stmt = select(Configuracao)
    salvo = (await db_session.execute(stmt)).scalar_one()
    assert salvo.horario_disparo == "11:45"


# ==============================================================================
# Item 5: Normalização da Chave Pix e Placeholder no Preview
# ==============================================================================
@pytest.mark.asyncio
async def test_patch_chave_pix_com_espacos_ou_vazia_grava_null(
    async_client: AsyncClient,
    db_session,
):
    """
    PATCH com chave_pix contendo apenas espaços em branco deve sofrer strip e gravar None (null).
    """
    repo = ConfiguracaoRepository(db_session)
    config = await repo.get_or_create()
    config.chave_pix = "pix-existente@club.com"
    await db_session.commit()

    res = await async_client.patch(
        API_CONFIG,
        json={"chave_pix": "    "},
    )

    assert res.status_code == 200
    dados = res.json()
    assert dados["chave_pix"] is None

    persistido = (await async_client.get(API_CONFIG)).json()
    assert persistido["chave_pix"] is None

    db_session.expire_all()
    stmt = select(Configuracao)
    salvo = (await db_session.execute(stmt)).scalar_one()
    assert salvo.chave_pix is None


@pytest.mark.asyncio
async def test_preview_template_com_chave_pix_vazia_usa_placeholder(
    async_client: AsyncClient,
    db_session,
):
    """
    Preview sem fatura ou com chave Pix nula deve renderizar [CHAVE PIX NÃO CONFIGURADA]
    em vez de string vazia.
    """
    repo = ConfiguracaoRepository(db_session)
    config = await repo.get_or_create()
    config.chave_pix = None
    await db_session.commit()

    res = await async_client.post(
        f"{API_CONFIG}/preview-template",
        json={"template": "Pague com a chave: {chave_pix}"},
    )

    assert res.status_code == 200
    mensagem = res.json()["mensagem"]
    assert "[CHAVE PIX NÃO CONFIGURADA]" in mensagem
    assert "{" not in mensagem and "}" not in mensagem


# ==============================================================================
# Item 6: Rate Limiting dedicado no teste-envio do WhatsApp
# ==============================================================================
@pytest.mark.asyncio
async def test_whatsapp_teste_envio_rate_limit_bloqueia_sexto_envio(
    async_client: AsyncClient,
):
    """
    6 POSTs seguidos para /api/v1/whatsapp/teste-envio:
    Os primeiros 5 são despachados com sucesso.
    O 6º recebe 429 Too Many Requests com cabeçalho Retry-After e nenhum envio extra.
    """
    provider = ProviderContador()
    app.dependency_overrides[get_provider] = lambda: provider

    try:
        teste_envio_rate_limiter.reset()

        payload = {
            "numero": "5575999990001",
            "mensagem": "Mensagem de teste de carga controlada",
        }

        # 5 envios válidos
        for i in range(5):
            res = await async_client.post(f"{API_WHATSAPP}/teste-envio", json=payload)
            assert res.status_code == 200, f"Envio {i+1} falhou com status {res.status_code}: {res.text}"

        assert provider.total_envios == 5

        # 6º envio deve ser barrado por rate limit
        res_bloqueado = await async_client.post(f"{API_WHATSAPP}/teste-envio", json=payload)
        assert res_bloqueado.status_code == 429
        assert "Retry-After" in res_bloqueado.headers
        assert int(res_bloqueado.headers["Retry-After"]) >= 1
        assert "Limite" in res_bloqueado.json()["detail"] or "excedido" in res_bloqueado.json()["detail"]

        # Nenhum send_message extra foi realizado
        assert provider.total_envios == 5
    finally:
        app.dependency_overrides.pop(get_provider, None)
        teste_envio_rate_limiter.reset()
