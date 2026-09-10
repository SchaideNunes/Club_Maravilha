"""
Endpoint de Health Check para monitoramento e Docker Compose.
"""
from typing import Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """
    Verifica a saúde do serviço FastAPI e a conectividade com o banco PostgreSQL.
    """
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "service": "club-maravilha-backend",
        "version": "0.1.0"
    }
