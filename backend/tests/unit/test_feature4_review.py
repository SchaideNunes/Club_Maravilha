"""
Testes de Code Review da Feature 4 (Motor Baileys + Régua de Cobrança).
Cobre os itens obrigatórios 6, 7, 8 e 9 do parecer de revisão.
"""
import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.billing_engine_service import BillingEngineService
from app.jobs import billing_scheduler
from app.services.whatsapp_queue_service import (
    LogContext,
    MessagePriority,
    WhatsAppQueueService,
)
from app.services.whatsapp_service import (
    MockWhatsAppProvider,
    StatusConexaoWhatsApp,
    WhatsAppProvider,
)
from tests.conftest import TestingSessionLocal


async def _criar_associado(db_session) -> Associado:
    socio = Associado(
        nome="Sócio Review",
        cpf=f"{uuid.uuid4().int % 90000000000 + 10000000000}",
        whatsapp="5575999998888",
        email=f"socio_review_{uuid.uuid4().hex[:6]}@clube.com",
        status=StatusAssociado.ATIVO,
    )
    db_session.add(socio)
    await db_session.commit()
    return socio


async def _criar_fatura(db_session, associado_id: uuid.UUID, data_vencimento: date) -> Fatura:
    fatura = Fatura(
        associado_id=associado_id,
        valor_base=150.0,
        valor_total=150.0,
        data_vencimento=data_vencimento,
        referencia_mes=data_vencimento.strftime("%Y-%m"),
        status=StatusFatura.PENDENTE,
    )
    db_session.add(fatura)
    await db_session.commit()
    return fatura


