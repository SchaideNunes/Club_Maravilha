"""
Módulo centralizador de relógio e datas no fuso horário oficial do clube (settings.TIMEZONE).
Garante que containers rodando com fuso horário UTC operem consistentemente no horário local.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from app.core.config import settings


def get_clube_tz() -> ZoneInfo:
    """Retorna o ZoneInfo configurado para o fuso horário do clube."""
    return ZoneInfo(settings.TIMEZONE)


def agora_clube() -> datetime:
    """Retorna a data e hora atual no fuso horário do clube."""
    return datetime.now(get_clube_tz())


def hoje_clube() -> date:
    """Retorna a data corrente (dia/mês/ano) no fuso horário do clube."""
    return agora_clube().date()
