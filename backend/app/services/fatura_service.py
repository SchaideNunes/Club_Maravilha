"""
Serviço de Negócio para Faturas, Cobrança Pix, Geração Mensal e Baixa Manual.
"""
import calendar
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
import re
from typing import Any, Dict, List, Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import hoje_clube
from app.core.config import settings
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura, calcular_valor_total_fatura
from app.models.log_mensagem import EtapaRegua
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.repositories.convidado_repository import ConvidadoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.schemas.fatura import (
    FaturaBaixaManual,
    FaturaCreate,
    FaturaPainelItemResponse,
    GeracaoFaturasResponse,
    PaginatedFaturasResponse,
)
from app.services.catraca_service import CatracaService
from app.services.pix_gateway_service import MockPixGateway
from app.services.template_service import renderizar_template, variaveis_da_fatura
from app.services.whatsapp_queue_service import (
    LogContext,
    MessagePriority,
    WhatsAppQueueService,
    get_global_whatsapp_queue,
)
from app.services.whatsapp_service import WhatsAppMessageBuilder


def calcular_data_vencimento(referencia_mes: str, dia_vencimento: int) -> date:
    """
    Calcula a data de vencimento a partir do mês de referência (AAAA-MM) e do dia do sócio.
    Se o dia exceder o último dia do mês (ex.: 31 em fevereiro), limita ao último dia do mês.
    """
    partes = referencia_mes.split("-")
    ano, mes = int(partes[0]), int(partes[1])
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(dia_vencimento, ultimo_dia)
    return date(ano, mes, dia)


def mes_anterior(referencia_mes: str) -> str:
    """Retorna o mês anterior no formato AAAA-MM."""
    partes = referencia_mes.split("-")
    ano, mes = int(partes[0]), int(partes[1])
    if mes == 1:
        ano -= 1
        mes = 12
    else:
        mes -= 1
    return f"{ano:04d}-{mes:02d}"


