"""
Gerenciamento de conexões assíncronas com o PostgreSQL via SQLAlchemy 2.0.
Fornece engine assíncrona, session maker e dependência get_db para injeção no FastAPI.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Engine assíncrona otimizada para conexões de alta concorrência
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Fábrica de sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependência FastAPI que fornece uma sessão assíncrona do banco de dados
    com rollback automático em caso de exceção e fechamento garantido.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
