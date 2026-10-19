"""
Testes de integração para as melhorias de code review da Feature 5 (API REST & Segurança).

Itens cobertos:
Item 1: toda APIRoute despachável sem token retorna 401 (exceto rotas públicas)
Item 2: endpoints da catraca protegidos por X-Turnstile-Token (401 sem/errado, 200 com correto)
Item 5: validação de tamanho de payload de login (e-mail com 10k chars -> 422)
Item 6: chaves de rate limit isoladas por IP do cliente
Item 9: agregação SQL de disparos do dia corrente no fuso do clube (ontem 23:59, hoje 00:01, amanhã)
Item 10: timeout no status do WhatsApp impedindo travamento do dashboard
"""
import asyncio
from datetime import datetime, timedelta, timezone
import time
from typing import Dict, Any
from unittest.mock import AsyncMock

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from httpx import AsyncClient
from zoneinfo import ZoneInfo

from app.core import clock
from app.core.config import settings
from app.core.rate_limit import login_rate_limiter
from app.main import app
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.services.whatsapp_service import WhatsAppProvider


# ==============================================================================
# Item 1: Todas as APIRoutes despacháveis não-públicas retornam 401 sem token
# ==============================================================================
@pytest.mark.asyncio
async def test_todas_as_rotas_reais_respondem_401_sem_token(async_client_sem_auth: AsyncClient):
    """
    Percorre todos os route contexts da aplicação. Para cada APIRoute não-pública despachável,
    executa uma requisição sem cabeçalho Authorization e garante HTTP 401.
    """
    prefixos_publicos = ("/api/v1/webhooks/", "/api/v1/catraca/")
    rotas_publicas = {
        ("GET", "/api/v1/health"),
        ("POST", "/api/v1/auth/login"),
        ("GET", "/api/v1/openapi.json"),
    }

    rotas_testadas = 0
    for rc in iter_route_contexts(app.routes):
        if not rc.path.startswith("/api/v1/"):
            continue
        if rc.path.startswith(prefixos_publicos) or any((m, rc.path) in rotas_publicas for m in rc.methods):
            continue

        # Monta caminho substituindo parâmetros como {associado_id} por um ID fixo
        caminho_teste = rc.path
        for param in ["associado_id", "fatura_id", "agendamento_id", "convidado_id"]:
            caminho_teste = caminho_teste.replace(f"{{{param}}}", "00000000-0000-0000-0000-000000000001")

        for metodo in rc.methods:
            if metodo in ("OPTIONS", "HEAD"):
                continue
            resp = await async_client_sem_auth.request(metodo, caminho_teste)
            assert resp.status_code == 401, f"Rota desprotegida encontrada: {metodo} {caminho_teste}"
            rotas_testadas += 1

    assert rotas_testadas >= 25, f"Esperado testar ao menos 25 rotas administrativas, testadas: {rotas_testadas}"


# ==============================================================================
# Item 2: Proteção da Catraca por X-Turnstile-Token
# ==============================================================================
@pytest.mark.asyncio
async def test_catraca_exige_token_x_turnstile(async_client_sem_auth: AsyncClient):
    """Verifica que /catraca/whitelist rejeita requisições sem o header ou com token incorreto."""
    # 1. Sem o header -> 401
    r_sem_header = await async_client_sem_auth.get("/api/v1/catraca/whitelist")
    assert r_sem_header.status_code == 401

    # 2. Com token incorreto -> 401
    r_token_errado = await async_client_sem_auth.get(
        "/api/v1/catraca/whitelist",
        headers={"X-Turnstile-Token": "token_invalido_123"},
    )
    assert r_token_errado.status_code == 401

    # 3. Com token correto -> 200
    r_token_correto = await async_client_sem_auth.get(
        "/api/v1/catraca/whitelist",
        headers={"X-Turnstile-Token": settings.TURNSTILE_API_TOKEN},
    )
    assert r_token_correto.status_code == 200


# ==============================================================================
# Item 5: Validação de Payload no Login (Pydantic max_length)
# ==============================================================================
@pytest.mark.asyncio
async def test_login_payload_com_email_gigante_retorna_422(async_client_sem_auth: AsyncClient):
    """E-mail com 10.000 caracteres deve ser rejeitado de imediato com 422 Unprocessable Content."""
    email_gigante = "a" * 10000 + "@club.com"
    resp = await async_client_sem_auth.post(
        "/api/v1/auth/login",
        json={"email": email_gigante, "senha": "qualquer_senha"},
    )
    assert resp.status_code == 422


