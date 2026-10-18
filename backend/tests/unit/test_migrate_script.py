"""
Testes do scripts.migrate: decisão entre criar o schema (banco vazio) e apenas migrar
(banco já inicializado), usada pelo comando do docker-compose.prod.yml.
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from app.core.config import settings
from app.models import Base
from scripts import migrate


def _inspector(*tabelas: str) -> SimpleNamespace:
    """Inspector falso: só o que o script consulta (get_table_names)."""
    return SimpleNamespace(get_table_names=lambda: list(tabelas))


@pytest.fixture
def espioes(monkeypatch):
    """Troca as chamadas com efeito colateral (create_all e comandos do Alembic) por mocks."""
    create_all = MagicMock(name="create_all")
    comandos = MagicMock(name="alembic_command")
    monkeypatch.setattr(Base.metadata, "create_all", create_all)
    monkeypatch.setattr(migrate, "command", comandos)
    return SimpleNamespace(create_all=create_all, command=comandos)


def _banco_com_tabelas(monkeypatch, *tabelas: str) -> None:
    monkeypatch.setattr(migrate, "inspect", lambda engine: _inspector(*tabelas))


# ------------------------------------------------------------------------------
# Decisão: banco vazio vs banco inicializado
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "tabelas,esperado",
    [
        ((), True),
        (("tabela_alheia",), True),
        (("alembic_version",), False),
        (("associados",), False),
        (("alembic_version", "associados", "faturas"), False),
    ],
)
def test_banco_vazio_decide_pelo_alembic_version_e_associados(tabelas, esperado):
    assert migrate.banco_vazio(_inspector(*tabelas)) is esperado


def test_banco_vazio_cria_schema_e_marca_head(monkeypatch, espioes):
    _banco_com_tabelas(monkeypatch)
    engine, config = MagicMock(), MagicMock()

    resultado = migrate.preparar_banco(engine, config)

    assert resultado == migrate.CRIADO
    espioes.create_all.assert_called_once_with(engine)
    espioes.command.stamp.assert_called_once_with(config, "head")
    espioes.command.upgrade.assert_not_called()


def test_banco_vazio_cria_o_schema_antes_de_marcar_head(monkeypatch, espioes):
    _banco_com_tabelas(monkeypatch)
    ordem = MagicMock()
    ordem.attach_mock(espioes.create_all, "create_all")
    ordem.attach_mock(espioes.command.stamp, "stamp")

    migrate.preparar_banco(MagicMock(), MagicMock())

    assert [chamada[0] for chamada in ordem.mock_calls] == ["create_all", "stamp"]


@pytest.mark.parametrize(
    "tabelas",
    [
        ("alembic_version", "associados", "faturas"),  # banco versionado
        ("associados", "faturas"),  # criado por create_all e nunca marcado pelo Alembic
        ("alembic_version",),
    ],
)
def test_banco_inicializado_apenas_aplica_migracoes(monkeypatch, espioes, tabelas):
    _banco_com_tabelas(monkeypatch, *tabelas)
    engine, config = MagicMock(), MagicMock()

    resultado = migrate.preparar_banco(engine, config)

    assert resultado == migrate.ATUALIZADO
    espioes.command.upgrade.assert_called_once_with(config, "head")
    espioes.create_all.assert_not_called()
    espioes.command.stamp.assert_not_called()


def test_banco_real_vazio_vira_schema_completo_e_na_segunda_execucao_so_migra(monkeypatch):
    """Sem mocks de create_all/inspect: SQLite vazio -> cria as tabelas; rodando de novo -> migra."""
    comandos = MagicMock(name="alembic_command")
    monkeypatch.setattr(migrate, "command", comandos)
    engine = create_engine("sqlite://")
    config = MagicMock()

    assert migrate.preparar_banco(engine, config) == migrate.CRIADO
    tabelas = set(inspect(engine).get_table_names())
    assert {"associados", "faturas", "configuracoes", "logs_mensagens"} <= tabelas
    comandos.stamp.assert_called_once_with(config, "head")

    assert migrate.preparar_banco(engine, config) == migrate.ATUALIZADO
    comandos.upgrade.assert_called_once_with(config, "head")
    engine.dispose()


# ------------------------------------------------------------------------------
# Configuração do Alembic e ponto de entrada
# ------------------------------------------------------------------------------
def test_alembic_config_independe_do_diretorio_de_trabalho():
    config = migrate.alembic_config()

    assert Path(config.get_main_option("script_location")).is_dir()
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1


@pytest.mark.parametrize(
    "configurada,driver_esperado",
    [
        ("postgresql://u:s@db:5432/club", "postgresql+psycopg2"),  # sem driver: psycopg2 explícito
        ("postgresql+psycopg2://u:s@db:5432/club", "postgresql+psycopg2"),
        ("postgresql+psycopg://u:s@db:5432/club", "postgresql+psycopg"),  # driver explícito é respeitado
        ("sqlite:///banco.db", "sqlite"),
    ],
)
def test_url_sincrona_fixa_o_driver_psycopg2_quando_omitido(monkeypatch, configurada, driver_esperado):
    monkeypatch.setattr(settings, "DATABASE_SYNC_URL", configurada)

    url = migrate.url_sincrona()

    assert url.drivername == driver_esperado
    assert url.render_as_string(hide_password=False).split("://", 1)[1] == configurada.split("://", 1)[1]


def test_main_usa_a_url_sincrona_e_descarta_a_engine(monkeypatch):
    engine = MagicMock()
    criar_engine = MagicMock(return_value=engine)
    preparar = MagicMock(return_value=migrate.CRIADO)
    monkeypatch.setattr(settings, "DATABASE_SYNC_URL", "postgresql://u:s@db:5432/club")
    monkeypatch.setattr(migrate, "create_engine", criar_engine)
    monkeypatch.setattr(migrate, "preparar_banco", preparar)

    migrate.main()

    criar_engine.assert_called_once_with(migrate.url_sincrona())
    assert criar_engine.call_args.args[0].drivername == "postgresql+psycopg2"
    preparar.assert_called_once()
    engine.dispose.assert_called_once()


def test_main_propaga_falha_para_impedir_a_subida_da_api(monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr(migrate, "create_engine", MagicMock(return_value=engine))
    monkeypatch.setattr(migrate, "preparar_banco", MagicMock(side_effect=RuntimeError("falhou")))

    with pytest.raises(RuntimeError, match="falhou"):
        migrate.main()

    engine.dispose.assert_called_once()
