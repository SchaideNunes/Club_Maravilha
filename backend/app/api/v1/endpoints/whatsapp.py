"""
Endpoints da API para diagnóstico, conexão via QR Code, testes de envio e auditoria de mensagens do WhatsApp.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.phone import sanitize_whatsapp_number
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.services.whatsapp_service import (
    WhatsAppProvider,
    get_whatsapp_provider,
)

router = APIRouter()


def get_provider() -> WhatsAppProvider:
    """Dependência FastAPI para injetar o provedor configurado de WhatsApp."""
    return get_whatsapp_provider()


class WhatsAppTesteEnvioRequest(BaseModel):
    numero: str = Field(..., description="Número do destinatário com DDD")
    mensagem: Optional[str] = Field(None, max_length=4096, description="Texto opcional da mensagem de teste")


class LogMensagemResponse(BaseModel):
    id: uuid.UUID
    associado_id: Optional[uuid.UUID] = None
    associado_nome: Optional[str] = None
    fatura_id: Optional[uuid.UUID] = None
    destinatario: str
    etapa: str
    status: str
    mensagem: str
    erro: Optional[str] = None
    enviado_em: datetime


@router.get("/status", summary="Consulta status de conexão do WhatsApp")
async def get_status(provider: WhatsAppProvider = Depends(get_provider)) -> Dict[str, Any]:
    """Retorna o estado da conexão: CONECTADO, DESCONECTADO ou AGUARDANDO_QRCODE."""
    status_data = await provider.get_connection_status()
    return {"status": status_data.get("status", "DESCONECTADO")}


@router.get("/qrcode", summary="Obtém o QR Code para pareamento do WhatsApp")
async def get_qrcode(provider: WhatsAppProvider = Depends(get_provider)) -> Dict[str, Any]:
    """Retorna o status atual e o QR Code em data URL (ou null se conectado)."""
    qr_data = await provider.get_qr_code()
    return {
        "status": qr_data.get("status", "DESCONECTADO"),
        "qrcode": qr_data.get("qrcode"),
    }


@router.post("/desconectar", summary="Desconecta a sessão do WhatsApp")
async def desconectar(provider: WhatsAppProvider = Depends(get_provider)) -> Dict[str, Any]:
    """Encerra a sessão ativa do WhatsApp no motor Baileys."""
    res = await provider.logout()
    if res.get("error"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao desconectar: {res['error']}",
        )
    return {"status": res.get("status", "DESCONECTADO")}


@router.post("/reiniciar", summary="Reinicia a conexão do WhatsApp")
async def reiniciar(provider: WhatsAppProvider = Depends(get_provider)) -> Dict[str, Any]:
    """Reinicia a conexão do motor Baileys sem apagar as credenciais salvas."""
    res = await provider.restart()
    if res.get("error"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha ao reiniciar: {res['error']}",
        )
    return {"status": res.get("status", "AGUARDANDO_QRCODE")}


@router.post("/teste-envio", summary="Dispara uma mensagem de teste imediata")
async def teste_envio(
    payload: WhatsAppTesteEnvioRequest,
    provider: WhatsAppProvider = Depends(get_provider),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Envia uma mensagem de teste diretamente pelo provedor ativo (sem passar pela fila anti-ban)
    e grava a auditoria correspondente em LogMensagem.
    """
    try:
        destinatario = sanitize_whatsapp_number(payload.numero)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    texto = payload.mensagem.strip() if payload.mensagem and payload.mensagem.strip() else "Olá! Mensagem de teste do Club Maravilha."

    res = await provider.send_message(destinatario, texto)

    status_envio = StatusEnvio.SUCESSO if res.get("status") == "success" else StatusEnvio.ERRO
    erro = res.get("error") if status_envio == StatusEnvio.ERRO else None

    log = LogMensagem(
        associado_id=None,
        fatura_id=None,
        destinatario=destinatario,
        etapa=EtapaRegua.TESTE,
        mensagem=texto,
        status=status_envio,
        erro=erro,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)

    if status_envio == StatusEnvio.ERRO:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(erro or "Erro retornado pelo motor de WhatsApp"),
        )

    return {
        "status": "SUCESSO",
        "destinatario": destinatario,
        "mensagem": texto,
        "message_id": res.get("message_id") or "MSG-TESTE",
        "log_id": str(log.id),
    }


@router.get("/logs", response_model=List[LogMensagemResponse], summary="Lista logs de disparos de WhatsApp")
async def listar_logs(
    limit: int = Query(default=50, ge=1, le=500, description="Quantidade máxima de logs a retornar"),
    etapa: Optional[EtapaRegua] = Query(default=None, description="Filtro por etapa da régua"),
    status: Optional[StatusEnvio] = Query(default=None, description="Filtro por status de envio"),
    associado_id: Optional[uuid.UUID] = Query(default=None, description="Filtro por associado"),
    db: AsyncSession = Depends(get_db),
) -> List[LogMensagemResponse]:
    """Retorna os logs de mensagens de WhatsApp ordenados por data de envio decrescente."""
    stmt = select(LogMensagem).options(joinedload(LogMensagem.associado))

    if etapa is not None:
        stmt = stmt.where(LogMensagem.etapa == etapa)
    if status is not None:
        stmt = stmt.where(LogMensagem.status == status)
    if associado_id is not None:
        stmt = stmt.where(LogMensagem.associado_id == associado_id)

    stmt = stmt.order_by(LogMensagem.enviado_em.desc()).limit(limit)

    result = await db.execute(stmt)
    registros = result.scalars().all()

    return [
        LogMensagemResponse(
            id=item.id,
            associado_id=item.associado_id,
            associado_nome=item.associado.nome if item.associado else None,
            fatura_id=item.fatura_id,
            destinatario=item.destinatario,
            etapa=item.etapa.value if hasattr(item.etapa, "value") else str(item.etapa),
            status=item.status.value if hasattr(item.status, "value") else str(item.status),
            mensagem=item.mensagem,
            erro=item.erro,
            enviado_em=item.enviado_em,
        )
        for item in registros
    ]