# ==============================================================================
# Item 6: Log gravado ANTES do sleep anti-ban (mesmo em cancelamento)
# ==============================================================================
@pytest.mark.asyncio
async def test_item_6_log_gravado_antes_do_sleep_antiban_em_cancelamento(db_session, monkeypatch):
    """
    Ordem obrigatória: enviar -> gravar LogMensagem -> _pending_keys.discard -> task_done -> sleep.
    Se o sleep anti-ban lançar CancelledError, o LogMensagem SUCESSO deve existir no banco
    e is_pending deve ser False.
    """
    socio = await _criar_associado(db_session)
    fatura = await _criar_fatura(db_session, socio.id, date(2026, 10, 22))
    fatura_id = fatura.id
    provider = MockWhatsAppProvider()

    fila = WhatsAppQueueService(
        provider=provider,
        min_delay_seconds=10.0,
        max_delay_seconds=20.0,
        session_factory=TestingSessionLocal,
    )

    async def _sleep_cancelado(segundos, *args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(asyncio, "sleep", _sleep_cancelado)

    await fila.enqueue(
        phone="+55 (75) 99999-8888",
        message="Mensagem de teste item 6",
        priority=MessagePriority.NORMAL,
        log_context=LogContext(
            etapa=EtapaRegua.D_MENOS_3,
            associado_id=socio.id,
            fatura_id=fatura_id,
        ),
    )

    assert fila.is_pending(fatura_id, EtapaRegua.D_MENOS_3) is True

    # O process_one propaga o CancelledError vindo do sleep
    with pytest.raises(asyncio.CancelledError):
        await fila.process_one()

    # Log SUCESSO deve existir na base de dados
    async with TestingSessionLocal() as s:
        logs = list(
            (
                await s.execute(
                    select(LogMensagem).where(LogMensagem.fatura_id == fatura_id)
                )
            ).scalars().all()
        )

    assert len(logs) == 1
    assert logs[0].status == StatusEnvio.SUCESSO
    assert logs[0].etapa == EtapaRegua.D_MENOS_3

    # Chave pendente foi descartada
    assert fila.is_pending(fatura_id, EtapaRegua.D_MENOS_3) is False


# ==============================================================================
# Item 7: Fila não esvazia como ERRO com WhatsApp desconectado
# ==============================================================================
class ProviderOscilante(MockWhatsAppProvider):
    def __init__(self, status_inicial: StatusConexaoWhatsApp):
        super().__init__()
        self.current_status = status_inicial

    async def get_connection_status(self) -> Dict[str, Any]:
        return {"status": self.current_status.value}


@pytest.mark.asyncio
async def test_item_7_fila_espera_whatsapp_reconectar_sem_gerar_erros(db_session):
    """
    Antes do send, consulta provider.get_connection_status(); se não CONECTADO,
    devolve o item à fila sem tentar e sem gravar log.
    Ao reconectar: exatamente 1 envio, zero ERRO, 1 SUCESSO.
    """
    socio = await _criar_associado(db_session)
    fatura = await _criar_fatura(db_session, socio.id, date(2026, 10, 19))
    fatura_id = fatura.id
    provider = ProviderOscilante(StatusConexaoWhatsApp.DESCONECTADO)

    fila = WhatsAppQueueService(
        provider=provider,
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
        session_factory=TestingSessionLocal,
        disconnect_retry_delay=0.0,
    )

    await fila.enqueue(
        phone="5575999998888",
        message="Aviso com WhatsApp oscilante",
        priority=MessagePriority.NORMAL,
        log_context=LogContext(
            etapa=EtapaRegua.D0,
            associado_id=socio.id,
            fatura_id=fatura_id,
        ),
    )

    assert fila.qsize == 1

    # 1ª tentativa: WhatsApp DESCONECTADO -> devolve à fila sem registrar log
    resultado1 = await fila.process_one()
    assert resultado1 is None
    assert fila.qsize == 1
    assert len(provider.sent_messages) == 0

    async with TestingSessionLocal() as s:
        logs_tentativa_1 = list((await s.execute(select(LogMensagem))).scalars().all())
    assert len(logs_tentativa_1) == 0  # Zero ERRO gerado!

    # WhatsApp restabelece a conexão
    provider.current_status = StatusConexaoWhatsApp.CONECTADO

    # 2ª tentativa: WhatsApp CONECTADO -> envia com sucesso e grava log
    resultado2 = await fila.process_one()
    assert resultado2 is not None
    assert resultado2.get("status") == "success"
    assert fila.qsize == 0
    assert len(provider.sent_messages) == 1

    async with TestingSessionLocal() as s:
        logs_finais = list((await s.execute(select(LogMensagem))).scalars().all())

    assert len(logs_finais) == 1
    assert logs_finais[0].status == StatusEnvio.SUCESSO
    assert logs_finais[0].etapa == EtapaRegua.D0


# ==============================================================================
# Item 8: Disparo perdido em reinício (recuperação automática se horário já passou)
# ==============================================================================
@pytest.mark.asyncio
async def test_item_8_agendamento_recuperacao_quando_horario_ja_passou(monkeypatch):
    """
    Relógio 09:00 com horário 08:00 -> agenda recuperação (now + 60s).
    Relógio 09:00 com horário 10:00 -> não agenda recuperação.
    """
    tz = ZoneInfo(settings.TIMEZONE)
    # Simula relógio oficial do clube às 09:00
    relogio_simulado = datetime(2026, 10, 19, 9, 0, 0, tzinfo=tz)

    monkeypatch.setattr(billing_scheduler, "agora_clube", lambda: relogio_simulado)

    # 1. Horário 08:00 (já passou de 09:00) -> deve agendar recuperação
    billing_scheduler.start_scheduler_and_worker("08:00", agendar_recuperacao=True)
    try:
        job_recuperacao = billing_scheduler.scheduler.get_job(
            billing_scheduler.JOB_ID_RECUPERACAO
        )
        assert job_recuperacao is not None
        # Confere que o run_date da recuperação está agendado para 60s à frente
        run_date = job_recuperacao.next_run_time
        assert run_date == relogio_simulado + timedelta(seconds=60)
    finally:
        await billing_scheduler.stop_scheduler_and_worker()

    # 2. Horário 10:00 (ainda no futuro em relação às 09:00) -> NÃO deve agendar recuperação
    billing_scheduler.start_scheduler_and_worker("10:00", agendar_recuperacao=True)
    try:
        job_recuperacao_futuro = billing_scheduler.scheduler.get_job(
            billing_scheduler.JOB_ID_RECUPERACAO
        )
        assert job_recuperacao_futuro is None
    finally:
        await billing_scheduler.stop_scheduler_and_worker()


# ==============================================================================
# Item 9: Relatório conta descartados (ja_pendentes quando enqueue retorna False)
# ==============================================================================
@pytest.mark.asyncio
async def test_item_9_relatorio_conta_ja_pendentes_em_execucao_duplicada(db_session):
    """
    Rodar a régua 2x sem processar a fila:
    - 1ª execução: total_enfileirados == 1, qsize == 1
    - 2ª execução: total_enfileirados == 0, ja_pendentes == 1, qsize == 1
    """
    hoje = date(2026, 10, 19)

    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.automacao_ativa = True
    await db_session.commit()

    socio = await _criar_associado(db_session)
    # Vencimento em hoje + 3 dias -> etapa D-3
    vencimento_d3 = hoje + timedelta(days=3)
    fatura = await _criar_fatura(db_session, socio.id, vencimento_d3)

    fila = WhatsAppQueueService(
        provider=MockWhatsAppProvider(),
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
        session_factory=TestingSessionLocal,
    )

    engine = BillingEngineService(session=db_session, queue_service=fila)

    # 1ª execução da régua diária
    relatorio1 = await engine.processar_regua_diaria(data_referencia=hoje)
    assert relatorio1.total_enfileirados == 1
    assert relatorio1.d_minus_3_enviados == 1
    assert relatorio1.ja_pendentes == 0
    assert fila.qsize == 1

    # 2ª execução da régua diária sem esvaziar a fila
    relatorio2 = await engine.processar_regua_diaria(data_referencia=hoje)
    assert relatorio2.total_enfileirados == 0
    assert relatorio2.d_minus_3_enviados == 0
    assert relatorio2.ja_pendentes == 1
    assert fila.qsize == 1  # Fila segue com o mesmo item pendente


# ==============================================================================
# Opcionais: Validação max_length e sanitização de telefone
# ==============================================================================
def test_opcional_whatsapp_teste_envio_request_limite_tamanho():
    from pydantic import ValidationError
    from app.api.v1.endpoints.whatsapp import WhatsAppTesteEnvioRequest

    # Mensagem de até 4096 caracteres é aceita
    valida = WhatsAppTesteEnvioRequest(numero="75999998888", mensagem="A" * 4096)
    assert len(valida.mensagem) == 4096

    # Mensagem acima de 4096 caracteres é rejeitada com ValidationError
    with pytest.raises(ValidationError):
        WhatsAppTesteEnvioRequest(numero="75999998888", mensagem="A" * 4097)


def test_opcional_normalize_whatsapp_number_utiliza_sanitizer():
    from app.services.whatsapp_service import normalize_whatsapp_number

    assert normalize_whatsapp_number("+55 (75) 99999-8888") == "5575999998888"
    assert normalize_whatsapp_number("75999998888") == "5575999998888"

