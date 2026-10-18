"""
Testes complementares do modelo Configuracao: garantia de singleton no banco,
variáveis dos templates padrão e cálculo de convites excedentes.
"""
import re
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.configuracao import (
    CONFIGURACAO_ID,
    VARIAVEIS_TEMPLATE,
    Configuracao,
)

CAMPOS_TEMPLATE = (
    "template_d_menos_3",
    "template_d0",
    "template_recibo",
    "template_d_mais_3",
    "template_d_mais_7",
)


async def test_configuracao_rejeita_segundo_registro(db_session):
    """O CHECK (id = 1) impede qualquer registro além do singleton."""
    db_session.add(Configuracao())
    await db_session.commit()

    db_session.add(Configuracao(id=2))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    registros = (await db_session.execute(select(Configuracao))).scalars().all()
    assert [c.id for c in registros] == [CONFIGURACAO_ID]


async def test_configuracao_rejeita_duplicar_o_singleton(db_session):
    db_session.add(Configuracao())
    await db_session.commit()
    db_session.expunge_all()  # força o conflito a ocorrer no banco, não no identity map

    db_session.add(Configuracao())
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_templates_padrao_usam_somente_variaveis_conhecidas(db_session):
    cfg = Configuracao()
    db_session.add(cfg)
    await db_session.flush()

    for campo in CAMPOS_TEMPLATE:
        usadas = set(re.findall(r"\{([^{}]*)\}", getattr(cfg, campo)))
        desconhecidas = usadas - set(VARIAVEIS_TEMPLATE)
        assert not desconhecidas, f"{campo} usa variáveis desconhecidas: {desconhecidas}"


@pytest.mark.parametrize(
    "usados,esperado",
    [(0, 0), (7, 0), (8, 0), (9, 1), (13, 5)],
)
def test_configuracao_calcular_convidados_excedentes(usados, esperado):
    cfg = Configuracao(franquia_convidados=8)
    assert cfg.calcular_convidados_excedentes(usados) == esperado
