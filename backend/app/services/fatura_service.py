"""
Serviço de Negócio para Faturas, Cobrança Pix e Liquidação Instantânea via Webhook (< 2s).
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.associado import StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.schemas.fatura import FaturaCreate
from app.services.pix_gateway_service import MockPixGateway
from app.services.whatsapp_service import WhatsAppMessageBuilder
from app.services.whatsapp_queue_service import MessagePriority, get_global_whatsapp_queue


class FaturaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.fatura_repo = FaturaRepository(session)
        self.associado_repo = AssociadoRepository(session)
        self.pix_gateway = MockPixGateway(secret_key=settings.PIX_WEBHOOK_SECRET)

    async def get_by_id(self, fatura_id: uuid.UUID) -> Fatura:
        fatura = await self.fatura_repo.get_by_id(fatura_id)
        if not fatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fatura não encontrada."
            )
        return fatura

    async def list_faturas(
        self,
        associado_id: Optional[uuid.UUID] = None,
        status_filter: Optional[StatusFatura] = None,
        referencia_mes: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Fatura]:
        return await self.fatura_repo.list_faturas(
            associado_id=associado_id,
            status=status_filter,
            referencia_mes=referencia_mes,
            skip=skip,
            limit=limit
        )

    async def create_fatura(self, data: FaturaCreate) -> Fatura:
        """Cria uma nova fatura com chave Pix dinâmica, txid exclusivo e QR Code."""
        associado = await self.associado_repo.get_by_id(data.associado_id)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado para emissão de fatura."
            )

        # Gera Pix Dinâmico no Gateway
        pix_charge = self.pix_gateway.create_dynamic_pix_charge(
            fatura_id=str(uuid.uuid4()),
            valor=data.valor_total,
            referencia_mes=data.referencia_mes,
            nome_associado=associado.nome,
            cpf_associado=associado.cpf
        )

        fatura = Fatura(
            associado_id=data.associado_id,
            referencia_mes=data.referencia_mes,
            valor_base=data.valor_base,
            valor_convidados_excedentes=data.valor_convidados_excedentes,
            valor_desconto=data.valor_desconto,
            valor_total=data.valor_total,
            data_vencimento=data.data_vencimento,
            forma_pagamento=data.forma_pagamento,
            status=StatusFatura.PENDENTE,
            txid=pix_charge.txid,
            pix_copia_cola=pix_charge.pix_copia_cola,
            pix_qr_code_url=pix_charge.pix_qr_code_url,
        )

        created = await self.fatura_repo.create(fatura)
        await self.session.commit()
        await self.session.refresh(created)
        return created

    async def cancel_fatura(self, fatura_id: uuid.UUID) -> Fatura:
        """Cancela uma fatura pendente."""
        fatura = await self.get_by_id(fatura_id)
        if fatura.status == StatusFatura.PAGO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível cancelar uma fatura que já foi paga."
            )
        fatura.status = StatusFatura.CANCELADO
        await self.session.commit()
        await self.session.refresh(fatura)
        return fatura

    async def process_pix_webhook(
        self,
        payload: Dict[str, Any],
        secret_token: Optional[str]
    ) -> Dict[str, Any]:
        """
        Processa notificação de pagamento Pix em menos de 2 segundos.
        Garante verificação de segurança, idempotência e reativação automática de sócios.
        """
        # 1. Validação de Segurança do Token do Webhook
        if not self.pix_gateway.verify_webhook_token(secret_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assinatura do webhook inválida ou ausente."
            )

        # 2. Extração do txid (compatível com payload raiz ou lista pix)
        txid = payload.get("txid")
        if not txid and "pix" in payload and isinstance(payload["pix"], list) and payload["pix"]:
            txid = payload["pix"][0].get("txid")

        if not txid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payload de webhook inválido: txid não localizado."
            )

        # 3. Localização da fatura
        fatura = await self.fatura_repo.get_by_txid(txid)
        if not fatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fatura com txid '{txid}' não encontrada."
            )

        # 4. Idempotência: se já foi paga, retorna sucesso sem duplicar baixa
        if fatura.status == StatusFatura.PAGO:
            return {
                "status": "success",
                "message": "Fatura já liquidada anteriormente (idempotência garantida).",
                "txid": txid
            }

        # 5. Baixa Instantânea
        fatura.status = StatusFatura.PAGO
        fatura.data_pagamento = datetime.now(timezone.utc)
        fatura.metadata_webhook = payload

        # 6. Reativação automática do associado caso estivesse inadimplente
        associado = await self.associado_repo.get_by_id(fatura.associado_id)
        if associado and associado.status == StatusAssociado.INADIMPLENTE:
            associado.status = StatusAssociado.ATIVO

        # 7. Disparo imediato de Recibo Digital e Confirmação de Catraca Liberada via WhatsApp
        if associado and associado.whatsapp:
            msg_recibo = WhatsAppMessageBuilder.build_pos_pagamento(
                nome=associado.nome,
                valor=fatura.valor_total,
                referencia_mes=fatura.referencia_mes
            )
            fatura.notificado_pos_pagamento_em = datetime.now(timezone.utc)
            await get_global_whatsapp_queue().enqueue(
                phone=associado.whatsapp,
                message=msg_recibo,
                priority=MessagePriority.HIGH
            )

        await self.session.commit()

        # TODO(FASE-6-CATRACA): Sincronizar liberação imediata na catraca física

        return {
            "status": "success",
            "message": "Fatura liquidada e associado liberado com sucesso.",
            "txid": txid
        }
