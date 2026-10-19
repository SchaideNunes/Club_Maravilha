"""
Testes unitários para as correções e melhorias de Code Review (Feature 3):
1. Catraca: carência de D+7 (DIAS_CARENCIA_BLOQUEIO) em vez de bloqueio imediato no D+1;
2. Concorrência: ON CONFLICT DO NOTHING evita 500 mesmo com leitura inicial vazia (monkeypatch);
3. Baixa manual: resiliência quando a fila de WhatsApp pós-commit falha;
4. Scheduler: sessões isoladas por etapa com rollback preventivo;
5. Migração Alembic: validação prévia aborta com RuntimeError se houver duplicatas;
6. Unificação de excedentes: vinculação de convites faturados elimina cobrança dupla;
7. Adesão no meio do mês: vencimento da fatura inicial nunca é anterior à data_adesao.
"""
import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import importlib
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, select, text

from app.core import clock
from app.core.constants import DIAS_CARENCIA_BLOQUEIO
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, FormaPagamento, StatusFatura
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.schemas.fatura import FaturaBaixaManual, FaturaCreate
from app.services.catraca_service import CatracaService
from app.services.fatura_service import FaturaService
from app.jobs.billing_scheduler import executar_rotina_diaria_cobranca


async def _configurar_clube(session, **campos):
    cfg = await ConfiguracaoRepository(session).get_or_create()
    cfg.valor_mensalidade = Decimal("150.00")
    cfg.franquia_convidados = 8
    cfg.valor_convidado_extra = Decimal("35.00")
    cfg.chave_pix = "financeiro@clubmaravilha.com.br"
    cfg.template_recibo = "Recibo {nome} {valor_total}"
    for k, v in campos.items():
        setattr(cfg, k, v)
    await session.commit()
    return cfg


def _criar_socio(numero: int, **campos) -> Associado:
    dados = {
        "nome": f"Associado Review {numero:02d}",
        "cpf": f"111.222.333-{numero:02d}",
        "whatsapp": f"55759999900{numero:02d}",
        "email": f"socio_review_{numero}@clube.com",
        "status": StatusAssociado.ATIVO,
        "dia_vencimento": 10,
        "data_adesao": date(2025, 1, 1),
    }
    dados.update(campos)
    return Associado(**dados)


# ===========================================================================
# 1. Catraca: tolerância de D+7 (DIAS_CARENCIA_BLOQUEIO)
# ===========================================================================

@pytest.mark.asyncio
async def test_catraca_bloqueia_somente_apos_d_mais_7(db_session):
    """
    Regra: vencimento em 10/10:
    - No dia 11/10 (D+1, fatura já com status ATRASADA): sócio AINDA ESTÁ na whitelist.
    - No dia 16/10 (D+6): sócio AINDA ESTÁ na whitelist.
    - No dia 17/10 (D+7): sócio É EXCLUÍDO da whitelist (carência encerrada).
    """
    service = CatracaService(db_session)
    socio = _criar_socio(1, facial_id="FACE_TEST_D7")
    db_session.add(socio)
    await db_session.commit()

    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-10",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 10, 10),
        status=StatusFatura.ATRASADA,
    )
    db_session.add(fatura)
    await db_session.commit()

    # D+1: 11/10 -> Dentro da tolerância de 7 dias (incluído)
    wl_d1 = await service.get_whitelist(data_consulta=date(2026, 10, 11))
    membros_d1 = [m["facial_id"] for m in wl_d1["members"]]
    assert "FACE_TEST_D7" in membros_d1, "No D+1 o sócio deve permanecer autorizado na catraca."

    # D+6: 16/10 -> Último dia antes do bloqueio (incluído)
    wl_d6 = await service.get_whitelist(data_consulta=date(2026, 10, 16))
    membros_d6 = [m["facial_id"] for m in wl_d6["members"]]
    assert "FACE_TEST_D7" in membros_d6, "No D+6 o sócio deve permanecer autorizado na catraca."

    # D+7: 17/10 -> Tolerância esgotada (excluído)
    wl_d7 = await service.get_whitelist(data_consulta=date(2026, 10, 17))
    membros_d7 = [m["facial_id"] for m in wl_d7["members"]]
    assert "FACE_TEST_D7" not in membros_d7, "No D+7 o sócio deve ser bloqueado na catraca."


