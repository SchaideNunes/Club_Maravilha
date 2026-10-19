"""
Feature 4 - Testes da Régua de Cobrança (D-3, D-0, D+3, D+7) com templates da Configuração e
idempotência por LogMensagem.

Substitui tests/unit/test_billing_engine.py: o contrato antigo usava mensagens fixas
(WhatsAppMessageBuilder) e idempotência pelos campos `notificado_*` da fatura; agora as mensagens
vêm dos templates editáveis da Configuração e a idempotência é a auditoria de envios (LogMensagem).

Contrato (app/services/billing_engine_service.py):
- `BillingEngineService(session, queue_service=None)`;
  `await processar_regua_diaria(data_referencia=None) -> BillingExecutionReport` (padrão: hoje_clube()).
- Etapas para a data de referência `hoje`:
    D_MENOS_3: vencimento == hoje + 3 -> template_d_menos_3
    D0:        vencimento == hoje     -> template_d0
    D_MAIS_3:  vencimento == hoje - 3 -> template_d_mais_3
    D_MAIS_7:  vencimento == hoje - DIAS_CARENCIA_BLOQUEIO -> template_d_mais_7; a fatura vira ATRASADA e o
               associado ATIVO vira INADIMPLENTE (BLOQUEADO é mantido), mesmo sem WhatsApp cadastrado.
- Somente faturas PENDENTE/ATRASADA; PAGO/CANCELADO nunca recebem mensagem.
- Mensagem = renderizar_template(template, variaveis_da_fatura(fatura, associado, configuracao)).
- Enfileira `queue_service.enqueue(phone=associado.whatsapp, message=..., priority=MessagePriority.NORMAL,
  log_context=LogContext(etapa, associado_id, fatura_id))`.
- Idempotência: não enfileira a etapa para a fatura se já existir LogMensagem SUCESSO (fatura_id, etapa);
  logs ERRO não bloqueiam (nova tentativa); os campos legados `notificado_*` NÃO são mais critério.
  A consulta é agregada: o número de SELECTs não cresce com a quantidade de faturas (sem N+1).
- Associado sem WhatsApp (vazio/brancos): ignorado sem quebrar (conta em `ignorados_sem_whatsapp`).
- Configuracao.automacao_ativa == False: nada é enfileirado nem alterado; relatório com automacao_ativa=False.
- BillingExecutionReport: data_referencia, d_minus_3_enviados, d_zero_enviados, d_plus_3_enviados,
  d_plus_7_enviados, inadimplentes_atualizados, total_enfileirados, ja_enviados, ignorados_sem_whatsapp,
  automacao_ativa, erros.
"""
import asyncio
import itertools
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, List, Optional

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DIAS_CARENCIA_BLOQUEIO
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.billing_engine_service import BillingEngineService
from app.services.whatsapp_queue_service import LogContext, MessagePriority, WhatsAppQueueService
from app.services.whatsapp_service import MockWhatsAppProvider
from tests.conftest import TestingSessionLocal, test_engine

HOJE = date(2026, 9, 10)
_seq = itertools.count(1)


@dataclass
class ItemEnfileirado:
    phone: str
    message: str
    priority: Any
    log_context: Optional[LogContext]


class FilaFalsa:
    """Captura os enfileiramentos sem enviar nada."""

    def __init__(self) -> None:
        self.itens: List[ItemEnfileirado] = []

    async def enqueue(self, phone, message, priority=MessagePriority.NORMAL, log_context=None) -> None:
        self.itens.append(ItemEnfileirado(phone, message, priority, log_context))

    def por_etapa(self, etapa: EtapaRegua) -> List[ItemEnfileirado]:
        return [i for i in self.itens if i.log_context and i.log_context.etapa == etapa]


async def _configurar(db_session: AsyncSession, **campos):
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    valores = {
        "chave_pix": "pix@clubemaravilha.com.br",
        "template_d_menos_3": "D-3 {nome} {valor_total} {vencimento} {chave_pix}",
        "template_d0": "D0 {nome} {valor_total} {vencimento} {chave_pix}",
        "template_d_mais_3": "D+3 {nome} {valor_total} {vencimento} {chave_pix}",
        "template_d_mais_7": "D+7 {nome} {valor_total} {vencimento} {chave_pix}",
    }
    valores.update(campos)
    for chave, valor in valores.items():
        setattr(cfg, chave, valor)
    await db_session.commit()
    return cfg


