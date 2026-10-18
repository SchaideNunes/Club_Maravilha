"""
Testes unitários da higienização de WhatsApp para o padrão Baileys
(somente dígitos com DDI 55), usada pelos schemas de Associado.
"""
import pytest
from app.core.phone import sanitize_whatsapp_number


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        # Formatos comuns digitados pela administração
        ("+55 (75) 99999-9999", "5575999999999"),
        ("(75) 99999-9999", "5575999999999"),
        ("75 3222-1111", "557532221111"),
        ("  +55 (11) 3333-4444  ", "551133334444"),
        # DDD 55 (RS) não pode ser confundido com o DDI do Brasil
        ("55999998888", "5555999998888"),
        ("(55) 99999-8888", "5555999998888"),
        ("+55 55 99999-8888", "5555999998888"),
        ("5555999998888", "5555999998888"),
        # Prefixos de tronco e de chamada internacional
        ("011 98888-7777", "5511988887777"),
        ("(011) 98888-7777", "5511988887777"),
        ("0055 11 98888-7777", "5511988887777"),
        # Já higienizado: idempotente
        ("5511988887777", "5511988887777"),
    ],
)
def test_sanitize_whatsapp_number_validos(entrada, esperado):
    assert sanitize_whatsapp_number(entrada) == esperado
    assert sanitize_whatsapp_number(esperado) == esperado


@pytest.mark.parametrize(
    "entrada",
    [
        "",
        "   ",
        "55",
        "12345",
        "abcdefghijk",
        "123456789012345",  # 15 dígitos
        "4475999999999",  # 13 dígitos com DDI diferente de 55
        "+1 555 123 4567",  # número estrangeiro
        "+75999999999",  # '+' indica formato internacional, mas sem DDI 55
        "5500999999999",  # DDD 00 não existe
        "5510999999999",  # DDD 10 não existe
    ],
)
def test_sanitize_whatsapp_number_invalidos(entrada):
    with pytest.raises(ValueError, match="WhatsApp inválido"):
        sanitize_whatsapp_number(entrada)
