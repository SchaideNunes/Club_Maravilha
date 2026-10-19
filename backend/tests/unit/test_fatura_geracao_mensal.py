"""
Testes unitários da geração de faturas mensais e da marcação de atraso (Feature 3).

Regras escolhidas (contrato):
1. Elegibilidade: TODO associado recebe a fatura do mês (ATIVO, INADIMPLENTE e BLOQUEADO).
   No sistema, INADIMPLENTE/BLOQUEADO são consequências financeiras (régua D+7), não
   desligamento: o vínculo continua e a mensalidade continua devida. Exceção: sócio cuja
   `data_adesao` é posterior ao último dia do mês de referência não é faturado nesse mês.
2. Vencimento: dia `dia_vencimento` do associado limitado ao último dia do mês
   (`calendar.monthrange`), ex.: 31 em fev/2026 -> 28/02/2026; 2028 (bissexto) -> 29/02.
3. Convidados: a fatura de referência AAAA-MM cobra os convidados do MÊS ANTERIOR
   (coerente com Fatura.valor_convidados_excedentes, "excedentes do mês anterior").
   convites_usados = convites não CANCELADOS com data_visita no mês anterior;
   convites_extras = max(0, convites_usados - franquia_convidados);
   valor_convidados_excedentes = convites_extras * valor_convidado_extra;
   valor_base = Configuracao.valor_mensalidade; valor_desconto = 0;
   valor_total = base + excedentes - desconto. Status inicial PENDENTE.
   `convites_usados` e `convites_extras` ficam gravados na fatura (colunas int, default 0).
4. Idempotência: UniqueConstraint `uq_faturas_associado_referencia_mes` em
   (associado_id, referencia_mes). Gerar de novo o mesmo mês não duplica; qualquer fatura já
   existente (inclusive CANCELADO) conta em `ja_existentes`.
5. Atraso: `FaturaService.marcar_faturas_atrasadas(data_referencia=None) -> int` muda
   PENDENTE com data_vencimento < data_referencia (default hoje_clube()) para ATRASADA;
   não mexe em PAGO/CANCELADO nem no status do associado.

API do serviço (app/services/fatura_service.py):
- calcular_data_vencimento(referencia_mes: str, dia_vencimento: int) -> date
- mes_anterior(referencia_mes: str) -> str
- FaturaService(session, queue_service=None)
- FaturaService.gerar_faturas_mes(referencia_mes: Optional[str] = None) -> GeracaoFaturasResponse
  (app/schemas/fatura.py: referencia_mes, criadas, ja_existentes, total = criadas + ja_existentes)
"""
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import UniqueConstraint, select
from sqlalchemy.exc import IntegrityError

from app.core import clock
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services.fatura_service import (
    FaturaService,
    calcular_data_vencimento,
    mes_anterior,
)

UQ_FATURA = "uq_faturas_associado_referencia_mes"


@pytest.fixture
def congelar_hoje(monkeypatch):
    """Fixa a data do clube (hoje_clube/agora_clube) em um dia conhecido."""
    def _congelar(dia: date) -> None:
        instante = datetime(dia.year, dia.month, dia.day, 12, 0, tzinfo=clock.get_clube_tz())
        monkeypatch.setattr(clock, "agora_clube", lambda: instante)
    return _congelar


async def _configurar(session, **campos):
    cfg = await ConfiguracaoRepository(session).get_or_create()
    cfg.valor_mensalidade = Decimal("150.00")
    cfg.franquia_convidados = 8
    cfg.valor_convidado_extra = Decimal("35.00")
    cfg.chave_pix = "financeiro@clubmaravilha.com.br"
    for nome, valor in campos.items():
        setattr(cfg, nome, valor)
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


def _convites(socio: Associado, quantidade: int, dia: date, status=StatusConvidado.EMITIDO):
    return [
        Convidado(
            associado_titular_id=socio.id,
            nome=f"Convidado {i}",
            data_visita=dia,
            status=status,
        )
        for i in range(quantidade)
    ]


async def _faturas(session):
    session.expire_all()
    return list((await session.execute(select(Fatura))).scalars().all())


