"""
Helper centralizador de comandos INSERT específicos por dialeto (PostgreSQL e SQLite).
Permite comandos avançados como INSERT ... ON CONFLICT ... DO NOTHING RETURNING ...
de forma portátil e segura.
"""
from typing import Callable
from sqlalchemy.dialects import postgresql, sqlite

_INSERT_POR_DIALETO: dict[str, Callable] = {
    "postgresql": postgresql.insert,
    "sqlite": sqlite.insert,
}


def insert_do_dialeto(dialeto: str) -> Callable:
    """Retorna a função insert específica para o dialeto do banco de dados."""
    try:
        return _INSERT_POR_DIALETO[dialeto]
    except KeyError:
        raise NotImplementedError(
            f"Operação não suporta o dialeto '{dialeto}'. Apenas 'postgresql' e 'sqlite' são suportados."
        ) from None


# Alias para compatibilidade interna
_insert_do_dialeto = insert_do_dialeto
