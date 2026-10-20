"""
Endpoints do Dashboard Operacional do Painel Admin.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin
from app.api.v1.endpoints.whatsapp import get_provider
from app.core import clock
from app.core.database import get_db
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.models.log_mensagem import LogMensagem, StatusEnvio
from app.models.usuario_admin import UsuarioAdmin
from app.services.whatsapp_service import WhatsAppProvider

router = APIRouter(dependencies=[Depends(get_current_admin)])


class ResumoDashboardResponse(BaseModel):
    total_associados: int
    faturas_pagas_mes: int
    faturas_pendentes_mes: int
    faturas_atrasadas: int
    disparos_hoje: int
    disparos_erro_hoje: int
    whatsapp_status: str


class AtividadeItemResponse(BaseModel):
    tipo: str
    data: datetime
    descricao: str
    associado_nome: Optional[str] = None
    status: Optional[str] = None


STATUS_WHATSAPP_VALIDOS = {"CONECTADO", "DESCONECTADO", "AGUARDANDO_QRCODE"}


@router.get("/resumo", response_model=ResumoDashboardResponse)
async def obter_resumo(
    db: AsyncSession = Depends(get_db),
    provider: WhatsAppProvider = Depends(get_provider),
) -> Dict[str, Any]:
    """
    Retorna métricas agregadas operacionais para o dashboard.
    """
    # 1. Total de associados (sem os inativos, desligados do clube)
    total_associados = (
        await db.execute(
            select(func.count()).select_from(Associado).where(Associado.status != StatusAssociado.INATIVO)
        )
    ).scalar_one()

    # 2. Mês de referência corrente no fuso do clube
    agora_clube = clock.agora_clube()
    mes_corrente = agora_clube.strftime("%Y-%m")

    # 3. Faturas do mês e atrasadas
    faturas_pagas_mes = (
        await db.execute(
            select(func.count())
            .select_from(Fatura)
            .where(
                Fatura.referencia_mes == mes_corrente,
                Fatura.status == StatusFatura.PAGO,
            )
        )
    ).scalar_one()

    faturas_pendentes_mes = (
        await db.execute(
            select(func.count())
            .select_from(Fatura)
            .where(
                Fatura.referencia_mes == mes_corrente,
                Fatura.status == StatusFatura.PENDENTE,
            )
        )
    ).scalar_one()

    faturas_atrasadas = (
        await db.execute(
            select(func.count())
            .select_from(Fatura)
            .where(Fatura.status == StatusFatura.ATRASADA)
        )
    ).scalar_one()

    # 4. Disparos hoje no fuso do clube (00:00 às 24:00 locais)
    tz_clube = clock.get_clube_tz()
    inicio_dia_local = datetime(
        agora_clube.year, agora_clube.month, agora_clube.day, 0, 0, 0, tzinfo=tz_clube
    )
    fim_dia_local = inicio_dia_local + timedelta(days=1)
    inicio_dia_utc = inicio_dia_local.astimezone(timezone.utc)
    fim_dia_utc = fim_dia_local.astimezone(timezone.utc)

    # Consulta agregada via SQL delimitada pelo início e fim do dia corrente em UTC
    query_disparos = (
        select(
            func.count(),
            func.count().filter(LogMensagem.status == StatusEnvio.ERRO),
        ).where(
            LogMensagem.enviado_em >= inicio_dia_utc,
            LogMensagem.enviado_em < fim_dia_utc,
        )
    )
    resultado_disparos = await db.execute(query_disparos)
    total_disparos, total_erros = resultado_disparos.one()
    disparos_hoje = total_disparos or 0
    disparos_erro_hoje = total_erros or 0

    # 5. Status da conexão WhatsApp com proteção contra travamento (timeout 3.0s)
    whatsapp_status = "DESCONECTADO"
    try:
        status_info = await asyncio.wait_for(provider.get_connection_status(), timeout=3.0)
        raw_status = status_info.get("status") if isinstance(status_info, dict) else None
        if raw_status in STATUS_WHATSAPP_VALIDOS:
            whatsapp_status = raw_status
    except Exception:
        whatsapp_status = "DESCONECTADO"

    return {
        "total_associados": total_associados,
        "faturas_pagas_mes": faturas_pagas_mes,
        "faturas_pendentes_mes": faturas_pendentes_mes,
        "faturas_atrasadas": faturas_atrasadas,
        "disparos_hoje": disparos_hoje,
        "disparos_erro_hoje": disparos_erro_hoje,
        "whatsapp_status": whatsapp_status,
    }


@router.get("/atividades", response_model=List[AtividadeItemResponse])
async def listar_atividades(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Retorna lista unificada e decrescente dos últimos disparos e baixas manuais/PIX.
    """
    # 1. Buscar disparos recentes com associado
    query_logs = (
        select(LogMensagem)
        .options(selectinload(LogMensagem.associado))
        .order_by(LogMensagem.enviado_em.desc())
        .limit(limit)
    )
    logs_res = await db.execute(query_logs)
    logs = logs_res.scalars().all()

    # 2. Buscar faturas PAGO com data_pagamento recente com associado
    query_faturas = (
        select(Fatura)
        .options(selectinload(Fatura.associado))
        .where(
            Fatura.status == StatusFatura.PAGO,
            Fatura.data_pagamento.is_not(None),
        )
        .order_by(Fatura.data_pagamento.desc())
        .limit(limit)
    )
    faturas_res = await db.execute(query_faturas)
    faturas = faturas_res.scalars().all()

    itens: List[Dict[str, Any]] = []

    for log in logs:
        status_str = (
            log.status.value if hasattr(log.status, "value") else str(log.status)
        )
        itens.append(
            {
                "tipo": "DISPARO",
                "data": log.enviado_em,
                "descricao": log.mensagem or "Disparo de mensagem",
                "associado_nome": log.associado.nome if log.associado else None,
                "status": status_str,
            }
        )

    for fatura in faturas:
        status_str = (
            fatura.status.value
            if hasattr(fatura.status, "value")
            else str(fatura.status)
        )
        forma = (
            fatura.forma_pagamento.value
            if hasattr(fatura.forma_pagamento, "value")
            else str(fatura.forma_pagamento or "")
        )
        itens.append(
            {
                "tipo": "BAIXA",
                "data": fatura.data_pagamento,
                "descricao": f"Mensalidade {fatura.referencia_mes} quitada via {forma}",
                "associado_nome": fatura.associado.nome if fatura.associado else None,
                "status": status_str,
            }
        )

    # Ordenar por data decrescente
    def _chave_data(item: Dict[str, Any]) -> datetime:
        d = item["data"]
        if d.tzinfo is None:
            return d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)

    itens.sort(key=_chave_data, reverse=True)

    return itens[:limit]
