"""
Regressão: a trava pessimista do associado (baixa manual, inativação) precisa funcionar no
PostgreSQL mesmo com o plano carregado por LEFT JOIN (lazy="joined"). Sem `OF associados`, o
PostgreSQL rejeita com "FOR UPDATE cannot be applied to the nullable side of an outer join" — erro
que o SQLite dos testes não reproduz, por isso o SQL é compilado para o dialeto do PostgreSQL.
"""
import uuid

from sqlalchemy.dialects import postgresql

from app.repositories.associado_repository import AssociadoRepository


class _SessaoQueCaptura:
    def __init__(self) -> None:
        self.statement = None

    async def execute(self, statement):
        self.statement = statement

        class _Resultado:
            def scalar_one_or_none(self):
                return None

        return _Resultado()


async def test_get_by_id_for_update_trava_somente_a_tabela_de_associados():
    sessao = _SessaoQueCaptura()
    await AssociadoRepository(sessao).get_by_id(uuid.uuid4(), for_update=True)

    sql = str(sessao.statement.compile(dialect=postgresql.dialect()))

    assert "LEFT OUTER JOIN planos" in sql
    assert sql.rstrip().endswith("FOR UPDATE OF associados")
