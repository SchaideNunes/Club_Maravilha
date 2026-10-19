"""
Feature 5 - Seed idempotente do administrador inicial (scripts/seed_admin.py).

Contratos:
- Settings ganha ADMIN_EMAIL: Optional[str] = None, ADMIN_PASSWORD: Optional[str] = None e
  ADMIN_NOME: str = "Administrador".
- `async seed_admin(session, email, senha, nome="Administrador") -> tuple[UsuarioAdmin, bool]`:
  e-mail normalizado (strip + minúsculas); cria o usuário ativo com senha bcrypt e devolve (usuario, True);
  se já existir um usuário com o e-mail, NÃO duplica e NÃO altera senha/nome — devolve (existente, False).
  Senha vazia/só espaços -> ValueError.
- `async seed_admin_from_env(session) -> UsuarioAdmin | None`: usa settings.ADMIN_EMAIL/ADMIN_PASSWORD/
  ADMIN_NOME; devolve None (sem criar nada) se e-mail ou senha não estiverem configurados.
- Execução CLI: `python -m scripts.seed_admin` (função `main()`).
"""
import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import verificar_senha
from app.models.usuario_admin import UsuarioAdmin
from scripts import seed_admin as seed


async def _total(db_session) -> int:
    return (await db_session.execute(select(func.count()).select_from(UsuarioAdmin))).scalar_one()


def test_settings_expoe_variaveis_do_admin_inicial():
    assert hasattr(settings, "ADMIN_EMAIL")
    assert hasattr(settings, "ADMIN_PASSWORD")
    assert settings.ADMIN_NOME


async def test_seed_cria_admin_ativo_com_senha_bcrypt(db_session):
    usuario, criado = await seed.seed_admin(
        db_session, "  Diretoria@ClubMaravilha.com.br ", "SenhaInicial#1", nome="Diretoria"
    )

    assert criado is True
    assert usuario.email == "diretoria@clubmaravilha.com.br"
    assert usuario.nome == "Diretoria"
    assert usuario.ativo is True
    assert usuario.senha_hash != "SenhaInicial#1"
    assert verificar_senha("SenhaInicial#1", usuario.senha_hash)
    assert await _total(db_session) == 1


async def test_seed_e_idempotente_e_nao_sobrescreve_senha(db_session):
    await seed.seed_admin(db_session, "diretoria@clubmaravilha.com.br", "SenhaOriginal#1")

    usuario, criado = await seed.seed_admin(
        db_session, "DIRETORIA@clubmaravilha.com.br", "OutraSenha#2", nome="Outro"
    )

    assert criado is False
    assert await _total(db_session) == 1
    assert verificar_senha("SenhaOriginal#1", usuario.senha_hash)
    assert not verificar_senha("OutraSenha#2", usuario.senha_hash)
    assert usuario.nome != "Outro"


@pytest.mark.parametrize("senha", ["", "   "])
async def test_seed_rejeita_senha_vazia(db_session, senha):
    with pytest.raises(ValueError):
        await seed.seed_admin(db_session, "a@clube.com", senha)
    assert await _total(db_session) == 0


async def test_seed_from_env_sem_configuracao_nao_cria(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", None)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", None)

    assert await seed.seed_admin_from_env(db_session) is None
    assert await _total(db_session) == 0


async def test_seed_from_env_so_com_email_nao_cria(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "env@clubmaravilha.com.br")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", None)

    assert await seed.seed_admin_from_env(db_session) is None
    assert await _total(db_session) == 0


async def test_seed_from_env_usa_variaveis_e_e_idempotente(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "env@clubmaravilha.com.br")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "SenhaDoEnv#1")
    monkeypatch.setattr(settings, "ADMIN_NOME", "Admin Env")

    usuario = await seed.seed_admin_from_env(db_session)
    de_novo = await seed.seed_admin_from_env(db_session)

    assert usuario is not None and usuario.email == "env@clubmaravilha.com.br"
    assert usuario.nome == "Admin Env"
    assert verificar_senha("SenhaDoEnv#1", usuario.senha_hash)
    assert de_novo.id == usuario.id
    assert await _total(db_session) == 1


def test_seed_tem_main_cli():
    assert callable(seed.main)
