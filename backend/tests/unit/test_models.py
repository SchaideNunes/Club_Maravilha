"""
Testes unitários dos Modelos e Schemas do Club Maravilha.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
import pytest
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra
from app.models.convidado import Convidado, StatusConvidado, generate_qr_token


@pytest.mark.asyncio
async def test_associado_model_defaults(db_session):
    """Valida instanciação e valores padrão do modelo Associado."""
    associado = Associado(
        nome="João da Silva",
        cpf="111.222.333-44",
        whatsapp="+5511988887777",
        email="joao@maravilha.com"
    )
    db_session.add(associado)
    await db_session.flush()

    assert associado.nome == "João da Silva"
    assert associado.cpf == "111.222.333-44"
    assert associado.status == StatusAssociado.ATIVO
    assert associado.limite_reservas_ativas == 2
    assert "João da Silva" in repr(associado)


@pytest.mark.asyncio
async def test_fatura_model_defaults(db_session):
    """Valida valores monetários e status da Fatura."""
    associado = Associado(
        nome="Titular Teste",
        cpf="222.333.444-55",
        whatsapp="+5511988886666",
        email="titular@maravilha.com"
    )
    db_session.add(associado)
    await db_session.flush()

    fatura = Fatura(
        associado_id=associado.id,
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_convidados_excedentes=Decimal("35.00"),
        valor_desconto=Decimal("0.00"),
        valor_total=Decimal("185.00"),
        data_vencimento=date(2026, 9, 10),
    )
    db_session.add(fatura)
    await db_session.flush()

    assert fatura.valor_total == Decimal("185.00")
    assert fatura.status == StatusFatura.PENDENTE
    assert fatura.forma_pagamento == FormaPagamento.PIX


@pytest.mark.asyncio
async def test_agendamento_model_defaults(db_session):
    """Valida atributos do Agendamento de Quadra."""
    associado = Associado(
        nome="Jogador Teste",
        cpf="333.444.555-66",
        whatsapp="+5511988885555",
        email="jogador@maravilha.com"
    )
    db_session.add(associado)
    await db_session.flush()

    inicio = datetime.now(timezone.utc)
    fim = datetime.now(timezone.utc)
    agendamento = AgendamentoQuadra(
        associado_id=associado.id,
        quadra=TipoQuadra.TENIS_1,
        data_inicio=inicio,
        data_fim=fim
    )
    db_session.add(agendamento)
    await db_session.flush()

    assert agendamento.quadra == TipoQuadra.TENIS_1
    assert agendamento.status == StatusAgendamento.CONFIRMADO


@pytest.mark.asyncio
async def test_convidado_model_token_and_defaults(db_session):
    """Valida geração automática de token QR Code e regra inicial de gratuidade."""
    associado = Associado(
        nome="Titular Convidante",
        cpf="444.555.666-77",
        whatsapp="+5511988884444",
        email="convidante@maravilha.com"
    )
    db_session.add(associado)
    await db_session.flush()

    token = generate_qr_token()
    assert len(token) == 64
    
    convidado = Convidado(
        associado_titular_id=associado.id,
        nome="Lucas Andrade",
        data_visita=date(2026, 9, 20),
        qr_code_token=token
    )
    db_session.add(convidado)
    await db_session.flush()

    assert convidado.is_gratuito is True
    assert convidado.valor_cobrado == Decimal("0.00")
    assert convidado.status == StatusConvidado.EMITIDO