async def _socio(db_session, nome: str, whatsapp: str = None, status=StatusAssociado.ATIVO) -> Associado:
    n = next(_seq)
    socio = Associado(
        nome=nome,
        cpf=f"{n:03d}.000.000-{n % 100:02d}",
        whatsapp=whatsapp if whatsapp is not None else f"55759{n:08d}",
        email=f"socio{n}@clube.com",
        status=status,
    )
    db_session.add(socio)
    await db_session.commit()
    return socio


async def _fatura(db_session, socio: Associado, vencimento: date, status=StatusFatura.PENDENTE,
                  valor=Decimal("150.00"), referencia: str = "2026-09") -> Fatura:
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes=referencia,
        valor_base=valor,
        valor_total=valor,
        data_vencimento=vencimento,
        status=status,
    )
    db_session.add(fatura)
    await db_session.commit()
    return fatura


def _engine(db_session, fila) -> BillingEngineService:
    return BillingEngineService(session=db_session, queue_service=fila)


# ------------------------------------------------------------------------------
# Etapas e templates
# ------------------------------------------------------------------------------
async def test_cada_etapa_usa_o_template_da_configuracao_com_variaveis(db_session):
    await _configurar(db_session)
    s_d3 = await _socio(db_session, "Ana D3")
    s_d0 = await _socio(db_session, "Bruno D0")
    s_dp3 = await _socio(db_session, "Carla D3+")
    s_dp7 = await _socio(db_session, "Davi D7+")
    f_d3 = await _fatura(db_session, s_d3, HOJE + timedelta(days=3), valor=Decimal("1234.50"))
    f_d0 = await _fatura(db_session, s_d0, HOJE)
    f_dp3 = await _fatura(db_session, s_dp3, HOJE - timedelta(days=3), status=StatusFatura.ATRASADA)
    f_dp7 = await _fatura(db_session, s_dp7, HOJE - timedelta(days=DIAS_CARENCIA_BLOQUEIO))
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert report.data_referencia == HOJE
    assert report.automacao_ativa is True
    assert (report.d_minus_3_enviados, report.d_zero_enviados, report.d_plus_3_enviados,
            report.d_plus_7_enviados) == (1, 1, 1, 1)
    assert report.total_enfileirados == 4
    assert report.erros == []

    pix = "pix@clubemaravilha.com.br"
    esperado = {
        EtapaRegua.D_MENOS_3: (s_d3, f_d3, f"D-3 Ana D3 R$ 1.234,50 13/09/2026 {pix}"),
        EtapaRegua.D0: (s_d0, f_d0, f"D0 Bruno D0 R$ 150,00 10/09/2026 {pix}"),
        EtapaRegua.D_MAIS_3: (s_dp3, f_dp3, f"D+3 Carla D3+ R$ 150,00 07/09/2026 {pix}"),
        EtapaRegua.D_MAIS_7: (s_dp7, f_dp7, f"D+7 Davi D7+ R$ 150,00 03/09/2026 {pix}"),
    }
    for etapa, (socio, fatura, mensagem) in esperado.items():
        itens = fila.por_etapa(etapa)
        assert len(itens) == 1, etapa
        item = itens[0]
        assert item.message == mensagem
        assert item.phone == socio.whatsapp
        assert item.priority == MessagePriority.NORMAL
        assert item.log_context.associado_id == socio.id
        assert item.log_context.fatura_id == fatura.id


async def test_template_padrao_inclui_chave_pix(db_session):
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.chave_pix = "12.345.678/0001-90"
    await db_session.commit()
    socio = await _socio(db_session, "Eva Padrão")
    await _fatura(db_session, socio, HOJE)
    fila = FilaFalsa()

    await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert len(fila.itens) == 1
    mensagem = fila.itens[0].message
    assert "Eva Padrão" in mensagem
    assert "12.345.678/0001-90" in mensagem
    assert "{" not in mensagem


async def test_d_mais_7_marca_fatura_atrasada_e_associado_inadimplente(db_session):
    await _configurar(db_session)
    socio = await _socio(db_session, "Fábio D7")
    fatura = await _fatura(db_session, socio, HOJE - timedelta(days=DIAS_CARENCIA_BLOQUEIO))

    report = await _engine(db_session, FilaFalsa()).processar_regua_diaria(data_referencia=HOJE)

    await db_session.refresh(fatura)
    await db_session.refresh(socio)
    assert fatura.status == StatusFatura.ATRASADA
    assert socio.status == StatusAssociado.INADIMPLENTE
    assert report.inadimplentes_atualizados == 1


