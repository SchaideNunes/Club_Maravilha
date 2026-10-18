"""
Feature 1 (MVP) - Testes de infraestrutura: docker-compose, .env.example, Settings e migração Alembic.

Contratos:
- docker-compose.yml (raiz): serviço `whatsapp-engine` com build `./whatsapp-engine`, volume nomeado
  persistente montado em `/app/auth`; nenhuma referência à imagem `evoapicloud/evolution-api`;
  serviço `backend` com env `WHATSAPP_ENGINE_URL` apontando para `http://whatsapp-engine:<porta>`
  e dependendo de `whatsapp-engine`.
- docker-compose.prod.yml: também sem Evolution API e com `whatsapp-engine`.
- .env.example e Settings: `WHATSAPP_ENGINE_URL`.
- alembic/versions: nova revisão (down_revision = 'ffc02257a2fe', head única) que cria
  `configuracoes` e `logs_mensagens`, adiciona `associados.dia_vencimento` e introduz `ATRASADA`.
"""
import re
from pathlib import Path

import pytest
import yaml

BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = BACKEND_DIR.parent
VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"
REVISAO_INICIAL = "ffc02257a2fe"


def _load_compose(nome: str) -> dict:
    caminho = ROOT_DIR / nome
    assert caminho.exists(), f"{nome} não encontrado na raiz do repositório"
    return yaml.safe_load(caminho.read_text(encoding="utf-8"))


def _env_as_dict(environment) -> dict:
    if environment is None:
        return {}
    if isinstance(environment, dict):
        return {k: ("" if v is None else str(v)) for k, v in environment.items()}
    resultado = {}
    for item in environment:
        chave, _, valor = str(item).partition("=")
        resultado[chave] = valor
    return resultado


def _build_context(service: dict) -> str:
    build = service.get("build")
    if isinstance(build, str):
        return build
    if isinstance(build, dict):
        return build.get("context", "")
    return ""


def _depends_on(service: dict) -> list:
    dep = service.get("depends_on") or []
    return list(dep.keys()) if isinstance(dep, dict) else list(dep)


@pytest.fixture(params=["docker-compose.yml", "docker-compose.prod.yml"])
def compose_file(request):
    return request.param


def test_compose_sem_evolution_api(compose_file):
    texto = (ROOT_DIR / compose_file).read_text(encoding="utf-8")
    assert "evoapicloud/evolution-api" not in texto
    services = _load_compose(compose_file)["services"]
    for nome, svc in services.items():
        assert "evolution" not in str(svc.get("image", "")).lower(), f"{nome} ainda usa Evolution API"


def test_compose_tem_whatsapp_engine_com_build_local(compose_file):
    services = _load_compose(compose_file)["services"]
    assert "whatsapp-engine" in services
    contexto = _build_context(services["whatsapp-engine"]).rstrip("/")
    assert contexto in ("./whatsapp-engine", "whatsapp-engine")


def test_compose_whatsapp_engine_volume_persistente_de_sessao(compose_file):
    compose = _load_compose(compose_file)
    engine = compose["services"]["whatsapp-engine"]
    volumes = engine.get("volumes") or []
    named_volumes = compose.get("volumes") or {}

    montagens_auth = []
    for vol in volumes:
        if isinstance(vol, str):
            partes = vol.split(":")
            if len(partes) >= 2 and partes[1] == "/app/auth":
                montagens_auth.append(partes[0])
        elif isinstance(vol, dict) and vol.get("target") == "/app/auth":
            montagens_auth.append(vol.get("source", ""))

    assert montagens_auth, "whatsapp-engine deve montar um volume em /app/auth"
    origem = montagens_auth[0]
    assert origem in named_volumes, "a sessão Baileys deve usar volume nomeado declarado em volumes:"


def test_compose_backend_aponta_para_engine(compose_file):
    services = _load_compose(compose_file)["services"]
    backend = services["backend"]
    env = _env_as_dict(backend.get("environment"))
    assert "WHATSAPP_ENGINE_URL" in env
    assert re.match(r"^http://whatsapp-engine:\d+/?$", env["WHATSAPP_ENGINE_URL"])
    assert "whatsapp-engine" in _depends_on(backend)
    assert "whatsapp" not in services, "serviço legado 'whatsapp' (Evolution) deve ser removido"


def test_env_example_tem_whatsapp_engine_url():
    texto = (ROOT_DIR / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^WHATSAPP_ENGINE_URL=", texto, re.MULTILINE)


def test_settings_tem_whatsapp_engine_url():
    from app.core.config import Settings

    assert "WHATSAPP_ENGINE_URL" in Settings.model_fields
    assert Settings.model_fields["WHATSAPP_ENGINE_URL"].default.startswith("http")


# ------------------------------------------------------------------------------
# Alembic
# ------------------------------------------------------------------------------
def _revisoes() -> dict:
    revisoes = {}
    for arquivo in VERSIONS_DIR.glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        rev = re.search(r"^revision(?::[^=]+)?=\s*['\"]([^'\"]+)['\"]", texto, re.MULTILINE)
        down = re.search(r"^down_revision(?::[^=]+)?=\s*['\"]?([^'\"\n]+?)['\"]?\s*$", texto, re.MULTILINE)
        if rev:
            revisoes[rev.group(1)] = {
                "down": down.group(1).strip() if down else None,
                "texto": texto,
                "arquivo": arquivo.name,
            }
    return revisoes


def _migracao_mvp() -> dict:
    for dados in _revisoes().values():
        texto = dados["texto"]
        if re.search(r"create_table\(\s*['\"]configuracoes['\"]", texto):
            return dados
    pytest.fail("Nenhuma migração em alembic/versions cria a tabela 'configuracoes'")


def test_migracao_cria_configuracoes_e_logs_mensagens():
    dados = _migracao_mvp()
    texto = dados["texto"]
    assert re.search(r"create_table\(\s*['\"]logs_mensagens['\"]", texto)
    assert re.search(r"drop_table\(\s*['\"]configuracoes['\"]", texto), "downgrade deve remover configuracoes"
    assert re.search(r"drop_table\(\s*['\"]logs_mensagens['\"]", texto), "downgrade deve remover logs_mensagens"


def test_migracao_altera_associado_e_status_fatura():
    texto = _migracao_mvp()["texto"]
    assert "dia_vencimento" in texto
    assert "ATRASADA" in texto


def test_migracao_encadeada_na_inicial_com_head_unica():
    revisoes = _revisoes()
    dados = _migracao_mvp()
    assert dados["down"] == REVISAO_INICIAL or dados["down"] in revisoes

    referenciadas = {d["down"] for d in revisoes.values() if d["down"] and d["down"] != "None"}
    heads = [r for r in revisoes if r not in referenciadas]
    assert len(heads) == 1, f"Alembic deve ter uma única head, encontrado: {heads}"
