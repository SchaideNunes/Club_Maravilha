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


def test_associado_model_defaults():
    """Valida instanciação e valores padrão do modelo Associado."""
    associado = Associado(
        nome="João da Silva",
        cpf="111.222.333-44",
        whatsapp="+5511988887777",
        email="joao@maravilha.com"
    )
    assert associado.nome == "João da Silva"
    assert associado.cpf == "111.222.333-44"
    assert associado.status == StatusAssociado.ATIVO
    assert associado.limite_reservas_ativas == 2
    assert "João da Silva" in repr(associado)


def test_fatura_model_defaults():
    """Valida valores monetários e status da Fatura."""
    fatura = Fatura(
        associado_id=uuid.uuid4(),
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_convidados_excedentes=Decimal("35.00"),
        valor_desconto=Decimal("0.00"),
        valor_total=Decimal("185.00"),
        data_vencimento=date(2026, 9, 10),
    )
    assert fatura.valor_total == Decimal("185.00")
    assert fatura.status == StatusFatura.PENDENTE
    assert fatura.forma_pagamento == FormaPagamento.PIX


def test_agendamento_model_defaults():
    """Valida atributos do Agendamento de Quadra."""
    inicio = datetime.now(timezone.utc)
    fim = datetime.now(timezone.utc)
    agendamento = AgendamentoQuadra(
        associado_id=uuid.uuid4(),
        quadra=TipoQuadra.TENIS_1,
        data_inicio=inicio,
        data_fim=fim
    )
    assert agendamento.quadra == TipoQuadra.TENIS_1
    assert agendamento.status == StatusAgendamento.CONFIRMADO


def test_convidado_model_token_and_defaults():
    """Valida geração automática de token QR Code e regra inicial de gratuidade."""
    token = generate_qr_token()
    assert len(token) == 64
    
    convidado = Convidado(
        associado_titular_id=uuid.uuid4(),
        nome="Lucas Andrade",
        data_visita=date(2026, 9, 20),
        qr_code_token=token
    )
    assert convidado.is_gratuito is True
    assert convidado.valor_cobrado == Decimal("0.00")
    assert convidado.status == StatusConvidado.EMITIDO
