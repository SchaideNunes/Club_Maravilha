"""
Higienização de números de WhatsApp para o padrão do motor Baileys.

Padrão armazenado: somente dígitos com DDI 55 (ex: ``5575999999999``). O JID
(``@s.whatsapp.net``) é montado e resolvido pelo motor, nunca gravado no banco.
"""
import re

DDI_BRASIL = "55"
DDD_MINIMO = 11  # Menor DDD válido no Brasil (São Paulo)

_MENSAGEM_INVALIDO = (
    "Número de WhatsApp inválido: informe DDD + número brasileiro, "
    "ex.: (75) 99999-9999 ou +55 75 99999-9999."
)


def sanitize_whatsapp_number(numero: str) -> str:
    """
    Converte um telefone brasileiro digitado livremente para o padrão Baileys.

    Regras:
    - Remove pontuação, espaços e o ``+`` (``+55 (75) 99999-9999`` -> ``5575999999999``).
    - 10 ou 11 dígitos sem ``+`` são DDD + número local e recebem o DDI 55
      (inclusive números com DDD 55, que não são confundidos com o DDI).
    - Zeros à esquerda (prefixo de tronco ``0 xx`` / ``0055``) são descartados.
    - Com DDI, exige 12 ou 13 dígitos iniciados por 55 e DDD >= 11.

    Raises:
        ValueError: quando o valor não puder ser interpretado como telefone brasileiro.
    """
    texto = str(numero).strip()
    internacional = texto.startswith("+")
    digitos = re.sub(r"\D", "", texto)

    if not internacional:
        digitos = digitos.lstrip("0")

    if not internacional and len(digitos) in (10, 11):
        digitos = f"{DDI_BRASIL}{digitos}"

    if len(digitos) not in (12, 13) or not digitos.startswith(DDI_BRASIL):
        raise ValueError(_MENSAGEM_INVALIDO)

    if int(digitos[2:4]) < DDD_MINIMO:
        raise ValueError(_MENSAGEM_INVALIDO)

    return digitos
