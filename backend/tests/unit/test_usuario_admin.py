"""
Feature 5 - Modelo UsuarioAdmin, utilitários de segurança (bcrypt + JWT) e migração Alembic.

Contratos:
- app/models/usuario_admin.py: `UsuarioAdmin(Base, UUIDPrimaryKeyMixin, TimestampMixin)`,
  __tablename__ = "usuarios_admin"; colunas nome (str, obrigatório), email (str, único, obrigatório),
  senha_hash (str, obrigatório), ativo (bool, default True). Exportado em `app.models`.
  O repr não expõe senha_hash.
- app/core/security.py:
    hash_senha(senha) -> str bcrypt ("$2a$"/"$2b$"/"$2y$"), com salt aleatório (dois hashes diferem);
    verificar_senha(senha, senha_hash) -> bool (False para senha errada ou hash malformado, sem exceção);
    criar_access_token(subject, expires_delta=None) -> JWT HS256 (settings.SECRET_KEY/ALGORITHM)
      com `sub` = subject e `exp` = agora + expires_delta (padrão ACCESS_TOKEN_EXPIRE_MINUTES).
  Observação: o venv usa bcrypt 5.x, incompatível com passlib 1.7.4 — use o pacote `bcrypt` diretamente.
- Nova migração Alembic (única head, down_revision = "d485e921b712") que cria `usuarios_admin`
  (email único) e a remove no downgrade.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from jose import jwt
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.security import criar_access_token, hash_senha, verificar_senha
from app.models.base import Base
from app.models.usuario_admin import UsuarioAdmin

BACKEND_DIR = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------------------------
# Modelo
# ------------------------------------------------------------------------------
async def test_usuario_admin_persiste_com_defaults(db_session):
    usuario = UsuarioAdmin(nome="Diretoria", email="diretoria@clubmaravilha.com.br", senha_hash=hash_senha("segredo123"))
    db_session.add(usuario)
    await db_session.commit()
    await db_session.refresh(usuario)

    assert usuario.id is not None
    assert usuario.ativo is True
    assert usuario.created_at is not None
    assert usuario.updated_at is not None


async def test_usuario_admin_email_unico(db_session):
    db_session.add(UsuarioAdmin(nome="A", email="dup@clube.com", senha_hash="x"))
    await db_session.commit()
    db_session.add(UsuarioAdmin(nome="B", email="dup@clube.com", senha_hash="y"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.parametrize("campo", ["nome", "email", "senha_hash", "ativo"])
def test_usuario_admin_campos_obrigatorios(campo):
    coluna = UsuarioAdmin.__table__.c[campo]
    assert coluna.nullable is False


def test_usuario_admin_tabela_e_exportacao():
    import app.models as modelos

    assert UsuarioAdmin.__tablename__ == "usuarios_admin"
    assert modelos.UsuarioAdmin is UsuarioAdmin
    assert "UsuarioAdmin" in modelos.__all__
    assert "usuarios_admin" in Base.metadata.tables
    tabela = UsuarioAdmin.__table__
    assert tabela.c["email"].unique or any(
        idx.unique and [c.name for c in idx.columns] == ["email"] for idx in tabela.indexes
    )


def test_usuario_admin_repr_nao_expoe_hash():
    usuario = UsuarioAdmin(nome="Diretoria", email="d@clube.com", senha_hash="$2b$12$segredo")
    assert "$2b$12$segredo" not in repr(usuario)


# ------------------------------------------------------------------------------
# Segurança
# ------------------------------------------------------------------------------
def test_hash_senha_bcrypt_com_salt():
    h1 = hash_senha("MinhaSenha!1")
    h2 = hash_senha("MinhaSenha!1")

    assert h1.startswith(("$2a$", "$2b$", "$2y$"))
    assert h1 != h2
    assert "MinhaSenha!1" not in h1
    assert bcrypt.checkpw(b"MinhaSenha!1", h1.encode())


def test_verificar_senha():
    h = hash_senha("correta")
    assert verificar_senha("correta", h) is True
    assert verificar_senha("errada", h) is False


@pytest.mark.parametrize("hash_invalido", ["", "nao-e-bcrypt", "$2b$12$curto"])
def test_verificar_senha_com_hash_malformado_retorna_false(hash_invalido):
    assert verificar_senha("qualquer", hash_invalido) is False


def test_criar_access_token_padrao():
    antes = datetime.now(timezone.utc)
    token = criar_access_token("abc-123")

    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert settings.ALGORITHM == "HS256"
    assert claims["sub"] == "abc-123"
    exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    esperado = antes + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assert abs((exp - esperado).total_seconds()) < 60


def test_criar_access_token_com_expiracao_customizada():
    antes = datetime.now(timezone.utc)
    token = criar_access_token("abc", expires_delta=timedelta(minutes=5))
    claims = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    exp = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    assert abs((exp - (antes + timedelta(minutes=5))).total_seconds()) < 60


# ------------------------------------------------------------------------------
# Migração Alembic
# ------------------------------------------------------------------------------
def _script() -> ScriptDirectory:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    return ScriptDirectory.from_config(config)


def test_migracao_usuarios_admin_esta_na_cadeia_com_uma_unica_head():
    script = _script()
    assert len(script.get_heads()) == 1
    revisao = script.get_revision("e5a1b2c3d4e5")
    assert revisao.down_revision == "d485e921b712"
    assert revisao.revision in {r.revision for r in script.walk_revisions()}

    fonte = Path(revisao.path).read_text(encoding="utf-8")
    assert "usuarios_admin" in fonte
    assert "create_table" in fonte
    assert "drop_table" in fonte
    for coluna in ("email", "nome", "senha_hash", "ativo"):
        assert coluna in fonte
