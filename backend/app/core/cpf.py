"""
Módulo de validação e formatação matemática de CPF (módulo 11).
"""
import re


def validate_and_format_cpf(cpf_raw: str) -> str:
    """
    Valida matematicamente os dígitos verificadores do CPF (módulo 11)
    e retorna o CPF formatado: 000.000.000-00.
    """
    if not cpf_raw:
        raise ValueError("CPF é obrigatório e não pode ser vazio.")

    # Remove todos os caracteres não numéricos
    digits = re.sub(r"\D", "", str(cpf_raw).strip())

    # Se tiver 9 ou 10 dígitos (ex: Excel removeu zeros à esquerda), completa com zeros à esquerda
    if 9 <= len(digits) < 11:
        digits = digits.zfill(11)

    if len(digits) != 11:
        raise ValueError(f"CPF deve conter exatamente 11 dígitos numéricos (recebido: {len(digits)}).")

    # Rejeita sequências conhecidas de dígitos repetidos (ex: 111.111.111-11)
    if digits == digits[0] * 11:
        raise ValueError("CPF inválido: sequência de dígitos idênticos.")

    # Cálculo do 1º Dígito Verificador
    soma_1 = sum(int(digits[i]) * (10 - i) for i in range(9))
    resto_1 = (soma_1 * 10) % 11
    d1 = 0 if resto_1 == 10 else resto_1
    if d1 != int(digits[9]):
        raise ValueError("Dígitos verificadores do CPF inválidos.")

    # Cálculo do 2º Dígito Verificador
    soma_2 = sum(int(digits[i]) * (11 - i) for i in range(10))
    resto_2 = (soma_2 * 10) % 11
    d2 = 0 if resto_2 == 10 else resto_2
    if d2 != int(digits[10]):
        raise ValueError("Dígitos verificadores do CPF inválidos.")

    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