# ---------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "referencia, dia, esperado",
    [
        ("2026-11", 10, date(2026, 11, 10)),
        ("2026-11", 31, date(2026, 11, 30)),
        ("2026-02", 31, date(2026, 2, 28)),
        ("2026-02", 29, date(2026, 2, 28)),
        ("2028-02", 31, date(2028, 2, 29)),
        ("2026-12", 31, date(2026, 12, 31)),
        ("2026-01", 1, date(2026, 1, 1)),
    ],
)
def test_calcular_data_vencimento_limita_ao_ultimo_dia_do_mes(referencia, dia, esperado):
    assert calcular_data_vencimento(referencia, dia) == esperado


@pytest.mark.parametrize(
    "referencia, esperado",
    [("2026-11", "2026-10"), ("2026-01", "2025-12"), ("2026-12", "2026-11")],
)
def test_mes_anterior(referencia, esperado):
    assert mes_anterior(referencia) == esperado


# ---------------------------------------------------------------------------
# Modelo / migração
# ---------------------------------------------------------------------------

def test_fatura_tem_constraint_unica_associado_referencia():
    constraints = [
        c for c in Fatura.__table__.constraints
        if isinstance(c, UniqueConstraint) and c.name == UQ_FATURA
    ]
    assert len(constraints) == 1
    assert [col.name for col in constraints[0].columns] == ["associado_id", "referencia_mes"]


def test_fatura_tem_colunas_de_convites():
    colunas = Fatura.__table__.columns
    for nome in ("convites_usados", "convites_extras"):
        assert nome in colunas
        assert colunas[nome].nullable is False


def test_migracao_alembic_cria_constraint_e_colunas_de_convites():
    versoes = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    conteudo = "\n".join(p.read_text(encoding="utf-8") for p in versoes.glob("*.py"))
    assert UQ_FATURA in conteudo
    assert "convites_usados" in conteudo
    assert "convites_extras" in conteudo


async def test_banco_rejeita_fatura_duplicada_no_mesmo_mes(db_session):
    socio = _socio(1)
    db_session.add(socio)
    await db_session.commit()
    for _ in range(2):
        db_session.add(Fatura(
            associado_id=socio.id,
            referencia_mes="2026-11",
            valor_base=Decimal("150.00"),
            valor_total=Decimal("150.00"),
            data_vencimento=date(2026, 11, 10),
        ))
    with pytest.raises(IntegrityError):
        await db_session.commit()


# ---------------------------------------------------------------------------
# Geração
# ---------------------------------------------------------------------------

async def test_gera_fatura_com_valores_vencimento_e_status(db_session):
    await _configurar(db_session)
    socio = _socio(1, dia_vencimento=15)
    db_session.add(socio)
    await db_session.commit()
    socio_id = socio.id

    resultado = await FaturaService(db_session).gerar_faturas_mes("2026-11")

    assert resultado.referencia_mes == "2026-11"
    assert (resultado.criadas, resultado.ja_existentes, resultado.total) == (1, 0, 1)
    [fatura] = await _faturas(db_session)
    assert fatura.associado_id == socio_id
    assert fatura.referencia_mes == "2026-11"
    assert fatura.status == StatusFatura.PENDENTE
    assert fatura.data_vencimento == date(2026, 11, 15)
    assert fatura.valor_base == Decimal("150.00")
    assert fatura.valor_convidados_excedentes == Decimal("0.00")
    assert fatura.valor_desconto == Decimal("0.00")
    assert fatura.valor_total == Decimal("150.00")
    assert fatura.convites_usados == 0
    assert fatura.convites_extras == 0


async def test_dia_31_em_fevereiro_vence_no_ultimo_dia(db_session):
    await _configurar(db_session)
    db_session.add(_socio(1, dia_vencimento=31))
    await db_session.commit()

    await FaturaService(db_session).gerar_faturas_mes("2026-02")

    [fatura] = await _faturas(db_session)
    assert fatura.data_vencimento == date(2026, 2, 28)


async def test_valores_vem_da_configuracao(db_session):
    await _configurar(
        db_session,
        valor_mensalidade=Decimal("199.90"),
        franquia_convidados=2,
        valor_convidado_extra=Decimal("40.00"),
    )
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    db_session.add_all(_convites(socio, 5, date(2026, 10, 3)))
    await db_session.commit()

    await FaturaService(db_session).gerar_faturas_mes("2026-11")

    [fatura] = await _faturas(db_session)
    assert fatura.valor_base == Decimal("199.90")
    assert fatura.convites_usados == 5
    assert fatura.convites_extras == 3
    assert fatura.valor_convidados_excedentes == Decimal("120.00")
    assert fatura.valor_total == Decimal("319.90")


