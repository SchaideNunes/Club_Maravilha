"""
Testes unitários da Baixa Manual de pagamento (Feature 3).

Contrato: `FaturaService(session, queue_service=None).baixa_manual(fatura_id, dados: FaturaBaixaManual) -> Fatura`
(queue_service default: get_global_whatsapp_queue()).
- Aceita faturas PENDENTE ou ATRASADA. PAGO -> HTTPException 409; CANCELADO -> 409; inexistente -> 404.
- Efeitos: status PAGO, forma_pagamento e data_pagamento gravados (data omitida -> agora UTC),
  lembretes_ativos False, notificado_pos_pagamento_em preenchido.
- Reativação: associado INADIMPLENTE/BLOQUEADO volta a ATIVO quando não restar fatura VENCIDA em
  aberto (status ATRASADA, ou PENDENTE com data_vencimento < hoje_clube()). Uma fatura PENDENTE
  ainda dentro do prazo NÃO impede a reativação (o sócio está em dia). Status ATIVO nunca muda.
- Recibo: após o commit, enfileira UMA mensagem com MessagePriority.HIGH, texto = template_recibo
  da Configuracao renderizado (template_service), log_context=LogContext(etapa=RECIBO,
  associado_id, fatura_id). O LogMensagem é gravado pela fila no envio.
- Concorrência: a transição para PAGO é atômica (lock/UPDATE condicional da fatura); só a
  baixa vencedora enfileira recibo.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.core import clock
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.schemas.fatura import FaturaBaixaManual
from app.services.fatura_service import FaturaService
from app.services.whatsapp_queue_service import MessagePriority, WhatsAppQueueService
from app.services.whatsapp_service import MockWhatsAppProvider
from tests.conftest import TestingSessionLocal

TEMPLATE_RECIBO_TESTE = (
    "Recibo {nome}: total {valor_total} (base {valor_base}, {convites_usados} usados, "
    "{convites_extras} extras) venc {vencimento} pix {chave_pix}"
)


@pytest.fixture
def congelar_hoje(monkeypatch):
    def _congelar(dia: date) -> None:
        instante = datetime(dia.year, dia.month, dia.day, 12, 0, tzinfo=clock.get_clube_tz())
        monkeypatch.setattr(clock, "agora_clube", lambda: instante)
    return _congelar


@pytest.fixture
def provider():
    return MockWhatsAppProvider()


@pytest.fixture
def fila(provider):
    return WhatsAppQueueService(
        provider=provider,
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
        session_factory=TestingSessionLocal,
    )


async def _cenario(session, status_socio=StatusAssociado.ATIVO, status_fatura=StatusFatura.PENDENTE,
                   vencimento=date(2026, 11, 10)):
    cfg = await ConfiguracaoRepository(session).get_or_create()
    cfg.valor_mensalidade = Decimal("150.00")
    cfg.franquia_convidados = 8
    cfg.valor_convidado_extra = Decimal("35.00")
    cfg.chave_pix = "financeiro@clubmaravilha.com.br"
    cfg.template_recibo = TEMPLATE_RECIBO_TESTE
    socio = Associado(
        nome="Joana Prado",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="joana@clube.com",
        status=status_socio,
        dia_vencimento=10,
    )
    session.add(socio)
    await session.flush()
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-11",
        valor_base=Decimal("1150.00"),
        valor_convidados_excedentes=Decimal("70.00"),
        valor_total=Decimal("1220.00"),
        convites_usados=10,
        convites_extras=2,
        data_vencimento=vencimento,
        status=status_fatura,
    )
    session.add(fatura)
    await session.commit()
    return socio, fatura


async def _outra_fatura(session, socio, referencia, vencimento, status):
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes=referencia,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=vencimento,
        status=status,
    )
    session.add(fatura)
    await session.commit()
    return fatura


async def test_baixa_manual_marca_paga_com_forma_e_data(db_session, fila, congelar_hoje):
    congelar_hoje(date(2026, 11, 12))
    _, fatura = await _cenario(db_session)
    pago_em = datetime(2026, 11, 11, 15, 30, tzinfo=timezone.utc)

    fatura_id = fatura.id
    resultado = await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura_id, FaturaBaixaManual(forma_pagamento=FormaPagamento.DINHEIRO, data_pagamento=pago_em)
    )

    assert resultado.id == fatura_id
    db_session.expire_all()
    lida = (await db_session.execute(select(Fatura).where(Fatura.id == fatura_id))).scalar_one()
    assert lida.status == StatusFatura.PAGO
    assert lida.forma_pagamento == FormaPagamento.DINHEIRO
    assert lida.data_pagamento.replace(tzinfo=timezone.utc) == pago_em
    assert lida.lembretes_ativos is False
    assert lida.notificado_pos_pagamento_em is not None


async def test_baixa_manual_sem_data_usa_instante_atual(db_session, fila):
    _, fatura = await _cenario(db_session)
    antes = datetime.now(timezone.utc) - timedelta(seconds=5)
    fatura_id = fatura.id
    await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura_id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
    )

    db_session.expire_all()
    lida = (await db_session.execute(select(Fatura).where(Fatura.id == fatura_id))).scalar_one()
    pago_em = lida.data_pagamento
    if pago_em.tzinfo is None:
        pago_em = pago_em.replace(tzinfo=timezone.utc)
    assert antes <= pago_em <= datetime.now(timezone.utc) + timedelta(seconds=5)
    assert lida.forma_pagamento == FormaPagamento.PIX


async def test_baixa_manual_aceita_fatura_atrasada(db_session, fila):
    _, fatura = await _cenario(db_session, status_fatura=StatusFatura.ATRASADA)

    await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.CARTAO)
    )

    await db_session.refresh(fatura)
    assert fatura.status == StatusFatura.PAGO
    assert fatura.forma_pagamento == FormaPagamento.CARTAO


@pytest.mark.parametrize("status_fatura", [StatusFatura.PAGO, StatusFatura.CANCELADO])
async def test_baixa_manual_em_fatura_paga_ou_cancelada_retorna_409(db_session, fila, status_fatura):
    _, fatura = await _cenario(db_session, status_fatura=status_fatura)

    with pytest.raises(HTTPException) as exc:
        await FaturaService(db_session, queue_service=fila).baixa_manual(
            fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
        )

    assert exc.value.status_code == 409
    assert fila.qsize == 0


async def test_baixa_manual_fatura_inexistente_retorna_404(db_session, fila):
    import uuid

    with pytest.raises(HTTPException) as exc:
        await FaturaService(db_session, queue_service=fila).baixa_manual(
            uuid.uuid4(), FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
        )
    assert exc.value.status_code == 404


@pytest.mark.parametrize("status_socio", [StatusAssociado.INADIMPLENTE, StatusAssociado.BLOQUEADO])
async def test_baixa_reativa_associado_sem_outras_faturas_vencidas(db_session, fila, congelar_hoje, status_socio):
    congelar_hoje(date(2026, 11, 20))
    socio, fatura = await _cenario(db_session, status_socio=status_socio, status_fatura=StatusFatura.ATRASADA)
    # fatura antiga já paga e uma futura ainda no prazo não impedem a reativação
    await _outra_fatura(db_session, socio, "2026-10", date(2026, 10, 10), StatusFatura.PAGO)
    await _outra_fatura(db_session, socio, "2026-12", date(2026, 12, 10), StatusFatura.PENDENTE)

    await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
    )

    await db_session.refresh(socio)
    assert socio.status == StatusAssociado.ATIVO


@pytest.mark.parametrize(
    "status_outra, vencimento_outra",
    [
        (StatusFatura.ATRASADA, date(2026, 10, 10)),
        (StatusFatura.PENDENTE, date(2026, 10, 10)),  # vencida, ainda não marcada como ATRASADA
    ],
)
async def test_baixa_nao_reativa_com_outra_fatura_vencida(db_session, fila, congelar_hoje,
                                                         status_outra, vencimento_outra):
    congelar_hoje(date(2026, 11, 20))
    socio, fatura = await _cenario(
        db_session, status_socio=StatusAssociado.INADIMPLENTE, status_fatura=StatusFatura.ATRASADA
    )
    await _outra_fatura(db_session, socio, "2026-10", vencimento_outra, status_outra)

    await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
    )

    await db_session.refresh(socio)
    assert socio.status == StatusAssociado.INADIMPLENTE


async def test_baixa_enfileira_recibo_renderizado_com_prioridade_alta(db_session, fila, provider):
    socio, fatura = await _cenario(db_session)
    await fila.enqueue(phone="5575988880000", message="lembrete normal", priority=MessagePriority.NORMAL)

    await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
    )
    assert fila.qsize == 2

    # Prioridade alta: o recibo sai antes do lembrete enfileirado anteriormente
    await fila.process_one()
    primeira = provider.sent_messages[0]
    assert primeira["phone"] == "5575999990001"
    assert primeira["message"] == (
        "Recibo Joana Prado: total R$ 1.220,00 (base R$ 1.150,00, 10 usados, 2 extras) "
        "venc 10/11/2026 pix financeiro@clubmaravilha.com.br"
    )


async def test_recibo_grava_log_mensagem_somente_quando_enviado(db_session, fila):
    socio, fatura = await _cenario(db_session)

    await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
    )
    async with TestingSessionLocal() as s:
        assert (await s.execute(select(LogMensagem))).scalars().all() == []

    await fila.process_one()

    async with TestingSessionLocal() as s:
        logs = list((await s.execute(select(LogMensagem))).scalars().all())
    assert len(logs) == 1
    log = logs[0]
    assert log.etapa == EtapaRegua.RECIBO
    assert log.status == StatusEnvio.SUCESSO
    assert log.fatura_id == fatura.id
    assert log.associado_id == socio.id
    assert log.destinatario == "5575999990001"
    assert log.mensagem.startswith("Recibo Joana Prado: total R$ 1.220,00")


async def test_baixa_usa_template_recibo_padrao_sem_prefixo_duplicado(db_session, fila, provider):
    _, fatura = await _cenario(db_session)
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    from app.models.configuracao import TEMPLATE_RECIBO_PADRAO
    cfg.template_recibo = TEMPLATE_RECIBO_PADRAO
    await db_session.commit()

    await FaturaService(db_session, queue_service=fila).baixa_manual(
        fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
    )
    await fila.process_one()

    mensagem = provider.sent_messages[0]["message"]
    assert "Joana Prado" in mensagem
    assert "R$ 1.220,00" in mensagem
    assert "R$ R$" not in mensagem


async def test_segunda_baixa_sequencial_nao_gera_segundo_recibo(db_session, fila):
    _, fatura = await _cenario(db_session)
    service = FaturaService(db_session, queue_service=fila)

    await service.baixa_manual(fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX))
    with pytest.raises(HTTPException) as exc:
        await service.baixa_manual(fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX))

    assert exc.value.status_code == 409
    assert fila.qsize == 1


async def test_baixas_concorrentes_em_sessoes_distintas_geram_um_unico_recibo(db_session, fila):
    import asyncio

    _, fatura = await _cenario(db_session)

    async def _baixar():
        async with TestingSessionLocal() as sessao:
            try:
                await FaturaService(sessao, queue_service=fila).baixa_manual(
                    fatura.id, FaturaBaixaManual(forma_pagamento=FormaPagamento.PIX)
                )
                return 200
            except HTTPException as exc:
                await sessao.rollback()
                return exc.status_code

    codigos = await asyncio.gather(_baixar(), _baixar())

    assert sorted(codigos) == [200, 409]
    assert fila.qsize == 1
