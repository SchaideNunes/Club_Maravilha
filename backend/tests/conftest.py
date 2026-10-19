"""
Configuração do ambiente de testes assíncronos com pytest e SQLite em memória.
"""
import os

# O padrão de produção do WHATSAPP_PROVIDER é BAILEYS (motor real). A suíte de testes nunca fala com
# o engine: força o provedor MOCK antes de qualquer import de `app` instanciar o `settings`.
os.environ["WHATSAPP_PROVIDER"] = "MOCK"

import pytest
from typing import AsyncGenerator
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.database import get_db
from app.main import app
from app.models.base import Base

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


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Cliente HTTP assíncrono para testar endpoints FastAPI injetando o banco de teste.
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
