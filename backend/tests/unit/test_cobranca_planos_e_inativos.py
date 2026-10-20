"""
Cadastro de Sócios - efeito de planos e da inativação na cobrança.

Regras:
1. Geração mensal: o valor_base da fatura é o valor do plano do sócio; sem plano, vale
   Configuracao.valor_mensalidade. Desativar o plano não muda o valor de quem já está nele.
2. Plano isento (valor 0): a fatura só é gerada se houver convidados excedentes a cobrar.
3. Sócios INATIVOS não recebem fatura nova.
4. Régua diária: não envia lembretes de faturas de sócios INATIVOS (dívidas antigas seguem em
   aberto, mas a cobrança passa a ser manual).
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.models.plano import Plano
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.billing_engine_service import BillingEngineService
from app.services.fatura_service import FaturaService
from app.services.whatsapp_queue_service import MessagePriority


async def _configurar(session):
    cfg = await ConfiguracaoRepository(session).get_or_create()
    cfg.valor_mensalidade = Decimal("150.00")
    cfg.franquia_convidados = 1
    cfg.valor_convidado_extra = Decimal("35.00")
    cfg.chave_pix = "pix@clube.com"
    cfg.template_d0 = "D0 {nome}"
    await session.commit()
    return cfg


def _socio(n: int, **campos) -> Associado:
    dados = dict(
        nome=f"Socio {n:02d}",
        cpf=f"000.000.{n:03d}-00",
        whatsapp=f"55759999900{n:02d}",
        email=f"socio{n}@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=10,
        data_adesao=date(2025, 1, 1),
    )
    dados.update(campos)
    return Associado(**dados)


async def _faturas_por_nome(session) -> dict:
    session.expire_all()
    linhas = await session.execute(select(Associado.nome, Fatura).join(Fatura, Fatura.associado_id == Associado.id))
    return {nome: fatura for nome, fatura in linhas.all()}


async def test_geracao_usa_valor_do_plano_e_padrao_sem_plano(db_session):
    await _configurar(db_session)
    familiar = Plano(nome="Familiar", valor_mensalidade=Decimal("220.00"))
    antigo = Plano(nome="Antigo", valor_mensalidade=Decimal("99.90"), ativo=False)
    db_session.add_all([familiar, antigo])
    await db_session.flush()
    db_session.add_all([
        _socio(1, plano_id=familiar.id),
        _socio(2),
        _socio(3, plano_id=antigo.id),
    ])
    await db_session.commit()

    await FaturaService(db_session).gerar_faturas_mes("2026-11")

    faturas = await _faturas_por_nome(db_session)
    assert faturas["Socio 01"].valor_base == Decimal("220.00")
    assert faturas["Socio 02"].valor_base == Decimal("150.00")
    assert faturas["Socio 03"].valor_base == Decimal("99.90")
    assert faturas["Socio 01"].valor_total == Decimal("220.00")


async def test_isento_so_gera_fatura_quando_ha_excedentes(db_session):
    await _configurar(db_session)
    remido = Plano(nome="Remido", valor_mensalidade=Decimal("0.00"))
    db_session.add(remido)
    await db_session.flush()
    sem_convites = _socio(1, plano_id=remido.id)
    com_excedente = _socio(2, plano_id=remido.id)
    db_session.add_all([sem_convites, com_excedente])
    await db_session.flush()
    # franquia = 1; dois convites em outubro => 1 excedente cobrado na fatura de novembro
    db_session.add_all([
        Convidado(associado_titular_id=com_excedente.id, nome=f"Visita {i}", data_visita=date(2026, 10, 5),
                  status=StatusConvidado.UTILIZADO)
        for i in range(2)
    ])
    await db_session.commit()

    resultado = await FaturaService(db_session).gerar_faturas_mes("2026-11")

    faturas = await _faturas_por_nome(db_session)
    assert "Socio 01" not in faturas
    assert faturas["Socio 02"].valor_base == Decimal("0.00")
    assert faturas["Socio 02"].valor_total == Decimal("35.00")
    assert resultado.criadas == 1


async def test_inativos_nao_recebem_fatura_nova(db_session):
    await _configurar(db_session)
    db_session.add_all([
        _socio(1),
        _socio(2, status=StatusAssociado.INATIVO),
        _socio(3, status=StatusAssociado.INADIMPLENTE),
    ])
    await db_session.commit()

    resultado = await FaturaService(db_session).gerar_faturas_mes("2026-11")

    assert set(await _faturas_por_nome(db_session)) == {"Socio 01", "Socio 03"}
    assert resultado.criadas == 2


class FilaFalsa:
    def __init__(self) -> None:
        self.telefones = []

    async def enqueue(self, phone, message, priority=MessagePriority.NORMAL, log_context=None) -> None:
        self.telefones.append(phone)


async def test_regua_nao_cobra_socio_inativo(db_session):
    await _configurar(db_session)
    hoje = date(2026, 9, 10)
    ativo = _socio(1)
    inativo = _socio(2, status=StatusAssociado.INATIVO)
    db_session.add_all([ativo, inativo])
    await db_session.flush()
    for socio in (ativo, inativo):
        db_session.add(Fatura(associado_id=socio.id, referencia_mes="2026-09", valor_base=Decimal("150.00"),
                              valor_total=Decimal("150.00"), data_vencimento=hoje, status=StatusFatura.PENDENTE))
    await db_session.commit()

    fila = FilaFalsa()
    report = await BillingEngineService(session=db_session, queue_service=fila).processar_regua_diaria(
        data_referencia=hoje
    )

    assert fila.telefones == [ativo.whatsapp]
    assert report.d_zero_enviados == 1


async def test_inativo_com_divida_antiga_nao_vira_inadimplente(db_session):
    await _configurar(db_session)
    hoje = date(2026, 9, 10)
    inativo = _socio(1, status=StatusAssociado.INATIVO)
    db_session.add(inativo)
    await db_session.flush()
    inativo_id = inativo.id
    db_session.add(Fatura(associado_id=inativo_id, referencia_mes="2026-07", valor_base=Decimal("150.00"),
                          valor_total=Decimal("150.00"), data_vencimento=hoje - timedelta(days=60),
                          status=StatusFatura.ATRASADA))
    await db_session.commit()

    await BillingEngineService(session=db_session, queue_service=FilaFalsa()).processar_regua_diaria(
        data_referencia=hoje
    )

    status_atual = await db_session.scalar(select(Associado.status).where(Associado.id == inativo_id))
    assert status_atual == StatusAssociado.INATIVO