async def test_d_mais_7_mantem_associado_bloqueado(db_session):
    await _configurar(db_session)
    socio = await _socio(db_session, "Gabi Bloqueada", status=StatusAssociado.BLOQUEADO)
    await _fatura(db_session, socio, HOJE - timedelta(days=DIAS_CARENCIA_BLOQUEIO))

    report = await _engine(db_session, FilaFalsa()).processar_regua_diaria(data_referencia=HOJE)

    await db_session.refresh(socio)
    assert socio.status == StatusAssociado.BLOQUEADO
    assert report.inadimplentes_atualizados == 0


async def test_faturas_pagas_ou_canceladas_nunca_recebem_mensagem(db_session):
    await _configurar(db_session)
    for status in (StatusFatura.PAGO, StatusFatura.CANCELADO):
        for dias in (-3, 0, 3, DIAS_CARENCIA_BLOQUEIO):
            socio = await _socio(db_session, f"Quitado {status.value} {dias}")
            await _fatura(db_session, socio, HOJE - timedelta(days=dias), status=status)
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert fila.itens == []
    assert report.total_enfileirados == 0
    assert report.inadimplentes_atualizados == 0


async def test_vencimentos_fora_das_etapas_sao_ignorados(db_session):
    await _configurar(db_session)
    for dias in (-4, -2, -1, 1, 2, 4, 5, 6, 8, 30):
        socio = await _socio(db_session, f"Fora {dias}")
        await _fatura(db_session, socio, HOJE - timedelta(days=dias))
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert fila.itens == []
    assert report.total_enfileirados == 0


async def test_data_referencia_padrao_e_hoje_do_clube(db_session, monkeypatch):
    import app.services.billing_engine_service as modulo

    await _configurar(db_session)
    monkeypatch.setattr(modulo, "hoje_clube", lambda: HOJE)
    socio = await _socio(db_session, "Hoje Clube")
    await _fatura(db_session, socio, HOJE)
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria()

    assert report.data_referencia == HOJE
    assert report.d_zero_enviados == 1


# ------------------------------------------------------------------------------
# WhatsApp ausente e automação desligada
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("whatsapp", ["", "   "])
async def test_associado_sem_whatsapp_e_ignorado_sem_quebrar(db_session, whatsapp):
    await _configurar(db_session)
    sem = await _socio(db_session, "Sem Zap", whatsapp=whatsapp)
    com = await _socio(db_session, "Com Zap")
    await _fatura(db_session, sem, HOJE)
    await _fatura(db_session, com, HOJE)
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert [i.log_context.associado_id for i in fila.itens] == [com.id]
    assert report.d_zero_enviados == 1
    assert report.ignorados_sem_whatsapp == 1
    assert report.erros == []


async def test_d_mais_7_sem_whatsapp_ainda_marca_inadimplente(db_session):
    await _configurar(db_session)
    socio = await _socio(db_session, "Sem Zap D7", whatsapp="")
    await _fatura(db_session, socio, HOJE - timedelta(days=DIAS_CARENCIA_BLOQUEIO))
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    await db_session.refresh(socio)
    assert fila.itens == []
    assert socio.status == StatusAssociado.INADIMPLENTE
    assert report.ignorados_sem_whatsapp == 1


async def test_automacao_desligada_nao_dispara_nada(db_session):
    await _configurar(db_session, automacao_ativa=False)
    s_d0 = await _socio(db_session, "Desligado D0")
    s_d7 = await _socio(db_session, "Desligado D7")
    await _fatura(db_session, s_d0, HOJE)
    f_d7 = await _fatura(db_session, s_d7, HOJE - timedelta(days=DIAS_CARENCIA_BLOQUEIO))
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert fila.itens == []
    assert report.automacao_ativa is False
    assert report.total_enfileirados == 0
    await db_session.refresh(s_d7)
    await db_session.refresh(f_d7)
    assert s_d7.status == StatusAssociado.ATIVO
    assert f_d7.status == StatusFatura.PENDENTE


# ------------------------------------------------------------------------------
# Idempotência por LogMensagem
# ------------------------------------------------------------------------------
async def test_reexecucao_apos_envio_com_sucesso_nao_reenvia(db_session):
    """Fluxo real: régua -> fila (Mock) grava LogMensagem SUCESSO -> nova execução não reenvia."""
    await _configurar(db_session)
    socios = [await _socio(db_session, f"Idem {i}") for i in range(4)]
    for socio, dias in zip(socios, (-3, 0, 3, DIAS_CARENCIA_BLOQUEIO)):
        await _fatura(db_session, socio, HOJE - timedelta(days=dias))
    provider = MockWhatsAppProvider()
    fila = WhatsAppQueueService(
        provider=provider, min_delay_seconds=0.0, max_delay_seconds=0.0, session_factory=TestingSessionLocal
    )
    engine = _engine(db_session, fila)

    primeiro = await engine.processar_regua_diaria(data_referencia=HOJE)
    assert primeiro.total_enfileirados == 4

    worker = asyncio.create_task(fila.start_worker())
    await fila.join()
    await fila.stop_worker(worker)
    assert len(provider.sent_messages) == 4

    segundo = await engine.processar_regua_diaria(data_referencia=HOJE)
    assert segundo.total_enfileirados == 0
    assert (segundo.d_minus_3_enviados, segundo.d_zero_enviados, segundo.d_plus_3_enviados,
            segundo.d_plus_7_enviados) == (0, 0, 0, 0)
    assert segundo.ja_enviados == 4
    assert fila.qsize == 0


