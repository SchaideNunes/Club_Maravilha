"""
Testes unitários do serviço de renderização de templates de WhatsApp (Feature 3).

Contrato (app/services/template_service.py), reutilizado pela régua na Feature 4:
- formatar_moeda_brl(Decimal) -> "R$ 1.234,56" (separador de milhar ".", decimal ",", 2 casas).
- formatar_data_br(date) -> "dd/mm/aaaa".
- renderizar_template(template, variaveis) -> str: substitui somente as chaves conhecidas
  ({nome}, {valor_base}, ...); placeholders desconhecidos e chaves soltas permanecem intactos
  (nunca lança KeyError/ValueError/IndexError como str.format faria).
- variaveis_da_fatura(fatura, associado, configuracao) -> dict[str, str] com exatamente as
  chaves de VARIAVEIS_TEMPLATE, valores monetários já no formato "R$ 1.234,56".
- Os templates padrão da Configuracao NÃO podem gerar "R$ R$" (o prefixo vem da formatação).
"""
from datetime import date
from decimal import Decimal

import pytest

from app.models.associado import Associado, StatusAssociado
from app.models.configuracao import (
    TEMPLATE_D0_PADRAO,
    TEMPLATE_D_MAIS_3_PADRAO,
    TEMPLATE_D_MAIS_7_PADRAO,
    TEMPLATE_D_MENOS_3_PADRAO,
    TEMPLATE_RECIBO_PADRAO,
    VARIAVEIS_TEMPLATE,
    Configuracao,
)
from app.models.fatura import Fatura, StatusFatura
from app.services.template_service import (
    formatar_data_br,
    formatar_moeda_brl,
    renderizar_template,
    variaveis_da_fatura,
)


@pytest.mark.parametrize(
    "valor, esperado",
    [
        (Decimal("0"), "R$ 0,00"),
        (Decimal("5"), "R$ 5,00"),
        (Decimal("35.5"), "R$ 35,50"),
        (Decimal("150.00"), "R$ 150,00"),
        (Decimal("1234.56"), "R$ 1.234,56"),
        (Decimal("1234567.89"), "R$ 1.234.567,89"),
        (Decimal("10.005"), "R$ 10,01"),  # arredondamento comercial (ROUND_HALF_UP)
    ],
)
def test_formatar_moeda_brl(valor, esperado):
    assert formatar_moeda_brl(valor) == esperado


@pytest.mark.parametrize(
    "dia, esperado",
    [
        (date(2026, 2, 5), "05/02/2026"),
        (date(2026, 12, 31), "31/12/2026"),
    ],
)
def test_formatar_data_br(dia, esperado):
    assert formatar_data_br(dia) == esperado


def test_renderizar_template_substitui_variaveis_conhecidas():
    texto = renderizar_template(
        "Olá, {nome}! Total {valor_total} até {vencimento}.",
        {"nome": "Ana", "valor_total": "R$ 185,00", "vencimento": "10/11/2026"},
    )
    assert texto == "Olá, Ana! Total R$ 185,00 até 10/11/2026."


def test_renderizar_template_preserva_placeholders_desconhecidos_e_chaves_soltas():
    texto = renderizar_template(
        "Oi {nome} {desconhecida} {} { chave } {0} }{",
        {"nome": "Ana"},
    )
    assert texto == "Oi Ana {desconhecida} {} { chave } {0} }{"


def test_renderizar_template_variavel_repetida():
    assert renderizar_template("{nome}/{nome}", {"nome": "Bia"}) == "Bia/Bia"


def _cenario() -> tuple[Fatura, Associado, Configuracao]:
    associado = Associado(
        nome="Carla Souza",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="carla@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=10,
    )
    fatura = Fatura(
        referencia_mes="2026-11",
        valor_base=Decimal("1150.00"),
        valor_convidados_excedentes=Decimal("70.00"),
        valor_desconto=Decimal("0.00"),
        valor_total=Decimal("1220.00"),
        convites_usados=10,
        convites_extras=2,
        data_vencimento=date(2026, 11, 10),
        status=StatusFatura.PENDENTE,
    )
    configuracao = Configuracao(
        valor_mensalidade=Decimal("1150.00"),
        franquia_convidados=8,
        valor_convidado_extra=Decimal("35.00"),
        chave_pix="financeiro@clubmaravilha.com.br",
    )
    return fatura, associado, configuracao


def test_variaveis_da_fatura_formata_todas_as_chaves():
    fatura, associado, configuracao = _cenario()

    variaveis = variaveis_da_fatura(fatura, associado, configuracao)

    assert set(variaveis) == set(VARIAVEIS_TEMPLATE)
    assert variaveis == {
        "nome": "Carla Souza",
        "valor_base": "R$ 1.150,00",
        "convites_usados": "10",
        "convites_extras": "2",
        "valor_total": "R$ 1.220,00",
        "vencimento": "10/11/2026",
        "chave_pix": "financeiro@clubmaravilha.com.br",
    }


def test_variaveis_da_fatura_sem_chave_pix_vira_texto_vazio():
    fatura, associado, configuracao = _cenario()
    configuracao.chave_pix = None

    assert variaveis_da_fatura(fatura, associado, configuracao)["chave_pix"] == ""


@pytest.mark.parametrize(
    "template",
    [
        TEMPLATE_D_MENOS_3_PADRAO,
        TEMPLATE_D0_PADRAO,
        TEMPLATE_RECIBO_PADRAO,
        TEMPLATE_D_MAIS_3_PADRAO,
        TEMPLATE_D_MAIS_7_PADRAO,
    ],
)
def test_templates_padrao_renderizados_nao_duplicam_prefixo_monetario(template):
    fatura, associado, configuracao = _cenario()

    texto = renderizar_template(template, variaveis_da_fatura(fatura, associado, configuracao))

    assert "R$ R$" not in texto
    assert "{" not in texto and "}" not in texto
    assert "Carla Souza" in texto
    if "{valor_total}" in template:
        assert "R$ 1.220,00" in texto
