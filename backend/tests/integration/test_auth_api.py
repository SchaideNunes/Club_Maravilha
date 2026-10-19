"""
Feature 5 - Autenticação do painel administrativo (login JWT, /auth/me e rate limit).

Contratos:
- Modelo `UsuarioAdmin` (app/models/usuario_admin.py, exportado em app.models): tabela
  `usuarios_admin`, campos id (UUID), nome, email (único, minúsculo), senha_hash (bcrypt), ativo
  (default True), created_at/updated_at.
- `app.core.security`: `hash_senha(senha) -> str` (bcrypt "$2..."), `verificar_senha(senha, hash) -> bool`,
  `criar_access_token(subject: str, expires_delta: timedelta | None = None) -> str` (JWT HS256 assinado
  com settings.SECRET_KEY/settings.ALGORITHM; claims `sub` = str(usuario.id) e `exp`; expiração padrão
  settings.ACCESS_TOKEN_EXPIRE_MINUTES).
- POST /api/v1/auth/login  JSON {"email", "senha"}
    200 {"access_token", "token_type": "bearer", "usuario": {"id", "nome", "email"}} (nunca expõe senha_hash);
    e-mail comparado sem diferenciar maiúsculas/espaços;
    401 {"detail": "Credenciais inválidas"} para e-mail inexistente, senha errada ou usuário inativo
    (mesma mensagem nos três casos, header WWW-Authenticate: Bearer); 422 sem campos obrigatórios.
- Rate limit em memória (app.core.rate_limit.login_rate_limiter): 5 falhas em 60 s para o mesmo
  IP + e-mail -> a 6ª tentativa (mesmo com a senha correta) recebe 429 {"detail"} com header Retry-After.
  Login bem-sucedido zera as falhas daquela chave; outro e-mail no mesmo IP não é afetado.
- GET /api/v1/auth/me  (Authorization: Bearer <token>) -> 200 {"id", "nome", "email"}; 401 sem token,
  token inválido, expirado, de usuário inexistente ou inativo.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.core.security import criar_access_token, hash_senha
from app.models.usuario_admin import UsuarioAdmin

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
SENHA = "SenhaForte!2026"
MENSAGEM_GENERICA = "Credenciais inválidas"


async def _criar_admin(db_session, email="diretoria@clubmaravilha.com.br", senha=SENHA, ativo=True, nome="Diretoria"):
    usuario = UsuarioAdmin(nome=nome, email=email, senha_hash=hash_senha(senha), ativo=ativo)
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)
    return usuario


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------------------
# Login
# ------------------------------------------------------------------------------
async def test_login_sucesso_retorna_token_bearer_e_usuario(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)

    res = await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": SENHA})

    assert res.status_code == 200, res.text
    corpo = res.json()
    assert corpo["token_type"] == "bearer"
    assert isinstance(corpo["access_token"], str) and corpo["access_token"]
    assert corpo["usuario"] == {"id": str(admin.id), "nome": "Diretoria", "email": admin.email}
    assert "senha" not in res.text and "senha_hash" not in res.text


async def test_login_token_e_jwt_hs256_com_sub_e_expiracao_configurada(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)
    antes = datetime.now(timezone.utc)

    res = await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": SENHA})
    token = res.json()["access_token"]

    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert claims["sub"] == str(admin.id)
    exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    esperado = antes + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assert abs((exp - esperado).total_seconds()) < 120


async def test_login_email_sem_diferenciar_maiusculas_e_espacos(async_client_sem_auth: AsyncClient, db_session):
    await _criar_admin(db_session, email="diretoria@clubmaravilha.com.br")

    res = await async_client_sem_auth.post(
        LOGIN, json={"email": "  Diretoria@ClubMaravilha.com.BR ", "senha": SENHA}
    )

    assert res.status_code == 200, res.text


@pytest.mark.parametrize(
    "email,senha,ativo",
    [
        ("diretoria@clubmaravilha.com.br", "senha-errada", True),
        ("ninguem@clubmaravilha.com.br", SENHA, True),
        ("diretoria@clubmaravilha.com.br", SENHA, False),
    ],
    ids=["senha_errada", "email_inexistente", "usuario_inativo"],
)
async def test_login_invalido_retorna_401_com_mensagem_generica(
    async_client_sem_auth: AsyncClient, db_session, email, senha, ativo
):
    await _criar_admin(db_session, ativo=ativo)

    res = await async_client_sem_auth.post(LOGIN, json={"email": email, "senha": senha})

    assert res.status_code == 401
    assert res.json() == {"detail": MENSAGEM_GENERICA}
    assert res.headers.get("www-authenticate", "").lower().startswith("bearer")
    assert "access_token" not in res.text


@pytest.mark.parametrize("payload", [{}, {"email": "a@b.com"}, {"senha": "x"}])
async def test_login_sem_campos_obrigatorios_retorna_422(async_client_sem_auth: AsyncClient, payload):
    res = await async_client_sem_auth.post(LOGIN, json=payload)
    assert res.status_code == 422


# ------------------------------------------------------------------------------
# Rate limit de login
# ------------------------------------------------------------------------------
async def test_login_bloqueia_apos_5_falhas_por_ip_e_email(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)

    for _ in range(5):
        falha = await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": "errada"})
        assert falha.status_code == 401

    bloqueado = await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": SENHA})

    assert bloqueado.status_code == 429
    assert "detail" in bloqueado.json()
    assert int(bloqueado.headers["retry-after"]) > 0


async def test_rate_limit_nao_afeta_outro_email_no_mesmo_ip(async_client_sem_auth: AsyncClient, db_session):
    await _criar_admin(db_session, email="um@clubmaravilha.com.br")
    outro = await _criar_admin(db_session, email="outro@clubmaravilha.com.br")

    for _ in range(5):
        await async_client_sem_auth.post(LOGIN, json={"email": "um@clubmaravilha.com.br", "senha": "errada"})

    res = await async_client_sem_auth.post(LOGIN, json={"email": outro.email, "senha": SENHA})
    assert res.status_code == 200


async def test_login_bem_sucedido_zera_as_falhas(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)

    for _ in range(4):
        await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": "errada"})
    ok = await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": SENHA})
    assert ok.status_code == 200

    for _ in range(4):
        falha = await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": "errada"})
        assert falha.status_code == 401


# ------------------------------------------------------------------------------
# /auth/me
# ------------------------------------------------------------------------------
async def test_me_com_token_do_login_retorna_usuario(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)
    login = await async_client_sem_auth.post(LOGIN, json={"email": admin.email, "senha": SENHA})

    res = await async_client_sem_auth.get(ME, headers=_bearer(login.json()["access_token"]))

    assert res.status_code == 200
    assert res.json() == {"id": str(admin.id), "nome": admin.nome, "email": admin.email}


async def test_me_sem_token_retorna_401(async_client_sem_auth: AsyncClient):
    res = await async_client_sem_auth.get(ME)
    assert res.status_code == 401
    assert res.headers.get("www-authenticate", "").lower().startswith("bearer")


async def test_me_com_esquema_diferente_de_bearer_retorna_401(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)
    token = criar_access_token(str(admin.id))
    res = await async_client_sem_auth.get(ME, headers={"Authorization": f"Basic {token}"})
    assert res.status_code == 401


async def test_me_com_token_expirado_retorna_401(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)
    token = criar_access_token(str(admin.id), expires_delta=timedelta(minutes=-5))

    res = await async_client_sem_auth.get(ME, headers=_bearer(token))

    assert res.status_code == 401


async def test_me_com_assinatura_invalida_retorna_401(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)
    forjado = jwt.encode(
        {"sub": str(admin.id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "outra-chave-qualquer",
        algorithm="HS256",
    )

    res = await async_client_sem_auth.get(ME, headers=_bearer(forjado))

    assert res.status_code == 401


@pytest.mark.parametrize("token", ["abc.def.ghi", "nao-e-jwt", ""])
async def test_me_com_token_malformado_retorna_401(async_client_sem_auth: AsyncClient, token):
    res = await async_client_sem_auth.get(ME, headers=_bearer(token))
    assert res.status_code == 401


async def test_me_token_com_alg_none_e_rejeitado(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)
    import base64
    import json

    def _b64(dados: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(dados).encode()).rstrip(b"=").decode()

    exp = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
    token = f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64({'sub': str(admin.id), 'exp': exp})}."

    res = await async_client_sem_auth.get(ME, headers=_bearer(token))

    assert res.status_code == 401


@pytest.mark.parametrize("sub", [str(uuid.uuid4()), "nao-e-uuid"])
async def test_me_token_de_usuario_inexistente_retorna_401(async_client_sem_auth: AsyncClient, sub):
    res = await async_client_sem_auth.get(ME, headers=_bearer(criar_access_token(sub)))
    assert res.status_code == 401


async def test_me_token_sem_sub_retorna_401(async_client_sem_auth: AsyncClient):
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(hours=1)}, settings.SECRET_KEY, algorithm="HS256"
    )
    res = await async_client_sem_auth.get(ME, headers=_bearer(token))
    assert res.status_code == 401


async def test_me_usuario_desativado_apos_emitir_token_retorna_401(async_client_sem_auth: AsyncClient, db_session):
    admin = await _criar_admin(db_session)
    token = criar_access_token(str(admin.id))
    admin.ativo = False
    await db_session.commit()

    res = await async_client_sem_auth.get(ME, headers=_bearer(token))

    assert res.status_code == 401