async def test_log_de_erro_nao_bloqueia_nova_tentativa(db_session):
    await _configurar(db_session)
    socio = await _socio(db_session, "Retry")
    fatura = await _fatura(db_session, socio, HOJE)
    db_session.add(LogMensagem(
        associado_id=socio.id, fatura_id=fatura.id, destinatario=socio.whatsapp,
        etapa=EtapaRegua.D0, mensagem="x", status=StatusEnvio.ERRO, erro="engine fora do ar",
    ))
    await db_session.commit()
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert report.d_zero_enviados == 1
    assert len(fila.itens) == 1


async def test_sucesso_de_outra_etapa_nao_bloqueia(db_session):
    await _configurar(db_session)
    socio = await _socio(db_session, "Outra Etapa")
    fatura = await _fatura(db_session, socio, HOJE)
    for etapa in (EtapaRegua.D_MENOS_3, EtapaRegua.AVULSO, EtapaRegua.TESTE):
        db_session.add(LogMensagem(
            associado_id=socio.id, fatura_id=fatura.id, destinatario=socio.whatsapp,
            etapa=etapa, mensagem="x", status=StatusEnvio.SUCESSO,
        ))
    await db_session.commit()
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert report.d_zero_enviados == 1


async def test_sucesso_da_mesma_etapa_em_outra_fatura_nao_bloqueia(db_session):
    await _configurar(db_session)
    socio = await _socio(db_session, "Duas Faturas")
    antiga = await _fatura(db_session, socio, date(2026, 8, 10), status=StatusFatura.PAGO, referencia="2026-08")
    await _fatura(db_session, socio, HOJE)
    db_session.add(LogMensagem(
        associado_id=socio.id, fatura_id=antiga.id, destinatario=socio.whatsapp,
        etapa=EtapaRegua.D0, mensagem="x", status=StatusEnvio.SUCESSO,
    ))
    await db_session.commit()
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert report.d_zero_enviados == 1


async def test_campos_legados_notificado_nao_sao_mais_criterio(db_session):
    """Sem LogMensagem SUCESSO a etapa é enviada, mesmo com `notificado_d_zero_em` preenchido."""
    from datetime import datetime, timezone

    await _configurar(db_session)
    socio = await _socio(db_session, "Legado")
    fatura = await _fatura(db_session, socio, HOJE)
    fatura.notificado_d_zero_em = datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc)
    await db_session.commit()
    fila = FilaFalsa()

    report = await _engine(db_session, fila).processar_regua_diaria(data_referencia=HOJE)

    assert report.d_zero_enviados == 1


async def test_consulta_de_idempotencia_nao_tem_n_mais_1(db_session):
    """O número de SELECTs da régua não cresce com a quantidade de faturas elegíveis."""
    await _configurar(db_session)

    async def _contar_selects(qtd_faturas: int, vencimento: date) -> int:
        for i in range(qtd_faturas):
            socio = await _socio(db_session, f"N+1 {vencimento} {i}")
            fatura = await _fatura(db_session, socio, vencimento)
            if i % 2 == 0:  # metade já recebeu a etapa
                db_session.add(LogMensagem(
                    associado_id=socio.id, fatura_id=fatura.id, destinatario=socio.whatsapp,
                    etapa=EtapaRegua.D_MENOS_3, mensagem="x", status=StatusEnvio.SUCESSO,
                ))
        await db_session.commit()

        selects = []

        def _registrar(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                selects.append(statement)

        event.listen(test_engine.sync_engine, "before_cursor_execute", _registrar)
        try:
            referencia = vencimento - timedelta(days=3)
            await _engine(db_session, FilaFalsa()).processar_regua_diaria(data_referencia=referencia)
        finally:
            event.remove(test_engine.sync_engine, "before_cursor_execute", _registrar)
        return len(selects)

    poucas = await _contar_selects(2, date(2026, 11, 13))
    muitas = await _contar_selects(10, date(2026, 12, 13))

    assert muitas == poucas
