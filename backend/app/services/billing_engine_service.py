"""
Motor automatizado da Régua Diária de Cobrança (D-3, D-0, D+3, D+7) e disparo avulso.
Orquestra seleções temporais, templates editáveis, auditoria de idempotência e enfileiramento seguro.
"""
from datetime import date, timedelta
import logging
from typing import Any, Dict, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import hoje_clube
from app.core.constants import DIAS_AVISO_CARENCIA, DIAS_CARENCIA_BLOQUEIO
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.schemas.fatura import BillingExecutionReport
from app.services.template_service import renderizar_template, variaveis_da_fatura
from app.services.whatsapp_queue_service import (
    LogContext,
    MessagePriority,
    WhatsAppQueueService,
    get_global_whatsapp_queue,
)

logger = logging.getLogger(__name__)


class BillingEngineService:
    def __init__(
        self,
        session: AsyncSession,
        queue_service: Optional[WhatsAppQueueService] = None,
    ) -> None:
        self.session = session
        self.queue_service = queue_service or get_global_whatsapp_queue()

    async def processar_regua_diaria(
        self,
        data_referencia: Optional[date] = None,
    ) -> BillingExecutionReport:
        """
        Executa as 4 etapas da régua diária de cobrança (D-3, D-0, D+3, D+7) para a data de referência.
        Totalmente idempotente: faturas já notificadas com sucesso para a etapa são ignoradas.
        Sem N+1: consultas de faturas e de auditoria de mensagens são agregadas.
        """
        hoje = data_referencia or hoje_clube()

        cfg_repo = ConfiguracaoRepository(self.session)
        configuracao = await cfg_repo.get_or_create()

        if not configuracao.automacao_ativa:
            # Sem mensagens, mas a inadimplência (e o bloqueio na catraca) não depende do WhatsApp
            report = BillingExecutionReport(
                data_referencia=hoje,
                automacao_ativa=False,
                d_minus_3_enviados=0,
                d_zero_enviados=0,
                d_plus_3_enviados=0,
                d_plus_7_enviados=0,
                inadimplentes_atualizados=0,
                total_enfileirados=0,
                ja_enviados=0,
                ignorados_sem_whatsapp=0,
                erros=[],
            )
            try:
                await self._marcar_inadimplentes(hoje, report)
                await self.session.commit()
            except Exception as exc:
                await self.session.rollback()
                logger.error(f"[BillingEngine] Erro ao marcar inadimplentes: {exc}", exc_info=True)
                report.erros.append(str(exc))
            logger.info(
                "[BillingEngine] Automação desativada: nenhuma mensagem enviada; "
                f"novos inadimplentes={report.inadimplentes_atualizados}."
            )
            return report

        report = BillingExecutionReport(
            data_referencia=hoje,
            automacao_ativa=True,
            d_minus_3_enviados=0,
            d_zero_enviados=0,
            d_plus_3_enviados=0,
            d_plus_7_enviados=0,
            inadimplentes_atualizados=0,
            total_enfileirados=0,
            ja_enviados=0,
            ignorados_sem_whatsapp=0,
            erros=[],
        )

        dias_etapas = [
            (EtapaRegua.D_MENOS_3, hoje + timedelta(days=3), configuracao.template_d_menos_3),
            (EtapaRegua.D0, hoje, configuracao.template_d0),
            (EtapaRegua.D_MAIS_3, hoje - timedelta(days=3), configuracao.template_d_mais_3),
            (EtapaRegua.D_MAIS_7, hoje - timedelta(days=DIAS_AVISO_CARENCIA), configuracao.template_d_mais_7),
        ]
        datas_alvo = {dt for _, dt, _ in dias_etapas}

        try:
            stmt = (
                select(Fatura)
                .options(joinedload(Fatura.associado))
                .join(Fatura.associado)
                .where(
                    Fatura.status.in_([StatusFatura.PENDENTE, StatusFatura.ATRASADA]),
                    Fatura.data_vencimento.in_(datas_alvo),
                    # Sócios inativos saem da régua automática; dívidas antigas ficam para cobrança manual
                    Associado.status != StatusAssociado.INATIVO,
                )
            )
            result = await self.session.execute(stmt)
            faturas = result.scalars().all()

            fatura_ids = [f.id for f in faturas]
            sucessos_existentes = set()
            if fatura_ids:
                stmt_logs = (
                    select(LogMensagem.fatura_id, LogMensagem.etapa)
                    .where(
                        LogMensagem.fatura_id.in_(fatura_ids),
                        LogMensagem.status == StatusEnvio.SUCESSO,
                    )
                )
                res_logs = await self.session.execute(stmt_logs)
                sucessos_existentes = set(res_logs.all())

            etapa_por_data = {dt: (etp, tmpl) for etp, dt, tmpl in dias_etapas}

            for fatura in faturas:
                info = etapa_por_data.get(fatura.data_vencimento)
                if not info:
                    continue
                etapa, template = info

                # Idempotência por LogMensagem SUCESSO
                if (fatura.id, etapa) in sucessos_existentes:
                    report.ja_enviados += 1
                    continue

                # D+7: fatura passa a ATRASADA (mesmo se sem WhatsApp); inadimplência só aos 30 dias
                if etapa == EtapaRegua.D_MAIS_7:
                    fatura.status = StatusFatura.ATRASADA

                # Verificação de telefone válido
                if not fatura.associado or not fatura.associado.whatsapp or not fatura.associado.whatsapp.strip():
                    report.ignorados_sem_whatsapp += 1
                    continue

                vars_fat = variaveis_da_fatura(fatura, fatura.associado, configuracao)
                msg = renderizar_template(template, vars_fat)

                enfileirado = await self.queue_service.enqueue(
                    phone=fatura.associado.whatsapp,
                    message=msg,
                    priority=MessagePriority.NORMAL,
                    log_context=LogContext(
                        etapa=etapa,
                        associado_id=fatura.associado.id,
                        fatura_id=fatura.id,
                    ),
                )

                if enfileirado is False:
                    report.ja_pendentes += 1
                else:
                    if etapa == EtapaRegua.D_MENOS_3:
                        report.d_minus_3_enviados += 1
                    elif etapa == EtapaRegua.D0:
                        report.d_zero_enviados += 1
                    elif etapa == EtapaRegua.D_MAIS_3:
                        report.d_plus_3_enviados += 1
                    elif etapa == EtapaRegua.D_MAIS_7:
                        report.d_plus_7_enviados += 1

                    report.total_enfileirados += 1

            await self._marcar_inadimplentes(hoje, report)

            await self.session.commit()
            logger.info(
                f"[BillingEngine] Régua executada para {hoje}: "
                f"Total enfileirado={report.total_enfileirados}, "
                f"Novos Inadimplentes={report.inadimplentes_atualizados}, "
                f"Já enviados={report.ja_enviados}, "
                f"Sem WhatsApp={report.ignorados_sem_whatsapp}."
            )

        except Exception as exc:
            await self.session.rollback()
            logger.error(f"[BillingEngine] Erro durante a execução da régua: {exc}", exc_info=True)
            report.erros.append(str(exc))

        return report

    async def _marcar_inadimplentes(self, hoje: date, report: BillingExecutionReport) -> None:
        """
        Associados ATIVOS com fatura em aberto vencida há DIAS_CARENCIA_BLOQUEIO dias (1 mês) ou mais
        passam a INADIMPLENTE. Varredura por limite (<=), idempotente e sem envio de mensagem;
        BLOQUEADO é mantido.
        """
        limite = hoje - timedelta(days=DIAS_CARENCIA_BLOQUEIO)
        stmt = (
            select(Fatura)
            .options(joinedload(Fatura.associado))
            .where(
                Fatura.status.in_([StatusFatura.PENDENTE, StatusFatura.ATRASADA]),
                Fatura.data_vencimento <= limite,
            )
        )
        for fatura in (await self.session.execute(stmt)).scalars().all():
            fatura.status = StatusFatura.ATRASADA
            if fatura.associado and fatura.associado.status == StatusAssociado.ATIVO:
                fatura.associado.status = StatusAssociado.INADIMPLENTE
                report.inadimplentes_atualizados += 1

    async def cobrar_fatura_agora(
        self,
        fatura_id: uuid.UUID,
        data_referencia: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Disparo avulso de cobrança pelo painel administrativo ("Cobrar agora no WhatsApp").
        Ignora automacao_ativa e envios anteriores.
        """
        hoje = data_referencia or hoje_clube()

        stmt = select(Fatura).options(joinedload(Fatura.associado)).where(Fatura.id == fatura_id)
        fatura = (await self.session.execute(stmt)).scalar_one_or_none()

        if not fatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fatura {fatura_id} não encontrada.",
            )

        if fatura.status in (StatusFatura.PAGO, StatusFatura.CANCELADO):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Fatura com status {fatura.status.value} não pode ser cobrada.",
            )

        if not fatura.associado or not fatura.associado.whatsapp or not fatura.associado.whatsapp.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Associado não possui WhatsApp cadastrado.",
            )

        cfg_repo = ConfiguracaoRepository(self.session)
        configuracao = await cfg_repo.get_or_create()

        if fatura.data_vencimento >= hoje:
            template = configuracao.template_d0
            template_code = "D0"
        else:
            template = configuracao.template_d_mais_3
            template_code = "D_MAIS_3"

        vars_fat = variaveis_da_fatura(fatura, fatura.associado, configuracao)
        mensagem = renderizar_template(template, vars_fat)

        queue = self.queue_service or get_global_whatsapp_queue()
        await queue.enqueue(
            phone=fatura.associado.whatsapp,
            message=mensagem,
            priority=MessagePriority.NORMAL,
            log_context=LogContext(
                etapa=EtapaRegua.AVULSO,
                associado_id=fatura.associado.id,
                fatura_id=fatura.id,
            ),
        )

        return {
            "fatura_id": str(fatura.id),
            "etapa": "AVULSO",
            "template": template_code,
            "destinatario": fatura.associado.whatsapp,
            "mensagem": mensagem,
        }
