"""
Testes de endurecimento dos docker-compose (produção e desenvolvimento): preparação do banco antes da
API, worker único, segredos obrigatórios em produção e portas sensíveis restritas ao loopback.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT_DIR = Path(__file__).resolve().parents[3]


def _compose(nome: str) -> dict:
    return yaml.safe_load((ROOT_DIR / nome).read_text(encoding="utf-8"))


def _texto(nome: str) -> str:
    return (ROOT_DIR / nome).read_text(encoding="utf-8")


def test_prod_prepara_o_banco_com_scripts_migrate_antes_da_api():
    comando = _compose("docker-compose.prod.yml")["services"]["backend"]["command"]

    assert "python -m scripts.migrate" in comando
    assert "&&" in comando, "a API só pode subir se a preparação do banco tiver sucesso"
    assert comando.index("python -m scripts.migrate") < comando.index("uvicorn")
    assert "alembic upgrade head" not in comando, "a decisão create_all vs upgrade é do scripts.migrate"


def test_prod_usa_um_unico_worker_para_nao_duplicar_scheduler_e_fila():
    comando = _compose("docker-compose.prod.yml")["services"]["backend"]["command"]

    assert re.search(r"--workers 1(\s|\"|$)", comando)


@pytest.mark.parametrize("variavel", ["WHATSAPP_API_KEY", "POSTGRES_PASSWORD"])
def test_prod_exige_segredos_sem_valor_padrao(variavel):
    texto = _texto("docker-compose.prod.yml")

    assert "${" + variavel + ":?" in texto, f"{variavel} deve ser obrigatória (sintaxe :?) em produção"
    assert "${" + variavel + ":-" not in texto, f"{variavel} não pode ter valor padrão em produção"


def test_prod_engine_e_backend_usam_a_mesma_chave_obrigatoria():
    servicos = _compose("docker-compose.prod.yml")["services"]
    chave_backend = servicos["backend"]["environment"]["WHATSAPP_API_KEY"]
    chave_engine = servicos["whatsapp-engine"]["environment"]["API_KEY"]

    assert chave_backend == chave_engine
    assert chave_backend.startswith("${WHATSAPP_API_KEY:?")


def test_dev_publica_banco_e_engine_somente_no_loopback():
    servicos = _compose("docker-compose.yml")["services"]

    for nome in ("db", "whatsapp-engine"):
        portas = servicos[nome]["ports"]
        assert portas and all(str(porta).startswith("127.0.0.1:") for porta in portas), nome
