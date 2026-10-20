"""
Validadores reutilizáveis dos schemas Pydantic v2.
"""
import re
from datetime import date
from typing import Any, Optional, TypeVar

from app.core.clock import hoje_clube

T = TypeVar("T")


def rejeitar_null(valor: Optional[T]) -> T:
    """
    Campos NOT NULL de schemas de atualização parcial (PATCH) podem ser omitidos, mas não enviados
    como null: um null explícito chegaria ao banco e viraria erro 500 em vez de 422.
    """
    if valor is None:
        raise ValueError("Este campo não aceita null: omita-o para mantê-lo inalterado.")
    return valor


UFS_BRASIL = frozenset({
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
})


def texto_opcional(valor: Any) -> Any:
    """Campos de texto opcionais vindos de formulário: remove espaços e grava vazio como null."""
    if isinstance(valor, str):
        valor = valor.strip()
        return valor or None
    return valor


def normalizar_cep(valor: Optional[str]) -> Optional[str]:
    """Aceita CEP com ou sem máscara e devolve no formato 00000-000."""
    if valor is None:
        return None
    digitos = re.sub(r"[\s.\-]", "", valor)
    if not re.fullmatch(r"\d{8}", digitos):
        raise ValueError("CEP deve conter 8 dígitos.")
    return f"{digitos[:5]}-{digitos[5:]}"


def normalizar_uf(valor: Optional[str]) -> Optional[str]:
    """Valida a sigla do estado e grava em maiúsculas."""
    if valor is None:
        return None
    sigla = valor.upper()
    if sigla not in UFS_BRASIL:
        raise ValueError("UF inválida: informe a sigla do estado (ex: BA).")
    return sigla


def validar_data_nascimento(valor: Optional[date]) -> Optional[date]:
    """Data de nascimento não pode estar no futuro nem antes de 1900."""
    if valor is None:
        return None
    if valor > hoje_clube():
        raise ValueError("Data de nascimento não pode estar no futuro.")
    if valor.year < 1900:
        raise ValueError("Data de nascimento inválida.")
    return valor