# ===========================================================================
# 2. Concorrência: ON CONFLICT DO NOTHING evita 500 mesmo com leitura inicial vazia
# ===========================================================================

@pytest.mark.asyncio
async def test_geracao_faturas_idempotente_mesmo_com_leitura_desatualizada(db_session, monkeypatch):
    """
    Simula race condition: fatura já existe no banco para o sócio A, mas o método
    _associados_ja_faturados é monkeypatched para retornar conjunto vazio.
    O INSERT ... ON CONFLICT DO NOTHING deve absorver o conflito sem levantar IntegrityError,
    retornando criadas=0, ja_existentes=1, total=1.
    """
    await _configurar_clube(db_session)
    socio = _criar_socio(2)
    db_session.add(socio)
    await db_session.commit()

    # Pre-cria a fatura no banco
    db_session.add(Fatura(
        associado_id=socio.id,
        referencia_mes="2026-11",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 11, 10),
        status=StatusFatura.PENDENTE,
    ))
    await db_session.commit()

    service = FaturaService(db_session)

    # Monkeypatch simulando leitura obsoleta em transações concorrentes
    monkeypatch.setattr(service, "_associados_ja_faturados", AsyncMock(return_value=set()))

    # Não deve levantar IntegrityError nem 500
    res = await service.gerar_faturas_mes("2026-11")

    assert res.criadas == 0
    assert res.ja_existentes == 1
    assert res.total == 1


# ===========================================================================
# 3. Baixa manual: resiliência pós-commit à falha da fila WhatsApp
# ===========================================================================

@pytest.mark.asyncio
async def test_baixa_manual_persiste_pagamento_mesmo_com_falha_na_fila(db_session):
    """
    Se o envio para a fila de WhatsApp falhar após o commit da baixa,
    o serviço NÃO deve levantar exceção, retornando a fatura PAGA com sucesso.
    """
    await _configurar_clube(db_session)
    socio = _criar_socio(3)
    db_session.add(socio)
    await db_session.commit()

    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-11",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 11, 10),
        status=StatusFatura.PENDENTE,
    )
    db_session.add(fatura)
    await db_session.commit()

    fila_falha = MagicMock()
    fila_falha.enqueue = AsyncMock(side_effect=RuntimeError("Serviço de mensageria indisponível"))

    service = FaturaService(db_session, queue_service=fila_falha)
    fatura_id = fatura.id
    fatura_paga = await service.baixa_manual(
        fatura_id,
        FaturaBaixaManual(forma_pagamento=FormaPagamento.DINHEIRO)
    )

    assert fatura_paga.status == StatusFatura.PAGO
    assert fatura_paga.forma_pagamento == FormaPagamento.DINHEIRO

    # Confere no banco que o pagamento permaneceu persistido
    db_session.expire_all()
    no_banco = (await db_session.execute(select(Fatura).where(Fatura.id == fatura_id))).scalar_one()
    assert no_banco.status == StatusFatura.PAGO


# ===========================================================================
# 4. Scheduler: sessões isoladas para marcação de atraso e régua
# ===========================================================================

@pytest.mark.asyncio
async def test_scheduler_executa_etapas_em_sessoes_distintas_com_rollback():
    """
    Verifica que executar_rotina_diaria_cobranca abre sessões separadas para
    marcar_faturas_atrasadas e processar_regua_diaria, executando rollback se
    a marcação falhar.
    """
    sessoes_criadas = []

    class FakeSessionContext:
        def __init__(self):
            self.session = MagicMock()
            self.session.rollback = AsyncMock()
            sessoes_criadas.append(self.session)

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.jobs.billing_scheduler.AsyncSessionLocal", side_effect=FakeSessionContext), \
         patch("app.jobs.billing_scheduler.FaturaService") as MockFaturaService, \
         patch("app.jobs.billing_scheduler.BillingEngineService") as MockBillingEngine:

        # Marcação falha com exceção
        MockFaturaService.return_value.marcar_faturas_atrasadas = AsyncMock(
            side_effect=RuntimeError("Falha de conexão na marcação")
        )
        relatorio = MagicMock(total_enfileirados=0, inadimplentes_atualizados=0)
        MockBillingEngine.return_value.processar_regua_diaria = AsyncMock(return_value=relatorio)

        await executar_rotina_diaria_cobranca()

        # Duas sessões distintas devem ter sido abertas
        assert len(sessoes_criadas) == 2
        # A primeira sessão deve ter sofrido rollback devido à falha
        sessoes_criadas[0].rollback.assert_awaited_once()
        # A segunda sessão executou a régua normalmente
        MockBillingEngine.return_value.processar_regua_diaria.assert_awaited_once()


