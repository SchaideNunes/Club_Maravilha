"""
Serviço de renderização e formatação de templates de mensagens de WhatsApp.

Contrato:
- formatar_moeda_brl(Decimal) -> "R$ 1.234,56" (separador milhar ".", decimal ",", 2 casas, ROUND_HALF_UP).
- formatar_data_br(date) -> "dd/mm/aaaa".
- renderizar_template(template, variaveis) -> str: substitui chaves conhecidas;
  preserva chaves desconhecidas e caracteres soltos de chaves sem lançar exceções.
- variaveis_da_fatura(fatura, associado, configuracao) -> dict[str, str]: monta o
  dicionário de variáveis mapeadas a partir dos modelos.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any, Mapping

from app.models.associado import Associado
from app.models.configuracao import VARIAVEIS_TEMPLATE, Configuracao
from app.models.fatura import Fatura


_CENTAVOS = Decimal("0.01")
_VARIAVEL_REGEX = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def formatar_moeda_brl(valor: Decimal | float | int) -> str:
    """
    Formata um valor numérico em moeda brasileira BRL: "R$ 1.234,56".
    Utiliza arredondamento comercial (ROUND_HALF_UP).
    """
    if not isinstance(valor, Decimal):
        valor = Decimal(str(valor))
    valor_arredondado = valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)
    negativo = valor_arredondado < 0
    valor_abs = abs(valor_arredondado)
    partes = f"{valor_abs:.2f}".split(".")
    inteiro_formatado = "{:,}".format(int(partes[0])).replace(",", ".")
    decimal_formatado = partes[1]
    sinal = "-" if negativo else ""
    return f"{sinal}R$ {inteiro_formatado},{decimal_formatado}"


def formatar_data_br(dia: date) -> str:
    """Formata uma data para o padrão brasileiro dd/mm/aaaa."""
    return dia.strftime("%d/%m/%Y")


def renderizar_template(template: str, variaveis: Mapping[str, Any]) -> str:
    """
    Substitui no template as variáveis presentes no dicionário `variaveis`.
    Placeholders desconhecidos, vazios ou chaves malformadas permanecem intactos,
    sem disparar exceções como KeyError ou ValueError.
    """
    def _substituir(match: re.Match) -> str:
        chave = match.group(1)
        if chave in variaveis:
            return str(variaveis[chave])
        return match.group(0)

    return _VARIAVEL_REGEX.sub(_substituir, template)


def variaveis_da_fatura(
    fatura: Fatura,
    associado: Associado,
    configuracao: Configuracao,
) -> dict[str, str]:
    """
    Extrai e formata o dicionário com todas as variáveis esperadas por um template
    de fatura (definidas em VARIAVEIS_TEMPLATE).
    """
    return {
        "nome": associado.nome,
        "valor_base": formatar_moeda_brl(fatura.valor_base),
        "convites_usados": str(fatura.convites_usados),
        "convites_extras": str(fatura.convites_extras),
        "valor_total": formatar_moeda_brl(fatura.valor_total),
        "vencimento": formatar_data_br(fatura.data_vencimento),
        "chave_pix": configuracao.chave_pix or "",
    }
