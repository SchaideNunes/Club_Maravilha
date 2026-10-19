"""
Configuração do ambiente de testes assíncronos com pytest e SQLite em memória.

Autenticação do painel admin (Feature 5)
----------------------------------------
Todas as rotas administrativas exigem `Depends(get_current_admin)` (app/api/deps.py). Para não
reescrever as centenas de testes de API existentes, a fixture `async_client` já injeta um
override de `get_current_admin` que devolve um administrador fictício (`ADMIN_FICTICIO`): os
testes antigos continuam chamando as rotas "como um admin logado".

- `async_client`          -> cliente autenticado (override de get_current_admin ativo).
- `async_client_sem_auth` -> cliente SEM o override: a autenticação real (Bearer JWT) é exercida.
                             Use-o nos testes de 401/login/me. Não combine as duas fixtures no
                             mesmo teste (ambas compartilham `app.dependency_overrides`).

Enquanto `app.api.deps.get_current_admin` não existir (fase RED da Feature 5) o override é
simplesmente ignorado, para que a suíte antiga continue verde.

O limitador de tentativas de login (`app.core.rate_limit.login_rate_limiter`) é global e em
memória; a fixture autouse `_resetar_rate_limit_login` o zera antes de cada teste.
"""
import os

# O padrão de produção do WHATSAPP_PROVIDER é BAILEYS (motor real). A suíte de testes nunca fala com
# o engine: força o provedor MOCK antes de qualquer import de `app` instanciar o `settings`.
os.environ["WHATSAPP_PROVIDER"] = "MOCK"

import uuid
from types import SimpleNamespace

import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.database import get_db
from app.main import app
from app.models.base import Base

try:  # Feature 5: dependência de autenticação do painel admin
    from app.api.deps import get_current_admin
except ImportError:  # pragma: no cover - fase RED, a dependência ainda não existe
    get_current_admin = None

try:  # Feature 5: limitador em memória das tentativas de login
    from app.core.rate_limit import login_rate_limiter
except ImportError:  # pragma: no cover - fase RED
    login_rate_limiter = None

# Administrador fictício devolvido pelo override de get_current_admin no `async_client`
ADMIN_FICTICIO = SimpleNamespace(
    id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
    nome="Admin de Teste",
    email="admin.teste@clubmaravilha.com.br",
    ativo=True,
)

# Engine SQLite assíncrona isolada em memória para execução ultrarrápida dos testes
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)


@event.listens_for(test_engine.sync_engine, "connect")
def _ativar_foreign_keys_no_sqlite(dbapi_connection, _connection_record) -> None:
    """O SQLite ignora FOREIGN KEY por padrão; ligar faz os testes refletirem o PostgreSQL (FK, SET NULL, CASCADE)."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()




TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def init_test_db() -> AsyncGenerator[None, None]:
    """Cria todas as tabelas em memória antes do teste e remove ao final."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Fornece uma sessão transacional limpa para cada teste."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def _resetar_rate_limit_login():
    """Zera o limitador global de tentativas de login (estado em memória) entre os testes."""
    if login_rate_limiter is not None:
        login_rate_limiter.reset()
    yield
    if login_rate_limiter is not None:
        login_rate_limiter.reset()


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def _override_get_current_admin() -> SimpleNamespace:
    return ADMIN_FICTICIO


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP assíncrono AUTENTICADO: injeta o banco de teste e um admin fictício
    (override de get_current_admin), para exercitar as rotas administrativas.
    """
    app.dependency_overrides[get_db] = _override_get_db
    if get_current_admin is not None:
        app.dependency_overrides[get_current_admin] = _override_get_current_admin

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client_sem_auth(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP assíncrono SEM override de autenticação: as rotas admin exigem um Bearer JWT
    válido de um UsuarioAdmin ativo. Usado nos testes de login, /auth/me e respostas 401.
    """
    app.dependency_overrides[get_db] = _override_get_db
    if get_current_admin is not None:
        app.dependency_overrides.pop(get_current_admin, None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