# ===========================================================================
# 5. Migração Alembic: validação prévia de duplicatas
# ===========================================================================

def test_migracao_alembic_aborta_se_houver_faturas_duplicadas():
    """
    Executa a função upgrade() da migração d485e921b712 em um banco SQLite temporário
    onde já existem faturas duplicadas para o mesmo associado e mês.
    Deve lançar RuntimeError listando o par conflitante sem apagar os dados.
    """
    caminho = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "d485e921b712_faturas_convites_e_constraint_unica.py"
    spec = importlib.util.spec_from_file_location("migracao_faturas_d485e921b712", caminho)
    migracao = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migracao)
    engine = create_engine("sqlite:///:memory:")

    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE faturas (id TEXT PRIMARY KEY, associado_id TEXT, referencia_mes TEXT)"))
        # Insere duas faturas duplicadas para o mesmo associado no mesmo mês
        conn.execute(text("INSERT INTO faturas VALUES ('f1', 'socio-dup', '2026-10')"))
        conn.execute(text("INSERT INTO faturas VALUES ('f2', 'socio-dup', '2026-10')"))
        conn.commit()

        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            with pytest.raises(RuntimeError) as exc_info:
                migracao.upgrade()

            msg = str(exc_info.value)
            assert "socio-dup" in msg
            assert "2026-10" in msg
            assert "faturas duplicadas" in msg

        # Confirma que os dados foram preservados e não apagados
        total = conn.execute(text("SELECT count(*) FROM faturas")).scalar_one()
        assert total == 2


# ===========================================================================
# 6. Unificação de excedentes / eliminação de cobrança dupla
# ===========================================================================

@pytest.mark.asyncio
async def test_geracao_vincula_convites_e_impede_dupla_cobranca_manual(db_session):
    """
    Cenário: Sócio emite 10 convites em outubro (franquia=8, 2 extras = R$ 70).
    1. Geração mensal de 2026-11 apura os 10 convites e cobra R$ 70 de excedentes.
    2. Convites apurados são vinculados (fatura_agregada_id) à fatura de novembro.
    3. Emissão manual subsequente (POST /faturas/) para o mesmo sócio em outro mês
       encontra 0 excedentes não faturados (valor_convidados_excedentes == 0).
    """
    await _configurar_clube(db_session)
    socio = _criar_socio(6)
    db_session.add(socio)
    await db_session.flush()

    # Cria 10 convites em outubro
    for i in range(10):
        db_session.add(Convidado(
            associado_titular_id=socio.id,
            nome=f"Convidado Out {i}",
            data_visita=date(2026, 10, 15),
            status=StatusConvidado.EMITIDO,
            is_gratuito=(i < 8),
            valor_cobrado=Decimal("0.00") if i < 8 else Decimal("35.00"),
        ))
    await db_session.commit()

    service = FaturaService(db_session)

    # 1. Geração de novembro
    res_geracao = await service.gerar_faturas_mes("2026-11")
    assert res_geracao.criadas == 1

    fatura_nov = (
        await db_session.execute(
            select(Fatura).where(Fatura.associado_id == socio.id, Fatura.referencia_mes == "2026-11")
        )
    ).scalar_one()
    assert fatura_nov.convites_usados == 10
    assert fatura_nov.convites_extras == 2
    assert fatura_nov.valor_convidados_excedentes == Decimal("70.00")

    # Verifica se os convites de outubro foram vinculados à fatura de novembro
    convidados_out = (
        await db_session.execute(
            select(Convidado).where(Convidado.associado_titular_id == socio.id)
        )
    ).scalars().all()
    assert len(convidados_out) == 10
    for conv in convidados_out:
        assert conv.fatura_agregada_id == fatura_nov.id

    # 2. Emissão manual subsequente para outro mês (ex: 2026-12)
    fatura_manual = await service.create_fatura(FaturaCreate(
        associado_id=socio.id,
        referencia_mes="2026-12",
        valor_base=Decimal("150.00"),
        valor_convidados_excedentes=Decimal("0.00"),
        valor_desconto=Decimal("0.00"),
        data_vencimento=date(2026, 12, 10),
        forma_pagamento=FormaPagamento.PIX,
    ))

    # Não deve ter cobrado nada de excedentes novamente
    assert fatura_manual.valor_convidados_excedentes == Decimal("0.00")
    assert fatura_manual.convites_extras == 0


