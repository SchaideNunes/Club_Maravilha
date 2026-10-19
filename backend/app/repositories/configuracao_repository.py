"""
Repositório de dados da Configuração do clube (singleton, sempre id = 1).
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.configuracao import CONFIGURACAO_ID, Configuracao
from app.repositories._dialect import _insert_do_dialeto, insert_do_dialeto


class ConfiguracaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(self) -> Configuracao:
        """
        Retorna a configuração do clube, criando-a com os valores padrão quando ainda não existe.

        O INSERT ... ON CONFLICT (id) DO NOTHING é atômico: requisições concorrentes não geram erro
        de chave duplicada nem registros extras. Os defaults (valores de `settings` e templates) são
        aplicados em Python pelo INSERT, a partir dos `default=` das colunas do modelo.
        Como os demais repositórios, apenas faz flush da instrução; quem commita é a camada de serviço.
        """
        insert = _insert_do_dialeto(self.session.get_bind().dialect.name)
        await self.session.execute(
            insert(Configuracao)
            .values(id=CONFIGURACAO_ID)
            .on_conflict_do_nothing(index_elements=["id"])
        )
        resultado = await self.session.execute(
            select(Configuracao).where(Configuracao.id == CONFIGURACAO_ID)
        )
        return resultado.scalar_one()
