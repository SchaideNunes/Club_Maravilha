"""
Motor automatizado da Régua Diária de Cobrança (D-3, D-0, D+3, D+7).
Orquestra seleções temporais, atualizações de status financeiro e enfileiramento seguro no WhatsApp.
"""
import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.schemas.fatura import BillingExecutionReport
from app.services.whatsapp_queue_service import (
    MessagePriority,
    WhatsAppQueueService,
    get_global_whatsapp_queue,
)
from app.services.whatsapp_service import WhatsAppMessageBuilder

logger = logging.getLogger(__name__)


class BillingEngineService:
    def __init__(
        self,
        session: AsyncSession,
        queue_service: Optional[WhatsAppQueueService] = None,
    ) -> None:
        self.session = session
        self.fatura_repo = FaturaRepository(session)
        self.associado_repo = AssociadoRepository(session)
        self.queue_service = queue_service or get_global_whatsapp_queue()

    async def processar_regua_diaria(
        self,
        data_referencia: Optional[date] = None
    ) -> BillingExecutionReport:
        """
        Executa todas as 4 etapas da régua diária de cobrança para a data de referência.
        Totalmente idempotente: faturas já notificadas para o estágio são ignoradas.
        """
        hoje = data_referencia or date.today()
        agora = datetime.now(timezone.utc)

        report = BillingExecutionReport(
            data_referencia=hoje,
            d_minus_3_enviados=0,
            d_zero_enviados=0,
            d_plus_3_enviados=0,
            d_plus_7_enviados=0,
            inadimplentes_atualizados=0,
            total_enfileirados=0,
            erros=[]
        )

        try:
            # 1. D-3: Aviso Preventivo Amigável (Vencimento em hoje + 3 dias)
            data_d3 = hoje + timedelta(days=3)
            faturas_d3 = await self.fatura_repo.get_faturas_para_regua(
                data_vencimento=data_d3,
                campo_notificacao="notificado_d_minus_3_em"
            )
            for fatura in faturas_d3:
                if fatura.associado and fatura.associado.whatsapp:
                    msg = WhatsAppMessageBuilder.build_d_minus_3(
                        nome=fatura.associado.nome,
                        valor=fatura.valor_total,
                        data_vencimento=fatura.data_vencimento
                    )
                    await self.queue_service.enqueue(
                        phone=fatura.associado.whatsapp,
                        message=msg,
                        priority=MessagePriority.NORMAL
                    )
                    fatura.notificado_d_minus_3_em = agora
                    report.d_minus_3_enviados += 1
                    report.total_enfileirados += 1

            # 2. D-0: Disparo Matinal com Pix Copia e Cola (Vencimento Hoje)
            faturas_d0 = await self.fatura_repo.get_faturas_para_regua(
                data_vencimento=hoje,
                campo_notificacao="notificado_d_zero_em"
            )
            for fatura in faturas_d0:
                if fatura.associado and fatura.associado.whatsapp:
                    pix = fatura.pix_copia_cola or "Chave Pix indisponível no momento."
                    msg = WhatsAppMessageBuilder.build_d_zero(
                        nome=fatura.associado.nome,
                        valor=fatura.valor_total,
                        data_vencimento=fatura.data_vencimento,
                        pix_copia_cola=pix
                    )
                    await self.queue_service.enqueue(
                        phone=fatura.associado.whatsapp,
                        message=msg,
                        priority=MessagePriority.NORMAL
                    )
                    fatura.notificado_d_zero_em = agora
                    report.d_zero_enviados += 1
                    report.total_enfileirados += 1

            # 3. D+3: Inadimplência Leve com Reenvio do Pix (Vencimento há 3 dias)
            data_dp3 = hoje - timedelta(days=3)
            faturas_dp3 = await self.fatura_repo.get_faturas_para_regua(
                data_vencimento=data_dp3,
                campo_notificacao="notificado_d_plus_3_em"
            )
            for fatura in faturas_dp3:
                if fatura.associado and fatura.associado.whatsapp:
                    pix = fatura.pix_copia_cola or ""
                    msg = WhatsAppMessageBuilder.build_d_plus_3(
                        nome=fatura.associado.nome,
                        valor=fatura.valor_total,
                        data_vencimento=fatura.data_vencimento,
                        pix_copia_cola=pix
                    )
                    await self.queue_service.enqueue(
                        phone=fatura.associado.whatsapp,
                        message=msg,
                        priority=MessagePriority.NORMAL
                    )
                    fatura.notificado_d_plus_3_em = agora
                    report.d_plus_3_enviados += 1
                    report.total_enfileirados += 1

            # 4. D+7: Inadimplência Crítica & Bloqueio Físico na Catraca (Vencimento há 7 dias)
            data_dp7 = hoje - timedelta(days=7)
            faturas_dp7 = await self.fatura_repo.get_faturas_para_regua(
                data_vencimento=data_dp7,
                campo_notificacao="notificado_d_plus_7_em"
            )
            for fatura in faturas_dp7:
                if fatura.associado and fatura.associado.whatsapp:
                    pix = fatura.pix_copia_cola or ""
                    msg = WhatsAppMessageBuilder.build_d_plus_7(
                        nome=fatura.associado.nome,
                        valor=fatura.valor_total,
                        data_vencimento=fatura.data_vencimento,
                        pix_copia_cola=pix
                    )
                    await self.queue_service.enqueue(
                        phone=fatura.associado.whatsapp,
                        message=msg,
                        priority=MessagePriority.NORMAL
                    )
                    fatura.notificado_d_plus_7_em = agora
                    fatura.status = StatusFatura.VENCIDO

                    # Atualiza o sócio para INADIMPLENTE se ainda estiver ATIVO
                    if fatura.associado.status != StatusAssociado.INADIMPLENTE:
                        fatura.associado.status = StatusAssociado.INADIMPLENTE
                        report.inadimplentes_atualizados += 1

                    report.d_plus_7_enviados += 1
                    report.total_enfileirados += 1

            # Persiste todas as alterações de forma atômica
            await self.session.commit()
            logger.info(
                f"[BillingEngine] Régua executada para {hoje}: "
                f"Total enfileirado={report.total_enfileirados}, "
                f"Novos Inadimplentes={report.inadimplentes_atualizados}."
            )

        except Exception as exc:
            await self.session.rollback()
            logger.error(f"[BillingEngine] Erro durante a execução da régua: {exc}", exc_info=True)
            report.erros.append(str(exc))

        return report
