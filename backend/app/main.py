"""
Club Maravilha - Sistema de Gestão Integrada
Ponto de entrada principal da API FastAPI.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import async_engine
from app.models.base import Base


from app.jobs.billing_scheduler import start_scheduler_and_worker, stop_scheduler_and_worker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Gerenciador de ciclo de vida da aplicação.
    No MVP, cria automaticamente as tabelas caso não existam (facilita setup de dev).
    Inicia o APScheduler e o consumidor anti-ban da fila de WhatsApp.
    """
    async with async_engine.begin() as conn:
        if async_engine.dialect.name == "postgresql":
            from sqlalchemy import text
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS evolution;"))
        # Criação inicial de tabelas para dev/MVP
        await conn.run_sync(Base.metadata.create_all)
    
    # Inicia scheduler e worker em segundo plano (exceto em modo de teste automatizado isolado)
    if settings.ENVIRONMENT != "test":
        start_scheduler_and_worker()

    yield
    
    # Finalização de recursos na desconexão
    if settings.ENVIRONMENT != "test":
        await stop_scheduler_and_worker()
        
    await async_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API do Sistema Integrado de Gestão do Club Maravilha (~300 associados).\n\n"
        "Módulos integrados: Associados, Mensalidades Pix, Quadras, Convidados, "
        "Catraca Facial e Automação de WhatsApp."
    ),
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configuração de CORS para permitir requisições do frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Rotas
app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Redireciona a raiz para a documentação interativa Swagger."""
    return RedirectResponse(url="/docs")
