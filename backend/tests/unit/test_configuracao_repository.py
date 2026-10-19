"""
Testes do ConfiguracaoRepository.get_or_create: criação do singleton com defaults,
idempotência e uso dos valores padrão vindos de settings.
"""
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models.configuracao import (
    CONFIGURACAO_ID,
    TEMPLATE_D0_PADRAO,
    TEMPLATE_D_MAIS_3_PADRAO,
    TEMPLATE_D_MAIS_7_PADRAO,
    TEMPLATE_D_MENOS_3_PADRAO,
    TEMPLATE_RECIBO_PADRAO,
    Configuracao,
)
from app.repositories.configuracao_repository import ConfiguracaoRepository, _insert_do_dialeto


async def _total_de_registros(db_session) -> int:
    return (await db_session.execute(select(func.count()).select_from(Configuracao))).scalar_one()


async def test_get_or_create_cria_o_registro_quando_a_tabela_esta_vazia(db_session):
    assert await _total_de_registros(db_session) == 0

    config = await ConfiguracaoRepository(db_session).get_or_create()

    assert isinstance(config, Configuracao)
    assert config.id == CONFIGURACAO_ID
    assert await _total_de_registros(db_session) == 1


async def test_get_or_create_materializa_todos_os_defaults(db_session):
    config = await ConfiguracaoRepository(db_session).get_or_create()

    assert config.valor_mensalidade == Decimal("150.00")
    assert config.franquia_convidados == 8
    assert config.valor_convidado_extra == Decimal("35.00")
    assert config.chave_pix is None
    assert config.horario_disparo == "08:00"
    assert config.automacao_ativa is True
    assert config.template_d_menos_3 == TEMPLATE_D_MENOS_3_PADRAO
    assert config.template_d0 == TEMPLATE_D0_PADRAO
    assert config.template_recibo == TEMPLATE_RECIBO_PADRAO
    assert config.template_d_mais_3 == TEMPLATE_D_MAIS_3_PADRAO
    assert config.template_d_mais_7 == TEMPLATE_D_MAIS_7_PADRAO
    assert config.updated_at is not None  # server_default preenchido pelo banco


async def test_get_or_create_usa_os_valores_padrao_de_settings(db_session, monkeypatch):
    monkeypatch.setattr(settings, "VALOR_MENSALIDADE_PADRAO", 199.9)
    monkeypatch.setattr(settings, "FRANQUIA_CONVITES_MENSAL", 5)
    monkeypatch.setattr(settings, "VALOR_CONVITE_EXCEDENTE", 42.5)

    config = await ConfiguracaoRepository(db_session).get_or_create()

    assert config.valor_mensalidade == Decimal("199.90")
    assert config.franquia_convidados == 5
    assert config.valor_convidado_extra == Decimal("42.50")


async def test_get_or_create_e_idempotente_e_preserva_alteracoes(db_session):
    repo = ConfiguracaoRepository(db_session)
    primeira = await repo.get_or_create()
    primeira.chave_pix = "financeiro@clubmaravilha.com.br"
    primeira.franquia_convidados = 12
    await db_session.commit()
    db_session.expunge_all()  # próxima chamada precisa ler do banco, como em outra requisição

    segunda = await repo.get_or_create()
    terceira = await repo.get_or_create()

    assert segunda is terceira
    assert segunda.chave_pix == "financeiro@clubmaravilha.com.br"
    assert segunda.franquia_convidados == 12
    assert await _total_de_registros(db_session) == 1


async def test_get_or_create_nao_sobrescreve_registro_existente_com_defaults(db_session, monkeypatch):
    db_session.add(Configuracao(valor_mensalidade=Decimal("180.00"), automacao_ativa=False))
    await db_session.commit()
    db_session.expunge_all()
    monkeypatch.setattr(settings, "VALOR_MENSALIDADE_PADRAO", 999.0)

    config = await ConfiguracaoRepository(db_session).get_or_create()

    assert config.valor_mensalidade == Decimal("180.00")
    assert config.automacao_ativa is False
    assert await _total_de_registros(db_session) == 1


async def test_get_or_create_nao_confirma_a_transacao(db_session):
    """Como os demais repositórios, quem commita é a camada de serviço."""
    await ConfiguracaoRepository(db_session).get_or_create()
    await db_session.rollback()

    assert await _total_de_registros(db_session) == 0


def test_dialeto_sem_on_conflict_e_rejeitado_com_erro_claro():
    assert _insert_do_dialeto("postgresql") is not None
    assert _insert_do_dialeto("sqlite") is not None
    with pytest.raises(NotImplementedError, match="mysql"):
        _insert_do_dialeto("mysql")