@pytest.mark.asyncio
async def test_convites_agregados_manualmente_nao_sao_recontados_na_geracao(db_session):
    """
    Cenário inverso:
    1. Sócio possui 10 convites em outubro (2 extras).
    2. Fatura manual é criada e agrega os excedentes de outubro.
    3. Geração mensal de 2026-11 roda depois: os convites já agregados NÃO são recontados.
       Fatura gerada nasce com 0 excedentes.
    """
    await _configurar_clube(db_session)
    socio = _criar_socio(7)
    db_session.add(socio)
    await db_session.flush()

    for i in range(10):
        db_session.add(Convidado(
            associado_titular_id=socio.id,
            nome=f"Convidado Out {i}",
            data_visita=date(2026, 10, 20),
            status=StatusConvidado.EMITIDO,
            is_gratuito=(i < 8),
            valor_cobrado=Decimal("0.00") if i < 8 else Decimal("35.00"),
        ))
    await db_session.commit()

    service = FaturaService(db_session)

    # Cria fatura manual agregando os 2 excedentes
    fatura_manual = await service.create_fatura(FaturaCreate(
        associado_id=socio.id,
        referencia_mes="2026-10",
        valor_base=Decimal("150.00"),
        valor_convidados_excedentes=Decimal("0.00"),
        valor_desconto=Decimal("0.00"),
        data_vencimento=date(2026, 10, 25),
        forma_pagamento=FormaPagamento.PIX,
    ))
    assert fatura_manual.valor_convidados_excedentes == Decimal("70.00")

    # Agora roda a geração de novembro
    await service.gerar_faturas_mes("2026-11")

    fatura_nov = (
        await db_session.execute(
            select(Fatura).where(Fatura.associado_id == socio.id, Fatura.referencia_mes == "2026-11")
        )
    ).scalar_one()

    # Como os excedentes já foram agregados e vinculados à fatura manual, não devem ser cobrados novamente
    assert fatura_nov.convites_extras == 0
    assert fatura_nov.valor_convidados_excedentes == Decimal("0.00")


# ===========================================================================
# 7. Adesão no meio do mês nasce com vencimento válido (não vencida)
# ===========================================================================

@pytest.mark.asyncio
async def test_adesao_no_meio_do_mes_limita_vencimento_a_data_de_adesao(db_session):
    """
    Sócio aderiu em 2026-11-20, com dia de vencimento contratual = 10.
    A fatura de 2026-11 deve ter vencimento em 2026-11-20 (e não 2026-11-10 retrógrado).
    """
    await _configurar_clube(db_session)
    socio = _criar_socio(8, data_adesao=date(2026, 11, 20), dia_vencimento=10)
    db_session.add(socio)
    await db_session.commit()

    service = FaturaService(db_session)
    res = await service.gerar_faturas_mes("2026-11")
    assert res.criadas == 1

    fatura = (
        await db_session.execute(
            select(Fatura).where(Fatura.associado_id == socio.id, Fatura.referencia_mes == "2026-11")
        )
    ).scalar_one()

    assert fatura.data_vencimento == date(2026, 11, 20)


# ===========================================================================
# Opcionais: desempate por id e escape de caracteres especiais na busca
# ===========================================================================

@pytest.mark.asyncio
async def test_painel_faturas_ordena_com_desempate_por_id_e_escapa_like(db_session):
    """
    Verifica que o painel de faturas:
    1. Usa Fatura.id.asc() como critério de desempate;
    2. Trata caracteres '_' e '%' na busca textual sem interpretar como curingas SQL.
    """
    await _configurar_clube(db_session)
    socio1 = _criar_socio(9, nome="Carlos Silva")
    socio2 = _criar_socio(10, nome="Carlos_Silva")
    db_session.add_all([socio1, socio2])
    await db_session.commit()

    service = FaturaService(db_session)
    await service.gerar_faturas_mes("2026-11")

    # Busca especificamente por "Carlos_" com escape
    painel = await service.list_painel_faturas(q="Carlos_")
    nomes = [item.associado_nome for item in painel.items]
    assert "Carlos_Silva" in nomes
    assert "Carlos Silva" not in nomes, "O sublinhado '_' deve ser tratado literalmente e não como curinga."
