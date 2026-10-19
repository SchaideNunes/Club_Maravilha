"""
Feature 5 - Infraestrutura de autenticação do painel admin.

Contratos:
- .env.example documenta ADMIN_EMAIL, ADMIN_PASSWORD (seed do admin inicial) e SECRET_KEY.
- docker-compose.prod.yml: backend exige SECRET_KEY (`${SECRET_KEY:?...}`), para nunca subir em
  produção com a chave de desenvolvimento, e repassa ADMIN_EMAIL/ADMIN_PASSWORD (seed idempotente).
- requirements.txt mantém python-jose e bcrypt.
"""
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent


def _env_example() -> dict:
    valores = {}
    for linha in (ROOT_DIR / ".env.example").read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, _, valor = linha.partition("=")
            valores[chave.strip()] = valor.strip()
    return valores


def _backend_env_prod() -> dict:
    compose = yaml.safe_load((ROOT_DIR / "docker-compose.prod.yml").read_text(encoding="utf-8"))
    environment = compose["services"]["backend"].get("environment") or {}
    if isinstance(environment, list):
        environment = dict(item.split("=", 1) for item in environment)
    return {k: str(v) for k, v in environment.items()}


def test_env_example_documenta_admin_inicial():
    env = _env_example()
    assert "ADMIN_EMAIL" in env
    assert "ADMIN_PASSWORD" in env
    assert "SECRET_KEY" in env


def test_compose_de_producao_exige_secret_key():
    env = _backend_env_prod()
    assert "SECRET_KEY" in env
    assert env["SECRET_KEY"].startswith("${SECRET_KEY:?")


def test_compose_de_producao_repassa_admin_inicial():
    env = _backend_env_prod()
    assert "ADMIN_EMAIL" in env
    assert "ADMIN_PASSWORD" in env


def test_requirements_mantem_jose_e_bcrypt():
    reqs = (BACKEND_DIR / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "python-jose" in reqs
    assert "bcrypt" in reqs
