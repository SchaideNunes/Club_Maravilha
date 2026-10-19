"""
Testes opcionais contra um PostgreSQL real (pulados quando TEST_POSTGRES_URL não está definida).

Cobrem o que o SQLite dos testes não consegue provar: a semântica do SQL de PostgreSQL usado na
migração (higienização do WhatsApp legado) e a atomicidade do get_or_create da Configuracao sob
concorrência. Tudo é criado dentro de um schema temporário, removido ao final.

Exemplo de uso (use um banco de desenvolvimento ou descartável):
    TEST_POSTGRES_URL=postgresql://postgres@127.0.0.1:5432/postgres pytest tests/integration/test_postgres_opcional.py
"""
import asyncio
import importlib.util
import os
import uuid
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.configuracao import Configuracao
from app.repositories.configuracao_repository import ConfiguracaoRepository

POSTGRES_URL = os.environ.get("TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="defina TEST_POSTGRES_URL para rodar os testes contra um PostgreSQL real",
)

MIGRACAO_MVP = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "c2749453ba07_mvp_configuracoes_logs_mensagens_dia_vencimento.py"
)

WHATSAPP_LEGADO = [
    ("+55 (75) 99999-9999", "5575999999999"),
    ("(75) 99999-9999", "5575999999999"),
    ("11999990000", "5511999990000"),
    ("+5511977776666", "5511977776666"),
    ("5575999999999", "5575999999999"),  # já higienizado: permanece igual
    ("+1 555 123 4567", "15551234567"),  # estrangeiro: mantém o próprio DDI, sem receber o 55
    ("55999998888", "5555999998888"),  # DDD 55 (RS) sem DDI
    ("(75) 3222-1111", "557532221111"),  # telefone fixo
]


def _url(driver: str) -> URL:
    return make_url(POSTGRES_URL).set(drivername=f"postgresql+{driver}")


@pytest.fixture
def schema_temporario():
    """Schema exclusivo, removido ao final, para não tocar nas tabelas reais do banco."""
    nome = f"teste_{uuid.uuid4().hex[:10]}"
    engine = create_engine(_url("psycopg2"), isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA {nome}"))
    yield nome
    with engine.connect() as conn:
        conn.execute(text(f"DROP SCHEMA {nome} CASCADE"))
    engine.dispose()


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_mvp", MIGRACAO_MVP)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_migracao_higieniza_o_whatsapp_legado_e_e_idempotente(schema_temporario):
    migracao = _carregar_migracao()
    engine = create_engine(_url("psycopg2"))

    with engine.begin() as conn:
        conn.execute(text(f"SET LOCAL search_path TO {schema_temporario}"))
        conn.execute(text("CREATE TABLE associados (id serial PRIMARY KEY, whatsapp varchar(20) NOT NULL)"))
        for entrada, _ in WHATSAPP_LEGADO:
            conn.execute(text("INSERT INTO associados (whatsapp) VALUES (:whatsapp)"), {"whatsapp": entrada})

        with Operations.context(MigrationContext.configure(conn)):
            migracao._higienizar_whatsapp_legado()
            migracao._higienizar_whatsapp_legado()  # segunda execução não altera nada

        obtido = [linha[0] for linha in conn.execute(text("SELECT whatsapp FROM associados ORDER BY id"))]

    engine.dispose()
    assert obtido == [esperado for _, esperado in WHATSAPP_LEGADO]


async def test_get_or_create_concorrente_cria_um_unico_registro(schema_temporario):
    engine = create_async_engine(
        _url("asyncpg"),
        connect_args={"server_settings": {"search_path": schema_temporario}},
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Configuracao.__table__.create(sync_conn))
        sessao = async_sessionmaker(engine, expire_on_commit=False)

        async def obter() -> int:
            async with sessao() as sessao_atual:
                configuracao = await ConfiguracaoRepository(sessao_atual).get_or_create()
                await sessao_atual.commit()
                return configuracao.id

        ids = await asyncio.gather(*(obter() for _ in range(8)))

        async with sessao() as sessao_atual:
            total = (await sessao_atual.execute(text("SELECT count(*) FROM configuracoes"))).scalar_one()
        assert ids == [1] * 8
        assert total == 1
    finally:
        await engine.dispose()


async def test_emissao_concorrente_com_uma_vaga_restante_gera_exatamente_um_gratuito(schema_temporario):
    """
    Testa concorrência real no PostgreSQL:
    Quando resta exatamente 1 vaga na franquia de convidados, duas requisições simultâneas
    (via asyncio.gather) de emissão de convite para o mesmo titular devem ser serializadas
    pela trava pessimista (SELECT ... FOR UPDATE). Exatamente 1 deve ser GRATUITO e a outra EXCEDENTE.
    """
    from datetime import date
    from decimal import Decimal
    from app.models.base import Base
    from app.models.associado import Associado, StatusAssociado
    from app.models.convidado import Convidado, StatusConvidado
    from app.schemas.convidado import ConvidadoAssociadoCreate
    from app.services.convidado_service import ConvidadoService

    engine = create_async_engine(
        _url("asyncpg"),
        connect_args={"server_settings": {"search_path": schema_temporario}},
    )
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        sessao_factory = async_sessionmaker(engine, expire_on_commit=False)
        socio_id = uuid.uuid4()
        hoje = date(2026, 10, 15)

        async with sessao_factory() as sessao:
            cfg = await ConfiguracaoRepository(sessao).get_or_create()
            cfg.franquia_convidados = 2
            cfg.valor_convidado_extra = Decimal("35.00")

            socio = Associado(
                id=socio_id,
                nome="Sócio Concorrência Postgres",
                cpf="529.982.247-25",
                whatsapp="5575999990000",
                email="concorrencia@clube.com",
                status=StatusAssociado.ATIVO,
                dia_vencimento=10,
            )
            sessao.add(socio)
            # 1 convite já utilizado => resta apenas 1 vaga na franquia (total 2)
            conv_existente = Convidado(
                associado_titular_id=socio_id,
                nome="Primeiro Visitante",
                data_visita=hoje,
                status=StatusConvidado.EMITIDO,
                is_gratuito=True,
                valor_cobrado=Decimal("0.00"),
            )
            sessao.add(conv_existente)
            await sessao.commit()

        async def emitir(nome: str):
            async with sessao_factory() as s:
                service = ConvidadoService(s)
                return await service.adicionar_convidado_associado(
                    socio_id,
                    ConvidadoAssociadoCreate(nome=nome, data_visita=hoje)
                )

        resp1, resp2 = await asyncio.gather(
            emitir("Visitante Concorrente A"),
            emitir("Visitante Concorrente B")
        )

        respostas = [resp1, resp2]
        gratuitos = [r for r in respostas if r.is_gratuito]
        excedentes = [r for r in respostas if not r.is_gratuito]

        assert len(gratuitos) == 1, f"Esperado exatamente 1 gratuito sob concorrência, obtido: {len(gratuitos)}"
        assert len(excedentes) == 1, f"Esperado exatamente 1 excedente sob concorrência, obtido: {len(excedentes)}"
        assert excedentes[0].tipo == "EXCEDENTE"
        assert excedentes[0].valor_taxa_extra == Decimal("35.00")
    finally:
        await engine.dispose()

