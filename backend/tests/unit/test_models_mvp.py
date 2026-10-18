"""
Feature 1 (MVP) - Testes dos modelos SQLAlchemy: Associado, Fatura, Convidado,
Configuracao (singleton) e LogMensagem, com persistência real em SQLite.

Contratos definidos aqui (a implementar):
- app.models.associado.Associado.dia_vencimento (int, default settings.DIA_VENCIMENTO_PADRAO)
- Associado.contar_convidados_no_mes(ano, mes) -> int  (ignora convidados CANCELADO)
- Associado.convidados_usados_mes (property, mês corrente; 0 se a relação não estiver carregada,
  nunca dispara lazy-load/IO)
- app.models.fatura.StatusFatura = PENDENTE | ATRASADA | PAGO | CANCELADO (sem VENCIDO)
- app.models.fatura.FormaPagamento contém PIX, CARTAO, DINHEIRO
- Fatura.calcular_valor_total() -> Decimal (valor_base + valor_convidados_excedentes - valor_desconto)
- Fatura.lembretes_ativos (property) -> False quando PAGO ou CANCELADO
- app.models.configuracao.Configuracao (tabela "configuracoes", id int singleton = 1)
- Configuracao.calcular_valor_excedentes(convidados_usados: int) -> Decimal
- app.models.log_mensagem.LogMensagem (tabela "logs_mensagens"), EtapaRegua, StatusEnvio
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.associado import Associado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura


def _novo_associado(sufixo: str = "1", **kwargs) -> Associado:
    return Associado(
        nome=f"Associado MVP {sufixo}",
        cpf=f"000.000.000-{sufixo.zfill(2)}",
        whatsapp="5575999999999",
        email=f"mvp{sufixo}@maravilha.com",
        **kwargs,
    )


# ------------------------------------------------------------------------------
# Associado
# ------------------------------------------------------------------------------
async def test_associado_dia_vencimento_default_vem_de_settings(db_session):
    associado = _novo_associado("11")
    db_session.add(associado)
    await db_session.flush()

    assert associado.dia_vencimento == settings.DIA_VENCIMENTO_PADRAO


async def test_associado_dia_vencimento_customizado_persiste(db_session):
    associado = _novo_associado("12", dia_vencimento=25)
    db_session.add(associado)
    await db_session.commit()

    lido = (
        await db_session.execute(select(Associado).where(Associado.id == associado.id))
    ).scalar_one()
    assert lido.dia_vencimento == 25


async def test_associado_contar_convidados_no_mes_ignora_outros_meses_e_cancelados(db_session):
    associado = _novo_associado("13")
    db_session.add(associado)
    await db_session.flush()

    db_session.add_all([
        Convidado(associado_titular_id=associado.id, nome="Conv Out 1", data_visita=date(2026, 10, 1)),
        Convidado(associado_titular_id=associado.id, nome="Conv Out 2", data_visita=date(2026, 10, 31)),
        Convidado(
            associado_titular_id=associado.id,
            nome="Conv Out Cancelado",
            data_visita=date(2026, 10, 15),
            status=StatusConvidado.CANCELADO,
        ),
        Convidado(associado_titular_id=associado.id, nome="Conv Setembro", data_visita=date(2026, 9, 30)),
        Convidado(associado_titular_id=associado.id, nome="Conv Novembro", data_visita=date(2026, 11, 1)),
    ])
    await db_session.commit()

    carregado = (
        await db_session.execute(
            select(Associado)
            .options(selectinload(Associado.convidados))
            .where(Associado.id == associado.id)
        )
    ).scalar_one()

    assert carregado.contar_convidados_no_mes(2026, 10) == 2
    assert carregado.contar_convidados_no_mes(2026, 9) == 1
    assert carregado.contar_convidados_no_mes(2026, 12) == 0


async def test_associado_convidados_usados_mes_usa_mes_corrente(db_session):
    hoje = date.today()
    associado = _novo_associado("14")
    db_session.add(associado)
    await db_session.flush()
    db_session.add_all([
        Convidado(associado_titular_id=associado.id, nome="Conv Hoje 1", data_visita=hoje),
        Convidado(associado_titular_id=associado.id, nome="Conv Hoje 2", data_visita=hoje),
        Convidado(associado_titular_id=associado.id, nome="Conv Hoje 3", data_visita=hoje),
    ])
    await db_session.commit()

    carregado = (
        await db_session.execute(
            select(Associado)
            .options(selectinload(Associado.convidados))
            .where(Associado.id == associado.id)
        )
    ).scalar_one()
    assert carregado.convidados_usados_mes == 3


async def test_associado_convidados_usados_mes_nao_dispara_lazy_load(db_session):
    """Sem a relação carregada, a property deve devolver 0 (sem IO/MissingGreenlet)."""
    associado = _novo_associado("15")
    db_session.add(associado)
    await db_session.commit()
    db_session.expunge_all()

    lido = (
        await db_session.execute(select(Associado).where(Associado.id == associado.id))
    ).scalar_one()
    assert lido.convidados_usados_mes == 0


# ------------------------------------------------------------------------------
# Fatura
# ------------------------------------------------------------------------------
def test_status_fatura_enum_mvp():
    assert {s.value for s in StatusFatura} == {"PENDENTE", "ATRASADA", "PAGO", "CANCELADO"}
    assert not hasattr(StatusFatura, "VENCIDO")


def test_forma_pagamento_aceita_pix_cartao_dinheiro():
    assert FormaPagamento("PIX") == FormaPagamento.PIX
    assert FormaPagamento("CARTAO") == FormaPagamento.CARTAO
    assert FormaPagamento("DINHEIRO") == FormaPagamento.DINHEIRO


def test_fatura_calcular_valor_total():
    fatura = Fatura(
        valor_base=Decimal("150.00"),
        valor_convidados_excedentes=Decimal("70.00"),
        valor_desconto=Decimal("20.00"),
    )
    assert fatura.calcular_valor_total() == Decimal("200.00")


def test_fatura_calcular_valor_total_sem_excedentes_e_desconto_explicitos():
    fatura = Fatura(valor_base=Decimal("150.00"))
    assert fatura.calcular_valor_total() == Decimal("150.00")


@pytest.mark.parametrize(
    "status,esperado",
    [
        ("PENDENTE", True),
        ("ATRASADA", True),
        ("PAGO", False),
        ("CANCELADO", False),
    ],
)
def test_fatura_lembretes_ativos_suspensos_quando_paga_ou_cancelada(status, esperado):
    fatura = Fatura(valor_base=Decimal("150.00"), status=StatusFatura(status))
    assert fatura.lembretes_ativos is esperado


async def test_fatura_baixa_manual_persiste(db_session):
    associado = _novo_associado("21")
    db_session.add(associado)
    await db_session.flush()

    pago_em = datetime(2026, 10, 12, 14, 30, tzinfo=timezone.utc)
    fatura = Fatura(
        associado_id=associado.id,
        referencia_mes="2026-10",
        valor_base=Decimal("150.00"),
        valor_convidados_excedentes=Decimal("35.00"),
        valor_desconto=Decimal("0.00"),
        valor_total=Decimal("185.00"),
        data_vencimento=date(2026, 10, 10),
        status=StatusFatura.ATRASADA,
    )
    db_session.add(fatura)
    await db_session.commit()

    fatura.status = StatusFatura.PAGO
    fatura.forma_pagamento = FormaPagamento.DINHEIRO
    fatura.data_pagamento = pago_em
    await db_session.commit()
    db_session.expunge_all()

    lida = (await db_session.execute(select(Fatura).where(Fatura.id == fatura.id))).scalar_one()
    assert lida.status == StatusFatura.PAGO
    assert lida.forma_pagamento == FormaPagamento.DINHEIRO
    assert lida.data_pagamento is not None
    assert lida.valor_total == lida.calcular_valor_total() == Decimal("185.00")
    assert lida.lembretes_ativos is False


# ------------------------------------------------------------------------------
# Configuracao (singleton)
# ------------------------------------------------------------------------------
async def test_configuracao_defaults_e_singleton(db_session):
    from app.models.configuracao import Configuracao

    assert Configuracao.__tablename__ == "configuracoes"

    cfg = Configuracao()
    db_session.add(cfg)
    await db_session.commit()
    db_session.expunge_all()

    lida = (await db_session.execute(select(Configuracao))).scalar_one()
    assert lida.id == 1
    assert lida.valor_mensalidade == Decimal("150.00")
    assert lida.franquia_convidados == 8
    assert lida.valor_convidado_extra == Decimal("35.00")
    assert lida.horario_disparo == "08:00"
    assert lida.automacao_ativa is True
    assert hasattr(lida, "chave_pix")


TEMPLATES = (
    "template_d_menos_3",
    "template_d0",
    "template_recibo",
    "template_d_mais_3",
    "template_d_mais_7",
)


async def test_configuracao_templates_default_nao_vazios_com_variaveis(db_session):
    from app.models.configuracao import Configuracao

    cfg = Configuracao()
    db_session.add(cfg)
    await db_session.flush()

    for campo in TEMPLATES:
        valor = getattr(cfg, campo)
        assert isinstance(valor, str) and valor.strip(), f"{campo} deve ter default não vazio"
        assert "{nome}" in valor, f"{campo} deve conter a variável {{nome}}"

    assert "{vencimento}" in cfg.template_d_menos_3
    assert "{valor_total}" in cfg.template_d0
    assert "{chave_pix}" in cfg.template_d0
    assert "{valor_total}" in cfg.template_d_mais_3
    assert "{chave_pix}" in cfg.template_d_mais_7


async def test_configuracao_campos_editaveis_persistem(db_session):
    from app.models.configuracao import Configuracao

    cfg = Configuracao(
        valor_mensalidade=Decimal("180.00"),
        franquia_convidados=10,
        valor_convidado_extra=Decimal("40.00"),
        chave_pix="financeiro@clubmaravilha.com.br",
        horario_disparo="09:30",
        automacao_ativa=False,
        template_d0="Olá {nome}, sua fatura de {valor_total} vence hoje. Pix: {chave_pix}",
    )
    db_session.add(cfg)
    await db_session.commit()
    db_session.expunge_all()

    lida = (await db_session.execute(select(Configuracao))).scalar_one()
    assert lida.valor_mensalidade == Decimal("180.00")
    assert lida.franquia_convidados == 10
    assert lida.valor_convidado_extra == Decimal("40.00")
    assert lida.chave_pix == "financeiro@clubmaravilha.com.br"
    assert lida.horario_disparo == "09:30"
    assert lida.automacao_ativa is False
    assert lida.template_d0.startswith("Olá {nome}")


@pytest.mark.parametrize(
    "usados,esperado",
    [(0, Decimal("0.00")), (8, Decimal("0.00")), (9, Decimal("35.00")), (11, Decimal("105.00"))],
)
def test_configuracao_calcular_valor_excedentes(usados, esperado):
    from app.models.configuracao import Configuracao

    cfg = Configuracao(franquia_convidados=8, valor_convidado_extra=Decimal("35.00"))
    assert cfg.calcular_valor_excedentes(usados) == esperado


# ------------------------------------------------------------------------------
# LogMensagem
# ------------------------------------------------------------------------------
def test_enums_log_mensagem():
    from app.models.log_mensagem import EtapaRegua, StatusEnvio

    assert {e.value for e in EtapaRegua} == {
        "D_MENOS_3", "D0", "RECIBO", "D_MAIS_3", "D_MAIS_7", "AVULSO", "TESTE",
    }
    assert {s.value for s in StatusEnvio} == {"SUCESSO", "ERRO"}


async def test_log_mensagem_persiste_com_fks(db_session):
    from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio

    assert LogMensagem.__tablename__ == "logs_mensagens"

    associado = _novo_associado("31")
    db_session.add(associado)
    await db_session.flush()
    fatura = Fatura(
        associado_id=associado.id,
        referencia_mes="2026-10",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 10, 10),
    )
    db_session.add(fatura)
    await db_session.flush()

    log = LogMensagem(
        associado_id=associado.id,
        fatura_id=fatura.id,
        destinatario="5575999999999",
        etapa=EtapaRegua.D0,
        mensagem="Olá Associado MVP 31, sua fatura vence hoje.",
        status=StatusEnvio.SUCESSO,
    )
    db_session.add(log)
    await db_session.commit()
    db_session.expunge_all()

    lido = (await db_session.execute(select(LogMensagem))).scalar_one()
    assert isinstance(lido.id, uuid.UUID)
    assert lido.associado_id == associado.id
    assert lido.fatura_id == fatura.id
    assert lido.destinatario == "5575999999999"
    assert lido.etapa == EtapaRegua.D0
    assert lido.status == StatusEnvio.SUCESSO
    assert lido.erro is None
    assert isinstance(lido.enviado_em, datetime)


async def test_log_mensagem_sem_fks_com_erro(db_session):
    from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio

    log = LogMensagem(
        destinatario="5511988887777",
        etapa=EtapaRegua.TESTE,
        mensagem="Mensagem de teste do painel",
        status=StatusEnvio.ERRO,
        erro="Engine desconectado",
    )
    db_session.add(log)
    await db_session.commit()
    db_session.expunge_all()

    lido = (await db_session.execute(select(LogMensagem))).scalar_one()
    assert lido.associado_id is None
    assert lido.fatura_id is None
    assert lido.status == StatusEnvio.ERRO
    assert lido.erro == "Engine desconectado"
    assert lido.enviado_em is not None


# ------------------------------------------------------------------------------
# Exportação em app.models
# ------------------------------------------------------------------------------
def test_app_models_exporta_novos_modelos_e_enums():
    import app.models as models

    for nome in ("Configuracao", "LogMensagem", "EtapaRegua", "StatusEnvio"):
        assert hasattr(models, nome), f"app.models deve exportar {nome}"
        assert nome in models.__all__, f"{nome} deve constar em app.models.__all__"


def test_metadata_registra_novas_tabelas():
    import app.models as models

    tabelas = models.Base.metadata.tables
    assert "configuracoes" in tabelas
    assert "logs_mensagens" in tabelas
    assert "dia_vencimento" in tabelas["associados"].c