async def test_excedentes_sao_do_mes_anterior_e_ignoram_cancelados(db_session):
    await _configurar(db_session)
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    db_session.add_all(
        _convites(socio, 10, date(2026, 10, 12))  # mês anterior: 10 válidos
        + _convites(socio, 3, date(2026, 10, 20), status=StatusConvidado.CANCELADO)  # não contam
        + _convites(socio, 4, date(2026, 11, 2))  # mês de referência: ficam para a fatura seguinte
        + _convites(socio, 6, date(2026, 9, 30))  # dois meses antes: não contam
    )
    await db_session.commit()

    await FaturaService(db_session).gerar_faturas_mes("2026-11")

    [fatura] = await _faturas(db_session)
    assert fatura.convites_usados == 10
    assert fatura.convites_extras == 2
    assert fatura.valor_convidados_excedentes == Decimal("70.00")
    assert fatura.valor_total == Decimal("220.00")


async def test_excedentes_de_dezembro_entram_na_fatura_de_janeiro(db_session):
    await _configurar(db_session)
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    db_session.add_all(_convites(socio, 9, date(2025, 12, 28)))
    await db_session.commit()

    await FaturaService(db_session).gerar_faturas_mes("2026-01")

    [fatura] = await _faturas(db_session)
    assert fatura.convites_usados == 9
    assert fatura.convites_extras == 1
    assert fatura.valor_total == Decimal("185.00")


async def test_franquia_exata_nao_gera_excedente(db_session):
    await _configurar(db_session)
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    db_session.add_all(_convites(socio, 8, date(2026, 10, 5)))
    await db_session.commit()

    await FaturaService(db_session).gerar_faturas_mes("2026-11")

    [fatura] = await _faturas(db_session)
    assert fatura.convites_usados == 8
    assert fatura.convites_extras == 0
    assert fatura.valor_convidados_excedentes == Decimal("0.00")


async def test_todos_os_status_recebem_fatura_mas_nao_quem_aderiu_depois(db_session):
    await _configurar(db_session)
    ativo = _socio(1, status=StatusAssociado.ATIVO)
    inadimplente = _socio(2, status=StatusAssociado.INADIMPLENTE)
    bloqueado = _socio(3, status=StatusAssociado.BLOQUEADO)
    aderiu_no_mes = _socio(4, data_adesao=date(2026, 11, 30))
    aderiu_depois = _socio(5, data_adesao=date(2026, 12, 1))
    db_session.add_all([ativo, inadimplente, bloqueado, aderiu_no_mes, aderiu_depois])
    await db_session.commit()

    esperados = {ativo.id, inadimplente.id, bloqueado.id, aderiu_no_mes.id}
    resultado = await FaturaService(db_session).gerar_faturas_mes("2026-11")

    assert (resultado.criadas, resultado.ja_existentes, resultado.total) == (4, 0, 4)
    faturados = {f.associado_id for f in await _faturas(db_session)}
    assert faturados == esperados


async def test_gerar_duas_vezes_nao_duplica(db_session):
    await _configurar(db_session)
    db_session.add_all([_socio(1), _socio(2), _socio(3)])
    await db_session.commit()
    service = FaturaService(db_session)

    primeira = await service.gerar_faturas_mes("2026-11")
    segunda = await service.gerar_faturas_mes("2026-11")

    assert (primeira.criadas, primeira.ja_existentes, primeira.total) == (3, 0, 3)
    assert (segunda.criadas, segunda.ja_existentes, segunda.total) == (0, 3, 3)
    assert len(await _faturas(db_session)) == 3


async def test_fatura_existente_cancelada_nao_e_recriada_e_novo_socio_e_faturado(db_session):
    await _configurar(db_session)
    antigo = _socio(1)
    db_session.add(antigo)
    await db_session.flush()
    db_session.add(Fatura(
        associado_id=antigo.id,
        referencia_mes="2026-11",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 11, 10),
        status=StatusFatura.CANCELADO,
    ))
    novo = _socio(2)
    db_session.add(novo)
    await db_session.commit()

    resultado = await FaturaService(db_session).gerar_faturas_mes("2026-11")

    assert (resultado.criadas, resultado.ja_existentes, resultado.total) == (1, 1, 2)
    antigo_id = antigo.id
    faturas = await _faturas(db_session)
    assert len(faturas) == 2
    assert {f.status for f in faturas if f.associado_id == antigo_id} == {StatusFatura.CANCELADO}


