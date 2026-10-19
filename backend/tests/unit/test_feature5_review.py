"""
Testes unitários para as melhorias de code review da Feature 5 (Admin & Segurança).

Itens cobertos:
Item 1: app.openapi() sem warnings de operation id duplicado
Item 2: infraestrutura do nginx com restrição por CIDR LAN para a catraca
Item 3: mitigação de timing attack (verificar_senha chamado exatamente 1x)
Item 4: bcrypt desacoplado do event loop via asyncio.to_thread
Item 5: gerenciamento de memória do rate limiter (sem vazamento de chaves e teto 10k)
Item 6: configuração de IP real e isolamento por host
Item 7: validação de segredos padrão em ambiente de produção
Item 8: validação de complexidade e tamanho de senha no seed
"""
import asyncio
import os
import re
import secrets
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.routing import APIRoute, iter_route_contexts

from app.core.config import Settings
from app.core.rate_limit import LoginRateLimiter
from app.core.security import hash_senha
from app.main import app
from app.models.usuario_admin import UsuarioAdmin
from scripts.seed_admin import seed_admin


# ==============================================================================
# Item 1: OpenAPI Schema Limpo (Sem Duplicidade de Operation ID)
# ==============================================================================
def test_openapi_schema_sem_operation_id_duplicado():
    """Garante que a documentação OpenAPI gerada não contém operation IDs duplicados nem rotas fantasmas."""
    schema = app.openapi()
    operation_ids = []
    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if isinstance(operation, dict) and "operationId" in operation:
                operation_ids.append(operation["operationId"])

    duplicados = [op for op in set(operation_ids) if operation_ids.count(op) > 1]
    assert duplicados == [], f"Operation IDs duplicados encontrados no OpenAPI: {duplicados}"


# ==============================================================================
# Item 2 & 6: Infraestrutura Docker / Nginx
# ==============================================================================
def test_infra_nginx_catraca_cidr_e_forwarded_for():
    """Verifica que o nginx restringe a catraca por CIDR LAN e sobrescreve X-Forwarded-For com remote_addr."""
    caminho_nginx = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "docker", "nginx", "default.conf"
    )
    with open(caminho_nginx, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Bloco da catraca
    assert "location /api/v1/catraca/" in conteudo
    assert "allow 192.168.0.0/16;" in conteudo
    assert "allow 10.0.0.0/8;" in conteudo
    assert "deny all;" in conteudo

    # Sobrescrita de X-Forwarded-For (não anexar)
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in conteudo
    assert "$proxy_add_x_forwarded_for" not in conteudo


def test_infra_uvicorn_proxy_headers():
    """Verifica que o comando do uvicorn em produção inclui as flags necessárias para confiar no proxy reverso."""
    caminho_compose = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "docker-compose.prod.yml"
    )
    with open(caminho_compose, "r", encoding="utf-8") as f:
        conteudo = f.read()

    assert "--proxy-headers" in conteudo
    assert "--forwarded-allow-ips" in conteudo


# ==============================================================================
# Item 3: Mitigação de Timing Attack na Autenticação
# ==============================================================================
@pytest.mark.asyncio
async def test_verificar_senha_chamado_exatamente_uma_vez_para_todos_os_casos(db_session):
    """
    verificar_senha deve ser chamado exatamente 1 vez tanto para e-mail inexistente,
    quanto para usuário inativo e senha incorreta, impedindo enumeração por tempo de CPU.
    """
    from app.api.v1.endpoints.auth import login, LoginRequest
    from starlette.requests import Request

    def _criar_request():
        scope = {
            "type": "http",
            "client": ("127.0.0.1", 12345),
            "headers": [],
        }
        return Request(scope)

    # 1. Usuário ativo existente
    usuario_ativo = UsuarioAdmin(
        nome="Admin Ativo",
        email="ativo@clubmaravilha.com.br",
        senha_hash=hash_senha("senha_correta_123"),
        ativo=True,
    )
    # 2. Usuário inativo existente
    usuario_inativo = UsuarioAdmin(
        nome="Admin Inativo",
        email="inativo@clubmaravilha.com.br",
        senha_hash=hash_senha("senha_correta_123"),
        ativo=False,
    )
    db_session.add_all([usuario_ativo, usuario_inativo])
    await db_session.commit()

    with patch("app.api.v1.endpoints.auth.verificar_senha", wraps=lambda s, h: False) as spy_verificar:
        # Caso A: e-mail inexistente
        spy_verificar.reset_mock()
        req = _criar_request()
        with pytest.raises(Exception):
            await login(LoginRequest(email="inexistente@clubmaravilha.com.br", senha="qq"), req, db_session)
        assert spy_verificar.call_count == 1, "Deve verificar senha mesmo para usuário inexistente (dummy hash)"

        # Caso B: usuário inativo
        spy_verificar.reset_mock()
        with pytest.raises(Exception):
            await login(LoginRequest(email="inativo@clubmaravilha.com.br", senha="qq"), req, db_session)
        assert spy_verificar.call_count == 1, "Deve verificar senha para usuário inativo antes de rejeitar"

        # Caso C: senha errada para usuário ativo
        spy_verificar.reset_mock()
        with pytest.raises(Exception):
            await login(LoginRequest(email="ativo@clubmaravilha.com.br", senha="senha_errada"), req, db_session)
        assert spy_verificar.call_count == 1, "Deve verificar senha para senha errada"


