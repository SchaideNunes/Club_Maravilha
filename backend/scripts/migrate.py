"""
Prepara o banco de dados antes de a API subir (usado pelo docker-compose.prod.yml).

O histórico do Alembic é uma sequência de deltas sobre um schema criado por
`Base.metadata.create_all` (a primeira migração só faz ALTER TABLE em `faturas`),
portanto ele não consegue construir um banco do zero. Por isso:

- Banco vazio (sem `alembic_version` e sem a tabela `associados`): cria o schema atual
  a partir dos modelos e marca o banco como atualizado (`alembic stamp head`).
- Banco já existente: aplica as migrações pendentes (`alembic upgrade head`).

Uso (a partir de backend/):
    python -m scripts.migrate
    docker compose exec backend python -m scripts.migrate

Em caso de falha o processo termina com código diferente de zero, o que impede
`&& uvicorn ...` de subir a API com o banco em estado desconhecido.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.engine.reflection import Inspector

from app.core.config import settings
from app.models import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]

# A presença de qualquer uma destas tabelas indica que o banco já foi inicializado
TABELAS_DE_BANCO_INICIALIZADO = frozenset({"alembic_version", "associados"})

CRIADO = "criado"
ATUALIZADO = "atualizado"


def banco_vazio(inspector: Inspector) -> bool:
    """True quando o banco ainda não foi inicializado: nem `alembic_version` nem `associados`."""
    return not TABELAS_DE_BANCO_INICIALIZADO.intersection(inspector.get_table_names())


def url_sincrona() -> URL:
    """
    URL síncrona do banco (DATABASE_SYNC_URL) com driver explícito. Um `postgresql://` sem driver
    depende da versão do SQLAlchemy (a 2.1 escolhe o psycopg 3), mas o projeto instala o psycopg2.
    """
    url = make_url(settings.DATABASE_SYNC_URL)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg2")
    return url


def alembic_config() -> Config:
    """Configuração do Alembic independente do diretório de trabalho atual."""
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return config


def preparar_banco(engine: Engine, config: Config) -> str:
    """
    Deixa o banco na revisão `head`. Retorna `CRIADO` quando o schema foi gerado a partir
    dos modelos (banco vazio) ou `ATUALIZADO` quando apenas as migrações pendentes rodaram.
    """
    if banco_vazio(inspect(engine)):
        print("[migrate] Banco vazio: criando o schema a partir dos modelos (create_all)...", flush=True)
        Base.metadata.create_all(engine)
        print("[migrate] Marcando o banco como atualizado (alembic stamp head)...", flush=True)
        command.stamp(config, "head")
        return CRIADO

    print("[migrate] Banco existente: aplicando as migrações pendentes (alembic upgrade head)...", flush=True)
    command.upgrade(config, "head")
    return ATUALIZADO


def main() -> None:
    engine = create_engine(url_sincrona())
    try:
        resultado = preparar_banco(engine, alembic_config())
    finally:
        engine.dispose()
    print(f"[migrate] Concluído: banco {resultado}.", flush=True)


if __name__ == "__main__":
    main()
