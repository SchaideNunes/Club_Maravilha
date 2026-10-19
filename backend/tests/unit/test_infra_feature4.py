"""
Feature 4 - Infraestrutura do motor Baileys (whatsapp-engine) e provedor padrão de produção.

Contratos:
- .env.example: WHATSAPP_PROVIDER=BAILEYS (padrão de produção); sem variáveis legadas da Evolution API.
- docker-compose.prod.yml: backend com WHATSAPP_PROVIDER=BAILEYS explícito (um .env com MOCK não desliga
  o envio em produção sem querer).
- whatsapp-engine/: package.json com @whiskeysockets/baileys 7.0.0-rc14 e scripts test/build/typecheck;
  entrypoint src/index.ts; Dockerfile real (não placeholder) que compila (npm ci + npm run build),
  roda `node dist/index.js` e usa /app/auth.
- .gitignore: whatsapp-engine/node_modules, whatsapp-engine/dist e whatsapp-engine/auth nunca versionados.
"""
import json
from pathlib import Path

import yaml

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
ENGINE_DIR = ROOT_DIR / "whatsapp-engine"


def _env_example() -> dict:
    valores = {}
    for linha in (ROOT_DIR / ".env.example").read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, _, valor = linha.partition("=")
            valores[chave.strip()] = valor.strip()
    return valores


def test_env_example_usa_baileys_por_padrao():
    env = _env_example()
    assert env.get("WHATSAPP_PROVIDER") == "BAILEYS"


def test_env_example_sem_variaveis_legadas_da_evolution():
    env = _env_example()
    assert "WHATSAPP_API_URL" not in env
    assert "WHATSAPP_INSTANCE_NAME" not in env


def test_compose_de_producao_forca_provedor_baileys():
    compose = yaml.safe_load((ROOT_DIR / "docker-compose.prod.yml").read_text(encoding="utf-8"))
    environment = compose["services"]["backend"].get("environment") or {}
    if isinstance(environment, list):
        environment = dict(item.split("=", 1) for item in environment)
    assert str(environment.get("WHATSAPP_PROVIDER")) == "BAILEYS"


def test_package_json_do_engine():
    pacote = json.loads((ENGINE_DIR / "package.json").read_text(encoding="utf-8"))
    assert pacote["dependencies"]["@whiskeysockets/baileys"] == "7.0.0-rc14"
    for script in ("test", "build", "typecheck"):
        assert script in pacote["scripts"]
    assert (ENGINE_DIR / "package-lock.json").exists()


def test_engine_tem_entrypoint():
    assert (ENGINE_DIR / "src" / "index.ts").exists()


def test_dockerfile_do_engine_compila_e_roda_o_motor():
    dockerfile = (ENGINE_DIR / "Dockerfile").read_text(encoding="utf-8")
    assert "placeholder" not in dockerfile.lower()
    assert "npm ci" in dockerfile
    assert "npm run build" in dockerfile
    assert "dist/index.js" in dockerfile
    assert "/app/auth" in dockerfile


def test_gitignore_protege_artefatos_e_sessao_do_engine():
    linhas = {
        linha.strip().rstrip("/")
        for linha in (ROOT_DIR / ".gitignore").read_text(encoding="utf-8").splitlines()
    }
    for caminho in ("whatsapp-engine/node_modules", "whatsapp-engine/dist", "whatsapp-engine/auth"):
        assert caminho in linhas, caminho