# ==============================================================================
# Item 4: bcrypt no Event Loop (asyncio.to_thread)
# ==============================================================================
@pytest.mark.asyncio
async def test_bcrypt_nao_bloqueia_event_loop_concorrente(async_client_sem_auth):
    """
    Uma verificação lenta de bcrypt (simulada com sleep síncrono de 300ms) executada via
    to_thread não pode bloquear requisições concorrentes de health check no event loop.
    """
    from app.main import app

    def _slow_verificar(senha, hash_val):
        time.sleep(0.3)
        return False

    with patch("app.api.v1.endpoints.auth.verificar_senha", side_effect=_slow_verificar):
        # Dispara login lento e medição concorrente de /api/v1/health
        task_login = asyncio.create_task(
            async_client_sem_auth.post("/api/v1/auth/login", json={"email": "teste@club.com", "senha": "x" * 12})
        )
        await asyncio.sleep(0.05)  # Garante que o login entrou em execução

        t_inicio = time.perf_counter()
        health_resp = await async_client_sem_auth.get("/api/v1/health")
        duracao_health_ms = (time.perf_counter() - t_inicio) * 1000

        assert health_resp.status_code == 200
        assert duracao_health_ms < 100, f"Health check demorou {duracao_health_ms}ms (esperado < 100ms)"

        await task_login


# ==============================================================================
# Item 5: Gerenciamento de Memória no Rate Limiter
# ==============================================================================
def test_rate_limiter_bloqueado_nao_cria_entradas():
    """Chamar bloqueado() para 1000 chaves distintas sem falha não deve alocar nenhuma entrada."""
    limiter = LoginRateLimiter(max_falhas=5, janela_segundos=60)
    for i in range(1000):
        assert limiter.bloqueado(f"chave_inexistente_{i}") is False
    assert len(limiter._falhas) == 0


def test_rate_limiter_limpar_expiradas_remove_chave():
    """Quando as falhas de uma chave expiram, ela deve ser removida do dicionário."""
    tempo_atual = 100.0
    limiter = LoginRateLimiter(max_falhas=5, janela_segundos=60, relogio=lambda: tempo_atual)

    limiter.registrar_falha("chave_teste")
    assert "chave_teste" in limiter._falhas

    # Avança o tempo além da janela de 60s
    tempo_atual = 170.0
    assert limiter.bloqueado("chave_teste") is False
    assert "chave_teste" not in limiter._falhas


def test_rate_limiter_teto_capacidade_10k_chaves():
    """Ao atingir o teto de 10k chaves, descarta a chave mais antiga."""
    limiter = LoginRateLimiter(max_falhas=5, janela_segundos=3600, max_chaves=10)
    for i in range(10):
        limiter.registrar_falha(f"chave_{i}")
    assert len(limiter._falhas) == 10
    assert "chave_0" in limiter._falhas

    # Adiciona a 11ª chave: chave_0 deve ter sido descartada
    limiter.registrar_falha("chave_10")
    assert len(limiter._falhas) == 10
    assert "chave_0" not in limiter._falhas
    assert "chave_10" in limiter._falhas


# ==============================================================================
# Item 7: Validação de Segredos em Produção
# ==============================================================================
def test_settings_producao_rejeita_segredos_padrao_e_curtos():
    """Em ambiente de produção, Settings deve levantar RuntimeError para segredos inseguros."""
    # SECRET_KEY default
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="insecure_dev_secret_key_change_in_production_12345",
            PIX_WEBHOOK_SECRET="segredo_forte_customizado_12345678",
        )

    # SECRET_KEY do .env.example
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="change_this_to_a_very_secure_random_secret_key_at_least_32_chars",
            PIX_WEBHOOK_SECRET="segredo_forte_customizado_12345678",
        )

    # SECRET_KEY com menos de 32 chars
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="chave_curta",
            PIX_WEBHOOK_SECRET="segredo_forte_customizado_12345678",
        )

    # PIX_WEBHOOK_SECRET default
    with pytest.raises(RuntimeError, match="PIX_WEBHOOK_SECRET"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY=secrets.token_urlsafe(48),
            PIX_WEBHOOK_SECRET="mock_webhook_secret_dev",
        )

    # Sucesso com segredos robustos
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=secrets.token_urlsafe(48),
        PIX_WEBHOOK_SECRET="segredo_webhook_super_seguro_producao_2026",
    )
    assert s.ENVIRONMENT == "production"


# ==============================================================================
# Item 8: Validação de Senha Forte no Seed
# ==============================================================================
@pytest.mark.asyncio
async def test_seed_admin_validacoes_de_senha(db_session):
    """Seed deve validar tamanho máximo de 72 bytes sempre e mínimo de 12 chars em produção."""
    # 1. Senha maior que 72 bytes (limite do bcrypt)
    senha_longa = "a" * 73
    with pytest.raises(ValueError, match="72 bytes"):
        await seed_admin(db_session, "adm@club.com", senha_longa)

    # 2. Senha fraca em produção (< 12 chars)
    with patch("scripts.seed_admin.settings.ENVIRONMENT", "production"):
        with pytest.raises(ValueError, match="12 caracteres"):
            await seed_admin(db_session, "adm@club.com", "curta123")

        # 3. Senha padrão do .env.example em produção
        with pytest.raises(ValueError, match=".env.example"):
            await seed_admin(db_session, "adm@club.com", "admin_secret_password_change_in_prod")
