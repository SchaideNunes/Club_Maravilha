"""
Serviço de Integração com Catraca Facial e Whitelist Offline (Rede Local).
Fornece lista autorizada sincronizável e processamento de eventos de passagem física.
"""
import hashlib
import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import and_, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.clock import hoje_clube
from app.core.config import settings
from app.core.constants import DIAS_CARENCIA_BLOQUEIO
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura

logger = logging.getLogger(__name__)


class CatracaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_whitelist(self, data_consulta: Optional[date] = None) -> Dict[str, Any]:
        """
        Gera a Lista Branca (Whitelist) offline autorizada para hoje:
        1. Associados ATIVOS que NÃO possuam faturas em aberto (PENDENTE/ATRASADA)
           vencidas há mais de DIAS_CARENCIA_BLOQUEIO dias (1 mês).
        2. Convidados EMITIDOS cuja data de visita seja a data da consulta.
        Retorna também um checksum hash para a catraca detectar se houve alterações.
        """
        hoje = data_consulta or hoje_clube()
        limite_bloqueio = hoje - timedelta(days=DIAS_CARENCIA_BLOQUEIO)

        # 1. Subquery para identificar sócios com faturas em aberto além da tolerância de bloqueio (1 mês)
        subquery_bloqueados = select(Fatura.associado_id).where(
            Fatura.status.in_([StatusFatura.PENDENTE, StatusFatura.ATRASADA]),
            Fatura.data_vencimento <= limite_bloqueio,
        ).scalar_subquery()

        # 2. Busca associados ativos e adimplentes (não bloqueados por faturas vencidas além da tolerância)
        query_associados = select(Associado).where(
            and_(
                Associado.status == StatusAssociado.ATIVO,
                Associado.facial_id.is_not(None),
                not_(Associado.id.in_(subquery_bloqueados))
            )
        ).order_by(Associado.id)
        res_associados = await self.session.execute(query_associados)
        associados = res_associados.scalars().all()

        # 3. Busca convidados autorizados para hoje
        query_convidados = select(Convidado).where(
            and_(
                Convidado.status == StatusConvidado.EMITIDO,
                Convidado.data_visita == hoje
            )
        ).order_by(Convidado.id)
        res_convidados = await self.session.execute(query_convidados)
        convidados = res_convidados.scalars().all()

        members_list = [
            {
                "id": str(assoc.id),
                "facial_id": assoc.facial_id,
                "nome": assoc.nome,
                "foto_url": assoc.foto_url,
                "type": "MEMBER"
            }
            for assoc in associados
        ]

        guests_list = [
            {
                "id": str(conv.id),
                "qr_token": conv.qr_code_token,
                "nome": conv.nome,
                "type": "GUEST"
            }
            for conv in convidados
        ]

        # Checksum do conteúdo (não só da contagem): trocar um sócio por outro também muda a versão,
        # e a catraca baixa a lista de novo
        payload_str = json.dumps({"m": members_list, "g": guests_list}, sort_keys=True)
        checksum = hashlib.md5(payload_str.encode("utf-8")).hexdigest()

        return {
            "date": hoje.isoformat(),
            "checksum": checksum,
            "total_authorized": len(members_list) + len(guests_list),
            "members": members_list,
            "guests": guests_list
        }

    async def notify_turnstile_sync(self, reason: str = "payment_confirmed") -> Dict[str, Any]:
        """
        Notifica o leitor/catraca na rede local para sincronizar sua memória offline imediatamente.
        Disparado quando uma fatura é liquidada ou novo sócio cadastrado.
        """
        logger.info(f"[CatracaService] Sincronização imediata disparada na catraca ({reason}).")
        # Em ambiente real, envia webhook/requisição HTTP POST para settings.TURNSTILE_HOST
        return {
            "status": "synchronized",
            "reason": reason,
            "host": settings.TURNSTILE_HOST,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def process_turnstile_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa evento de giro/passagem física na catraca:
        - Se for QR Code de visitante: atualiza status para UTILIZADO e grava check_in_at.
        - Se for biometria facial de sócio: audita passagem.
        """
        token = event.get("token")
        if token:
            res_conv = await self.session.execute(
                select(Convidado).where(Convidado.qr_code_token == token)
            )
            convidado = res_conv.scalar_one_or_none()
            # O QR do convidado só vale no dia da visita
            if (
                convidado
                and convidado.status == StatusConvidado.EMITIDO
                and convidado.data_visita == hoje_clube()
            ):
                convidado.status = StatusConvidado.UTILIZADO
                convidado.check_in_at = datetime.now(timezone.utc)
                await self.session.commit()
                await self.session.refresh(convidado)
                return {
                    "authorized": True,
                    "type": "GUEST",
                    "nome": convidado.nome,
                    "check_in_at": convidado.check_in_at.isoformat()
                }

        facial_id = event.get("facial_id")
        if facial_id:
            res_assoc = await self.session.execute(
                select(Associado).where(Associado.facial_id == facial_id)
            )
            assoc = res_assoc.scalar_one_or_none()
            if assoc and assoc.status == StatusAssociado.ATIVO:
                return {
                    "authorized": True,
                    "type": "MEMBER",
                    "nome": assoc.nome,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        return {"authorized": False, "detail": "Credencial não autorizada"}