# ==============================================================================
# Item 6: Rate Limiting com Isolamento por Host
# ==============================================================================
@pytest.mark.asyncio
async def test_login_rate_limiting_chaves_distintas_por_cliente(db_session):
    """Dois clientes com IPs distintos geram chaves independentes no login_rate_limiter."""
    from app.api.v1.endpoints.auth import login, LoginRequest
    from starlette.requests import Request

    def _criar_req_com_ip(ip: str):
        return Request({"type": "http", "client": (ip, 1234), "headers": []})

    email = "admin@clubmaravilha.com.br"
    req_ip1 = _criar_req_com_ip("192.168.1.10")
    req_ip2 = _criar_req_com_ip("192.168.1.20")

    # 5 falhas no IP 1
    for _ in range(5):
        try:
            await login(LoginRequest(email=email, senha="errada"), req_ip1, db_session)
        except Exception:
            pass

    assert login_rate_limiter.bloqueado(f"192.168.1.10|{email}") is True
    assert login_rate_limiter.bloqueado(f"192.168.1.20|{email}") is False


# ==============================================================================
# Item 9: Dashboard com Agregação SQL de Disparos do Dia Local
# ==============================================================================
@pytest.mark.asyncio
async def test_dashboard_contagem_disparos_apenas_do_dia_corrente(async_client: AsyncClient, db_session):
    """
    Insere mensagens enviadas ontem às 23:59 BRT, hoje às 00:01 BRT e amanhã.
    O endpoint de dashboard deve contabilizar exatamente 1 disparo no dia.
    """
    tz = ZoneInfo(settings.TIMEZONE)
    agora_local = datetime.now(tz)

    hoje_zero_hora = datetime(agora_local.year, agora_local.month, agora_local.day, 0, 0, 0, tzinfo=tz)

    ontem_23_59_local = hoje_zero_hora - timedelta(minutes=1)
    hoje_00_01_local = hoje_zero_hora + timedelta(minutes=1)
    amanha_local = hoje_zero_hora + timedelta(days=1, hours=2)

    log_ontem = LogMensagem(
        destinatario="5575999999991",
        etapa=EtapaRegua.AVULSO,
        mensagem="Mensagem de ontem",
        status=StatusEnvio.SUCESSO,
        enviado_em=ontem_23_59_local.astimezone(timezone.utc),
    )
    log_hoje = LogMensagem(
        destinatario="5575999999992",
        etapa=EtapaRegua.AVULSO,
        mensagem="Mensagem de hoje",
        status=StatusEnvio.SUCESSO,
        enviado_em=hoje_00_01_local.astimezone(timezone.utc),
    )
    log_amanha = LogMensagem(
        destinatario="5575999999993",
        etapa=EtapaRegua.AVULSO,
        mensagem="Mensagem de amanhã",
        status=StatusEnvio.SUCESSO,
        enviado_em=amanha_local.astimezone(timezone.utc),
    )

    db_session.add_all([log_ontem, log_hoje, log_amanha])
    await db_session.commit()

    resp = await async_client.get("/api/v1/dashboard/resumo")
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["disparos_hoje"] == 1


# ==============================================================================
# Item 10: Timeout no Status do WhatsApp
# ==============================================================================
@pytest.mark.asyncio
async def test_dashboard_whatsapp_status_timeout_retorna_desconectado(async_client: AsyncClient):
    """
    Um provider de WhatsApp lento (com sleep de 10s) deve sofrer timeout de 3s
    e o dashboard responder em menos de 4s com status DESCONECTADO.
    """
    from app.api.v1.endpoints.whatsapp import get_provider

    class SlowWhatsAppProvider(WhatsAppProvider):
        async def get_connection_status(self) -> Dict[str, Any]:
            await asyncio.sleep(10.0)
            return {"status": "CONECTADO"}

        async def get_qr_code(self) -> Dict[str, Any]:
            return {}

        async def send_message(self, phone: str, text: str) -> Dict[str, Any]:
            return {}

        async def logout(self) -> Dict[str, Any]:
            return {}

        async def restart(self) -> Dict[str, Any]:
            return {}

    app.dependency_overrides[get_provider] = lambda: SlowWhatsAppProvider()

    t_inicio = time.perf_counter()
    resp = await async_client.get("/api/v1/dashboard/resumo")
    duracao_s = time.perf_counter() - t_inicio

    assert resp.status_code == 200
    dados = resp.json()
    assert dados["whatsapp_status"] == "DESCONECTADO"
    assert duracao_s < 4.0, f"Dashboard demorou {duracao_s}s (esperado < 4.0s)"

    app.dependency_overrides.pop(get_provider, None)
