"""
Validadores reutilizáveis dos schemas Pydantic v2.
"""
from typing import Optional, TypeVar

T = TypeVar("T")


def rejeitar_null(valor: Optional[T]) -> T:
    """
    Campos NOT NULL de schemas de atualização parcial (PATCH) podem ser omitidos, mas não enviados
    como null: um null explícito chegaria ao banco e viraria erro 500 em vez de 422.
    """
    if valor is None:
        raise ValueError("Este campo não aceita null: omita-o para mantê-lo inalterado.")
    return valor