class FaturaService:
    def __init__(
        self,
        session: AsyncSession,
        queue_service: Optional[WhatsAppQueueService] = None,
    ) -> None:
        self.session = session
        self.queue_service = queue_service or get_global_whatsapp_queue()
        self.fatura_repo = FaturaRepository(session)
        self.associado_repo = AssociadoRepository(session)
        self.configuracao_repo = ConfiguracaoRepository(session)
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

    async def list_painel_faturas(
        self,
        referencia_mes: Optional[str] = None,
        status_filter: Optional[StatusFatura] = None,
        q: Optional[str] = None,
        associado_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedFaturasResponse:
        """
        Listagem paginada para o painel de faturas com nome do associado, filtros
        por mês de referência, status e busca textual (nome ou CPF).
        Ordenação padrão: nome do associado asc, depois vencimento desc.
        """
        query = (
            select(Fatura, Associado.nome.label("associado_nome"))
            .join(Associado, Fatura.associado_id == Associado.id)
        )
        count_query = (
            select(func.count(Fatura.id))
            .join(Associado, Fatura.associado_id == Associado.id)
        )

        if referencia_mes:
            query = query.where(Fatura.referencia_mes == referencia_mes)
            count_query = count_query.where(Fatura.referencia_mes == referencia_mes)

        if status_filter:
            query = query.where(Fatura.status == status_filter)
            count_query = count_query.where(Fatura.status == status_filter)

        if associado_id:
            query = query.where(Fatura.associado_id == associado_id)
            count_query = count_query.where(Fatura.associado_id == associado_id)

        if q and q.strip():
            termo = q.strip()
            condicoes = [
                Associado.nome.ilike(f"%{termo}%"),
                Associado.cpf.ilike(f"%{termo}%"),
            ]
            digitos = re.sub(r"\D", "", termo)
            if digitos:
                condicoes.append(
                    func.replace(func.replace(Associado.cpf, ".", ""), "-", "").ilike(f"%{digitos}%")
                )
            query = query.where(or_(*condicoes))
            count_query = count_query.where(or_(*condicoes))

        query = query.order_by(Associado.nome.asc(), Fatura.data_vencimento.desc())

        total = (await self.session.execute(count_query)).scalar_one()

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        rows = (await self.session.execute(query)).all()

        items = [
            FaturaPainelItemResponse(
                id=f.id,
                associado_id=f.associado_id,
                associado_nome=nome,
                referencia_mes=f.referencia_mes,
                data_vencimento=f.data_vencimento,
                valor_base=f.valor_base,
                valor_convidados_excedentes=f.valor_convidados_excedentes,
                valor_desconto=f.valor_desconto,
                valor_total=f.valor_total,
                convites_usados=f.convites_usados,
                convites_extras=f.convites_extras,
                status=f.status,
                forma_pagamento=f.forma_pagamento,
                data_pagamento=f.data_pagamento,
                lembretes_ativos=f.lembretes_ativos,
            )
            for f, nome in rows
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return PaginatedFaturasResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def create_fatura(self, data: FaturaCreate) -> Fatura:
        """Cria uma nova fatura com chave Pix dinâmica, txid exclusivo e QR Code."""
        existente = await self.fatura_repo.get_by_associado_e_referencia(
            data.associado_id, data.referencia_mes
        )
        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe fatura emitida para este associado nesta referência."
            )

        associado = await self.associado_repo.get_by_id(data.associado_id)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado para emissão de fatura."
            )

        # Agrega automaticamente convidados excedentes pendentes de faturamento
        convidado_repo = ConvidadoRepository(self.session)
        excedentes = await convidado_repo.get_excedentes_nao_faturados(data.associado_id)
        valor_excedentes = data.valor_convidados_excedentes
        if excedentes and valor_excedentes == Decimal("0.00"):
            valor_excedentes = sum(c.valor_cobrado for c in excedentes)

        valor_total = calcular_valor_total_fatura(data.valor_base, valor_excedentes, data.valor_desconto)

        # Gera Pix Dinâmico no Gateway com valor total consolidado
        pix_charge = self.pix_gateway.create_dynamic_pix_charge(
            fatura_id=str(uuid.uuid4()),
            valor=valor_total,
            referencia_mes=data.referencia_mes,
            nome_associado=associado.nome,
            cpf_associado=associado.cpf
        )

        fatura = Fatura(
            associado_id=data.associado_id,
            referencia_mes=data.referencia_mes,
            valor_base=data.valor_base,
            valor_convidados_excedentes=valor_excedentes,
            valor_desconto=data.valor_desconto,
            valor_total=valor_total,
            convites_usados=len(excedentes) if excedentes else 0,
            convites_extras=len(excedentes) if excedentes else 0,
            data_vencimento=data.data_vencimento,
            forma_pagamento=data.forma_pagamento,
            status=StatusFatura.PENDENTE,
            txid=pix_charge.txid,
            pix_copia_cola=pix_charge.pix_copia_cola,
            pix_qr_code_url=pix_charge.pix_qr_code_url,
        )

        try:
            created = await self.fatura_repo.create(fatura)

            # Vincula os convites excedentes faturados a esta fatura
            if excedentes:
                for convite in excedentes:
                    convite.fatura_agregada_id = created.id

            await self.session.commit()
            await self.session.refresh(created)
            return created
        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe fatura emitida para este associado nesta referência."
            )

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

    async def gerar_faturas_mes(
        self,
        referencia_mes: Optional[str] = None,
    ) -> GeracaoFaturasResponse:
        """
        Gera as faturas mensais para todos os associados elegíveis do clube.
        Idempotente: faturas existentes (em qualquer status, inclusive CANCELADO) não são recriadas.
        """
        if referencia_mes is None:
            hoje = hoje_clube()
            referencia_mes = f"{hoje.year:04d}-{hoje.month:02d}"
        else:
            if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", referencia_mes):
                raise ValueError(f"Mês de referência inválido: {referencia_mes}")

        ano, mes = map(int, referencia_mes.split("-"))
        ultimo_dia_mes = calendar.monthrange(ano, mes)[1]
        limite_adesao = date(ano, mes, ultimo_dia_mes)

        cfg = await self.configuracao_repo.get_or_create()
        valor_mensalidade = cfg.valor_mensalidade
        franquia = cfg.franquia_convidados
        valor_extra = cfg.valor_convidado_extra

        # 1. Busca todos os sócios cuja data_adesao seja anterior ou igual ao fim do mês de referência
        socios_query = (
            select(Associado)
            .where(Associado.data_adesao <= limite_adesao)
        )
        socios_elegiveis = list((await self.session.execute(socios_query)).scalars().all())

        if not socios_elegiveis:
            return GeracaoFaturasResponse(
                referencia_mes=referencia_mes,
                criadas=0,
                ja_existentes=0,
                total=0,
            )

        # 2. Busca faturas já existentes neste mês de referência (qualquer status conta)
        existentes_query = select(Fatura.associado_id).where(Fatura.referencia_mes == referencia_mes)
        existentes_ids = set((await self.session.execute(existentes_query)).scalars().all())

        # 3. Agregação em lote de convites usados no mês anterior (sem N+1)
        ref_anterior = mes_anterior(referencia_mes)
        ano_ant, mes_ant = map(int, ref_anterior.split("-"))
        inicio_ant = date(ano_ant, mes_ant, 1)
        fim_ant = date(ano_ant, mes_ant, calendar.monthrange(ano_ant, mes_ant)[1])

        convidados_query = (
            select(Convidado.associado_titular_id, func.count(Convidado.id))
            .where(
                Convidado.status != StatusConvidado.CANCELADO,
                Convidado.data_visita >= inicio_ant,
                Convidado.data_visita <= fim_ant,
            )
            .group_by(Convidado.associado_titular_id)
        )
        convidados_count = dict((await self.session.execute(convidados_query)).all())

        criadas = 0
        ja_existentes = 0

        for socio in socios_elegiveis:
            if socio.id in existentes_ids:
                ja_existentes += 1
                continue

            usados = convidados_count.get(socio.id, 0)
            extras = max(0, usados - franquia)
            valor_excedentes = (Decimal(extras) * valor_extra).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            valor_base = valor_mensalidade
            valor_desconto = Decimal("0.00")
            valor_total = calcular_valor_total_fatura(valor_base, valor_excedentes, valor_desconto)
            vencimento = calcular_data_vencimento(referencia_mes, socio.dia_vencimento)

            nova_fatura = Fatura(
                associado_id=socio.id,
                referencia_mes=referencia_mes,
                valor_base=valor_base,
                valor_convidados_excedentes=valor_excedentes,
                valor_desconto=valor_desconto,
                valor_total=valor_total,
                convites_usados=usados,
                convites_extras=extras,
                data_vencimento=vencimento,
                forma_pagamento=FormaPagamento.PIX,
                status=StatusFatura.PENDENTE,
            )
            self.session.add(nova_fatura)
            criadas += 1

        await self.session.commit()

        return GeracaoFaturasResponse(
            referencia_mes=referencia_mes,
            criadas=criadas,
            ja_existentes=ja_existentes,
            total=criadas + ja_existentes,
        )

    async def marcar_faturas_atrasadas(
        self,
        data_referencia: Optional[date] = None,
    ) -> int:
        """
        Atualiza para ATRASADA todas as faturas PENDENTES com data_vencimento anterior
        a data_referencia (padrão: hoje_clube()). Não altera faturas pagas ou canceladas
        nem o status cadastral do associado.
        """
        if data_referencia is None:
            data_referencia = hoje_clube()

        stmt = (
            update(Fatura)
            .where(
                Fatura.status == StatusFatura.PENDENTE,
                Fatura.data_vencimento < data_referencia,
            )
            .values(status=StatusFatura.ATRASADA)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def baixa_manual(
        self,
        fatura_id: uuid.UUID,
        dados: FaturaBaixaManual,
    ) -> Fatura:
        """
        Realiza a baixa manual de uma fatura PENDENTE ou ATRASADA pela administração.
        - Se a fatura não existir -> 404
        - Se a fatura já estiver PAGA ou CANCELADA -> 409
        - Transição atômica (UPDATE ... WHERE status IN (PENDENTE, ATRASADA))
        - Se não restar nenhuma fatura vencida em aberto para o associado, reativa o associado para ATIVO
        - Enfileira após o commit um único recibo digital com MessagePriority.HIGH
        """
        fatura = await self.fatura_repo.get_by_id(fatura_id)
        if not fatura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fatura não encontrada."
            )

        if fatura.status in (StatusFatura.PAGO, StatusFatura.CANCELADO):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Não é possível dar baixa em fatura com status '{fatura.status.value}'."
            )

        agora = datetime.now(timezone.utc)
        pago_em = dados.data_pagamento or agora

        stmt = (
            update(Fatura)
            .where(
                Fatura.id == fatura_id,
                Fatura.status.in_([StatusFatura.PENDENTE, StatusFatura.ATRASADA]),
            )
            .values(
                status=StatusFatura.PAGO,
                forma_pagamento=dados.forma_pagamento,
                data_pagamento=pago_em,
                notificado_pos_pagamento_em=agora,
            )
        )
        res = await self.session.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fatura já liquidada ou em estado conflitante."
            )

        await self.session.refresh(fatura)

        # Reativação do associado se não houver outras faturas vencidas em aberto
        associado = await self.associado_repo.get_by_id(fatura.associado_id)
        if associado:
            hoje = hoje_clube()
            outras_vencidas_query = select(Fatura.id).where(
                Fatura.associado_id == associado.id,
                Fatura.id != fatura.id,
                or_(
                    Fatura.status == StatusFatura.ATRASADA,
                    and_(
                        Fatura.status == StatusFatura.PENDENTE,
                        Fatura.data_vencimento < hoje,
                    ),
                ),
            )
            tem_outras_vencidas = (await self.session.execute(outras_vencidas_query)).scalars().first() is not None
            if not tem_outras_vencidas and associado.status in (StatusAssociado.INADIMPLENTE, StatusAssociado.BLOQUEADO):
                associado.status = StatusAssociado.ATIVO

        await self.session.commit()
        await self.session.refresh(fatura)

        # Enfileira recibo digital de prioridade alta após commit
        if associado and associado.whatsapp:
            cfg = await self.configuracao_repo.get_or_create()
            variaveis = variaveis_da_fatura(fatura, associado, cfg)
            texto_recibo = renderizar_template(cfg.template_recibo, variaveis)
            await self.queue_service.enqueue(
                phone=associado.whatsapp,
                message=texto_recibo,
                priority=MessagePriority.HIGH,
                log_context=LogContext(
                    etapa=EtapaRegua.RECIBO,
                    associado_id=associado.id,
                    fatura_id=fatura.id,
                ),
            )

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
            await self.queue_service.enqueue(
                phone=associado.whatsapp,
                message=msg_recibo,
                priority=MessagePriority.HIGH
            )

        await self.session.commit()

        # 8. Sincronização imediata na catraca física
        catraca_service = CatracaService(self.session)
        await catraca_service.notify_turnstile_sync(reason=f"pix_paid_{txid}")

        return {
            "status": "success",
            "message": "Fatura liquidada e associado liberado com sucesso.",
            "txid": txid
        }