async def test_meses_diferentes_geram_faturas_independentes(db_session):
    await _configurar(db_session)
    db_session.add(_socio(1))
    await db_session.commit()
    service = FaturaService(db_session)

    await service.gerar_faturas_mes("2026-10")
    await service.gerar_faturas_mes("2026-11")

    assert sorted(f.referencia_mes for f in await _faturas(db_session)) == ["2026-10", "2026-11"]


async def test_referencia_padrao_e_o_mes_corrente_do_clube(db_session, congelar_hoje):
    congelar_hoje(date(2026, 11, 5))
    await _configurar(db_session)
    db_session.add(_socio(1))
    await db_session.commit()

    resultado = await FaturaService(db_session).gerar_faturas_mes()

    assert resultado.referencia_mes == "2026-11"
    [fatura] = await _faturas(db_session)
    assert fatura.referencia_mes == "2026-11"


@pytest.mark.parametrize("referencia", ["2026-13", "2026-00", "2026/11", "26-11", "abc"])
async def test_referencia_invalida_e_rejeitada(db_session, referencia):
    await _configurar(db_session)
    with pytest.raises(ValueError):
        await FaturaService(db_session).gerar_faturas_mes(referencia)


# ---------------------------------------------------------------------------
# Marcação de atraso
# ---------------------------------------------------------------------------

async def _fatura(session, socio, referencia, vencimento, status=StatusFatura.PENDENTE) -> Fatura:
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes=referencia,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=vencimento,
        status=status,
    )
    session.add(fatura)
    await session.flush()
    return fatura


async def test_marcar_atrasadas_somente_pendentes_vencidas(db_session):
    socios = [_socio(i) for i in range(1, 6)]
    db_session.add_all(socios)
    await db_session.flush()
    vencida = await _fatura(db_session, socios[0], "2026-10", date(2026, 10, 10))
    vence_hoje = await _fatura(db_session, socios[1], "2026-10", date(2026, 10, 19))
    futura = await _fatura(db_session, socios[2], "2026-10", date(2026, 10, 25))
    paga = await _fatura(db_session, socios[3], "2026-10", date(2026, 10, 1), StatusFatura.PAGO)
    cancelada = await _fatura(db_session, socios[4], "2026-10", date(2026, 10, 1), StatusFatura.CANCELADO)
    await db_session.commit()

    atualizadas = await FaturaService(db_session).marcar_faturas_atrasadas(date(2026, 10, 19))

    assert atualizadas == 1
    db_session.expire_all()
    status = {f.id: f.status for f in await _faturas(db_session)}
    assert status[vencida.id] == StatusFatura.ATRASADA
    assert status[vence_hoje.id] == StatusFatura.PENDENTE
    assert status[futura.id] == StatusFatura.PENDENTE
    assert status[paga.id] == StatusFatura.PAGO
    assert status[cancelada.id] == StatusFatura.CANCELADO


async def test_marcar_atrasadas_usa_hoje_clube_e_e_idempotente(db_session, congelar_hoje):
    congelar_hoje(date(2026, 11, 11))
    socio = _socio(1)
    db_session.add(socio)
    await db_session.flush()
    await _fatura(db_session, socio, "2026-11", date(2026, 11, 10))
    await db_session.commit()
    service = FaturaService(db_session)

    assert await service.marcar_faturas_atrasadas() == 1
    assert await service.marcar_faturas_atrasadas() == 0


async def test_marcar_atrasadas_nao_altera_status_do_associado(db_session):
    socio = _socio(1, status=StatusAssociado.ATIVO)
    db_session.add(socio)
    await db_session.flush()
    await _fatura(db_session, socio, "2026-10", date(2026, 10, 10))
    await db_session.commit()

    await FaturaService(db_session).marcar_faturas_atrasadas(date(2026, 10, 19))

    await db_session.refresh(socio)
    assert socio.status == StatusAssociado.ATIVO
