"""
Testes das validações adicionais dos schemas (code review da Feature 1): sintaxe dos templates de
mensagem, null explícito em campos NOT NULL dos PATCH e data futura na baixa manual.
"""
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.configuracao import (
    TEMPLATE_D0_PADRAO,
    TEMPLATE_D_MAIS_3_PADRAO,
    TEMPLATE_D_MAIS_7_PADRAO,
    TEMPLATE_D_MENOS_3_PADRAO,
    TEMPLATE_RECIBO_PADRAO,
    VARIAVEIS_TEMPLATE,
)
from app.schemas.associado import CAMPOS_ATUALIZAVEIS_NAO_NULOS, AssociadoUpdate
from app.schemas.configuracao import CAMPOS_NAO_NULOS, ConfiguracaoUpdate, validar_template
from app.schemas.fatura import FaturaBaixaManual

CAMPOS_TEMPLATE = (
    "template_d_menos_3",
    "template_d0",
    "template_recibo",
    "template_d_mais_3",
    "template_d_mais_7",
)


# ------------------------------------------------------------------------------
# Templates de mensagem
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "template",
    [
        "Ola {nom}",  # variável com erro de digitação
        "Ola {nom} {",  # erro de digitação + chave sem par
        "Ola {nome",  # chave aberta sem fechar
        "{",
        "}",
        "a } b",
        "{{}",  # '{{' literal seguido de '}' solto
        "{}",  # campo vazio
        "{0}",  # campo posicional
        "Ola {nome} {1}",
        "{nome!r}",  # conversão
        "{nome:>10}",  # especificação de formato
        "{nome.upper}",  # acesso a atributo
        "{nome[0]}",  # acesso a índice
        "{Nome}",  # variáveis diferenciam maiúsculas de minúsculas
        "{valor_total:{nome}}",  # formato aninhado
    ],
)
def test_template_invalido_e_rejeitado(template):
    with pytest.raises(ValidationError):
        ConfiguracaoUpdate(template_d0=template)


def test_template_invalido_informa_o_motivo():
    with pytest.raises(ValidationError, match="variável desconhecida '{nom}'"):
        ConfiguracaoUpdate(template_d0="Ola {nom}")
    with pytest.raises(ValidationError, match="campo vazio ou posicional '{}'"):
        ConfiguracaoUpdate(template_d0="Ola {}")
    with pytest.raises(ValidationError, match="Template inválido"):
        ConfiguracaoUpdate(template_d0="Ola {")


@pytest.mark.parametrize(
    "campo,padrao",
    [
        ("template_d_menos_3", TEMPLATE_D_MENOS_3_PADRAO),
        ("template_d0", TEMPLATE_D0_PADRAO),
        ("template_recibo", TEMPLATE_RECIBO_PADRAO),
        ("template_d_mais_3", TEMPLATE_D_MAIS_3_PADRAO),
        ("template_d_mais_7", TEMPLATE_D_MAIS_7_PADRAO),
    ],
)
def test_templates_padrao_sao_aceitos(campo, padrao):
    assert getattr(ConfiguracaoUpdate(**{campo: padrao}), campo) == padrao


def test_todas_as_variaveis_conhecidas_sao_aceitas():
    template = " ".join("{" + variavel + "}" for variavel in VARIAVEIS_TEMPLATE)

    assert validar_template(template) == template


@pytest.mark.parametrize("template", ["Aviso geral sem variáveis", "Chaves literais {{assim}} e {nome}"])
def test_template_sem_variaveis_ou_com_chaves_escapadas_e_aceito(template):
    assert ConfiguracaoUpdate(template_d0=template).template_d0 == template


def test_template_tem_espacos_das_pontas_removidos():
    assert ConfiguracaoUpdate(template_d0="  Olá {nome}\n").template_d0 == "Olá {nome}"


# ------------------------------------------------------------------------------
# null explícito em campos NOT NULL (PATCH)
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("campo", CAMPOS_NAO_NULOS)
def test_configuracao_update_rejeita_null_explicito(campo):
    with pytest.raises(ValidationError) as erro:
        ConfiguracaoUpdate(**{campo: None})

    assert erro.value.errors()[0]["loc"] == (campo,)


def test_configuracao_update_chave_pix_aceita_null_para_limpar_a_chave():
    assert ConfiguracaoUpdate(chave_pix=None).model_dump(exclude_unset=True) == {"chave_pix": None}


def test_configuracao_update_omitir_campos_continua_valido():
    assert ConfiguracaoUpdate().model_dump(exclude_unset=True) == {}


def test_configuracao_update_toda_coluna_nova_precisa_decidir_sobre_null():
    """Falha se um campo novo não entrar na regra de null (nem for declarado anulável)."""
    assert set(ConfiguracaoUpdate.model_fields) == set(CAMPOS_NAO_NULOS) | {"chave_pix"}


@pytest.mark.parametrize("campo", CAMPOS_ATUALIZAVEIS_NAO_NULOS)
def test_associado_update_rejeita_null_explicito(campo):
    with pytest.raises(ValidationError) as erro:
        AssociadoUpdate(**{campo: None})

    assert erro.value.errors()[0]["loc"] == (campo,)


@pytest.mark.parametrize("campo", ["foto_url", "observacoes"])
def test_associado_update_campos_opcionais_aceitam_null(campo):
    assert AssociadoUpdate(**{campo: None}).model_dump(exclude_unset=True) == {campo: None}


def test_associado_update_toda_coluna_nova_precisa_decidir_sobre_null():
    assert set(AssociadoUpdate.model_fields) == set(CAMPOS_ATUALIZAVEIS_NAO_NULOS) | {"foto_url", "observacoes"}


# ------------------------------------------------------------------------------
# Baixa manual: data de pagamento
# ------------------------------------------------------------------------------
def _agora() -> datetime:
    return datetime.now(timezone.utc)


@pytest.mark.parametrize("deslocamento", [timedelta(days=-30), timedelta(minutes=-1), timedelta(minutes=2)])
def test_baixa_manual_aceita_data_passada_ou_dentro_da_tolerancia_de_relogio(deslocamento):
    quando = _agora() + deslocamento

    assert FaturaBaixaManual(forma_pagamento="PIX", data_pagamento=quando).data_pagamento == quando


@pytest.mark.parametrize("deslocamento", [timedelta(minutes=10), timedelta(hours=3), timedelta(days=2)])
def test_baixa_manual_rejeita_data_futura(deslocamento):
    with pytest.raises(ValidationError, match="não pode estar no futuro"):
        FaturaBaixaManual(forma_pagamento="DINHEIRO", data_pagamento=_agora() + deslocamento)


def test_baixa_manual_sem_fuso_horario_e_tratada_como_utc():
    passada = (_agora() - timedelta(days=1)).replace(tzinfo=None)
    futura = (_agora() + timedelta(days=1)).replace(tzinfo=None)

    assert FaturaBaixaManual(forma_pagamento="CARTAO", data_pagamento=passada).data_pagamento == passada
    with pytest.raises(ValidationError, match="não pode estar no futuro"):
        FaturaBaixaManual(forma_pagamento="CARTAO", data_pagamento=futura)


def test_baixa_manual_data_omitida_continua_valida():
    assert FaturaBaixaManual(forma_pagamento="PIX").data_pagamento is None
