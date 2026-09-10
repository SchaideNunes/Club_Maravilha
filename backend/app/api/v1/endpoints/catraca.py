"""
Endpoints da API v1 para Integração com a Catraca Facial (Rede Local).
Fornece sincronização de Lista Branca (Offline Whitelist) para operação autônoma da catraca.
"""
from datetime import date
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado

router = APIRouter()


@router.get("/whitelist", status_code=status.HTTP_200_OK)
async def get_turnstile_whitelist(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retorna a lista de pessoas autorizadas para acesso hoje:
    1. Associados com status ATIVO que possuem facial_id cadastrado.
    2. Convidados com status EMITIDO cuja data_visita seja hoje (com qr_code_token).
    A catraca faz download periódico deste payload em memória local.
    """
    hoje = date.today()

    # Associados Ativos
    res_associados = await db.execute(
        select(Associado).where(
            Associado.status == StatusAssociado.ATIVO,
            Associado.facial_id.is_not(None)
        )
    )
    associados = res_associados.scalars().all()

    # Convidados do Dia
    res_convidados = await db.execute(
        select(Convidado).where(
            Convidado.status == StatusConvidado.EMITIDO,
            Convidado.data_visita == hoje
        )
    )
    convidados = res_convidados.scalars().all()

    return {
        "date": hoje.isoformat(),
        "total_authorized": len(associados) + len(convidados),
        "members": [
            {
                "id": str(assoc.id),
                "facial_id": assoc.facial_id,
                "nome": assoc.nome,
                "type": "MEMBER"
            }
            for assoc in associados
        ],
        "guests": [
            {
                "id": str(conv.id),
                "qr_token": conv.qr_code_token,
                "nome": conv.nome,
                "type": "GUEST"
            }
            for conv in convidados
        ]
    }


@router.post("/events", status_code=status.HTTP_200_OK)
async def receive_turnstile_event(
    event: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Recebe evento de passagem física na catraca para auditoria ou baixa de convite.
    TODO(FASE-2-CATRACA): Atualizar status do Convidado para UTILIZADO e salvar log de catraca.
    """
    return {"status": "received"}
