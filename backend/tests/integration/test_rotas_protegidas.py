"""
Feature 5 - Proteção das rotas administrativas com `get_current_admin` (app/api/deps.py).

Contratos:
- `app.api.deps.get_current_admin` é a dependência FastAPI que valida o Bearer JWT e devolve o
  `UsuarioAdmin` ativo; falha -> 401 {"detail"} com header WWW-Authenticate: Bearer.
- TODAS as rotas sob /api/v1 dependem (direta ou indiretamente) de `get_current_admin`, EXCETO as
  públicas abaixo (inclusive rotas futuras, como configuração, entram protegidas automaticamente):
    * GET  /api/v1/health                (monitoramento/docker)
    * POST /api/v1/auth/login            (obtém o token)
    * /api/v1/webhooks/*                 (autenticados pelo próprio segredo do gateway Pix)
    * /api/v1/catraca/*                  (equipamento na rede local; mecanismo atual preservado)
  Protegidos: associados, faturas, convidados, agendamentos, whatsapp, dashboard e /auth/me.
- Fixture `async_client` (conftest) já autentica por override; `async_client_sem_auth` não.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient
from jose import jwt

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.security import criar_access_token, hash_senha
from app.main import app
from app.models.usuario_admin import UsuarioAdmin

ID = str(uuid.uuid4())

PREFIXOS_PUBLICOS = ("/api/v1/webhooks/", "/api/v1/catraca/")
ROTAS_PUBLICAS = {("GET", "/api/v1/health"), ("POST", "/api/v1/auth/login")}

ROTAS_ADMIN = [
    ("GET", "/api/v1/associados/"),
    ("POST", "/api/v1/associados/"),
    ("GET", f"/api/v1/associados/{ID}"),
    ("PATCH", f"/api/v1/associados/{ID}"),
    ("DELETE", f"/api/v1/associados/{ID}"),
    ("POST", f"/api/v1/associados/{ID}/convidados"),
    ("POST", "/api/v1/associados/importar"),
    ("GET", "/api/v1/faturas/"),
    ("POST", "/api/v1/faturas/gerar-mes"),
    ("POST", "/api/v1/faturas/marcar-atrasadas"),
    ("POST", "/api/v1/faturas/executar-regua"),
    ("POST", f"/api/v1/faturas/{ID}/baixa-manual"),
    ("POST", f"/api/v1/faturas/{ID}/cobrar-whatsapp"),
    ("GET", "/api/v1/convidados/"),
    ("POST", "/api/v1/convidados/"),
    ("GET", f"/api/v1/convidados/cota/{ID}"),
    ("GET", "/api/v1/agendamentos/"),
    ("GET", "/api/v1/whatsapp/status"),
    ("GET", "/api/v1/whatsapp/qrcode"),
    ("POST", "/api/v1/whatsapp/desconectar"),
    ("POST", "/api/v1/whatsapp/reiniciar"),
    ("POST", "/api/v1/whatsapp/teste-envio"),
    ("GET", "/api/v1/whatsapp/logs"),
    ("GET", "/api/v1/dashboard/resumo"),
    ("GET", "/api/v1/dashboard/atividades"),
    ("GET", "/api/v1/auth/me"),
]


def _depende_de(dependant, alvo) -> bool:
    for sub in dependant.dependencies:
        if sub.call is alvo or _depende_de(sub, alvo):
            return True
    return False


def _rota_publica(path: str, methods: set) -> bool:
    if path.startswith(PREFIXOS_PUBLICOS):
        return True
    return all((m, path) in ROTAS_PUBLICAS for m in methods)


async def _token_valido(db_session) -> str:
    usuario = UsuarioAdmin(nome="Diretoria", email="diretoria@clubmaravilha.com.br", senha_hash=hash_senha("x" * 12))
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return criar_access_token(str(usuario.id))


# ------------------------------------------------------------------------------
# Estrutural: nenhuma rota admin fica sem autenticação (inclui rotas futuras)
# ------------------------------------------------------------------------------
def test_todas_as_rotas_nao_publicas_dependem_de_get_current_admin():
    desprotegidas = []
    for rota in app.routes:
        if not isinstance(rota, APIRoute) or not rota.path.startswith("/api/v1/"):
            continue
        if _rota_publica(rota.path, set(rota.methods)):
            continue
        if not _depende_de(rota.dependant, get_current_admin):
            desprotegidas.append(f"{sorted(rota.methods)} {rota.path}")
    assert desprotegidas == []


def test_rotas_publicas_nao_dependem_de_get_current_admin():
    encontradas = set()
    for rota in app.routes:
        if not isinstance(rota, APIRoute):
            continue
        if rota.path.startswith(PREFIXOS_PUBLICOS) or any((m, rota.path) in ROTAS_PUBLICAS for m in rota.methods):
            assert not _depende_de(rota.dependant, get_current_admin), rota.path
            encontradas.add(rota.path)
    assert "/api/v1/health" in encontradas
    assert "/api/v1/auth/login" in encontradas
    assert "/api/v1/webhooks/pix" in encontradas
    assert "/api/v1/catraca/whitelist" in encontradas


def test_dashboard_e_auth_estao_registrados():
    caminhos = {rota.path for rota in app.routes if isinstance(rota, APIRoute)}
    assert {"/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/dashboard/resumo", "/api/v1/dashboard/atividades"} <= caminhos


# ------------------------------------------------------------------------------
# HTTP: 401 sem token / token inválido / expirado
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("metodo,caminho", ROTAS_ADMIN)
async def test_rota_admin_sem_token_retorna_401(async_client_sem_auth: AsyncClient, metodo, caminho):
    res = await async_client_sem_auth.request(metodo, caminho)
    assert res.status_code == 401, f"{metodo} {caminho} -> {res.status_code}"
    assert res.headers.get("www-authenticate", "").lower().startswith("bearer")


@pytest.mark.parametrize("metodo,caminho", [("GET", "/api/v1/associados/"), ("GET", "/api/v1/faturas/"), ("GET", "/api/v1/dashboard/resumo")])
async def test_rota_admin_com_token_invalido_retorna_401(async_client_sem_auth: AsyncClient, metodo, caminho):
    res = await async_client_sem_auth.request(metodo, caminho, headers={"Authorization": "Bearer invalido"})
    assert res.status_code == 401


async def test_rota_admin_com_token_expirado_retorna_401(async_client_sem_auth: AsyncClient, db_session):
    usuario = UsuarioAdmin(nome="Diretoria", email="d@clubmaravilha.com.br", senha_hash=hash_senha("x" * 12))
    db_session.add(usuario)
    await db_session.commit()
    expirado = jwt.encode(
        {"sub": str(usuario.id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    res = await async_client_sem_auth.get("/api/v1/associados/", headers={"Authorization": f"Bearer {expirado}"})
    assert res.status_code == 401


async def test_rota_admin_com_token_valido_passa(async_client_sem_auth: AsyncClient, db_session):
    token = await _token_valido(db_session)
    res = await async_client_sem_auth.get("/api/v1/associados/", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["total"] == 0


async def test_async_client_padrao_continua_autenticado(async_client: AsyncClient):
    """O override do conftest mantém os testes antigos funcionando sem token."""
    res = await async_client.get("/api/v1/associados/")
    assert res.status_code == 200


# ------------------------------------------------------------------------------
# Rotas públicas continuam sem autenticação
# ------------------------------------------------------------------------------
async def test_health_continua_publico(async_client_sem_auth: AsyncClient):
    res = await async_client_sem_auth.get("/api/v1/health")
    assert res.status_code == 200


async def test_catraca_whitelist_continua_publica(async_client_sem_auth: AsyncClient):
    res = await async_client_sem_auth.get("/api/v1/catraca/whitelist")
    assert res.status_code == 200


async def test_webhook_pix_nao_exige_bearer(async_client_sem_auth: AsyncClient):
    """O webhook continua protegido apenas pelo segredo do gateway (não pelo JWT do admin)."""
    res = await async_client_sem_auth.post(
        "/api/v1/webhooks/pix",
        json={"pix": []},
        headers={"X-Webhook-Secret": settings.PIX_WEBHOOK_SECRET},
    )
    # 400 = payload sem txid: passou da autenticação e chegou ao processamento do webhook
    assert res.status_code == 400
    assert "bearer" not in res.headers.get("www-authenticate", "").lower()
