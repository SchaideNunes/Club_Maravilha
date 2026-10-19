"""
Feature 6 - API da Central de Configurações do clube (`app/api/v1/endpoints/configuracao.py`).

Contratos HTTP (todas as rotas sob o admin_router -> exigem Bearer JWT; sem token -> 401):
- GET   /api/v1/configuracao
    -> 200 ConfiguracaoResponse (usa ConfiguracaoRepository.get_or_create: cria com os defaults
       quando ainda não existe). Decimais serializados como string ("150.00").
- PATCH /api/v1/configuracao   body ConfiguracaoUpdate (parcial; só os campos enviados mudam)
    -> 200 ConfiguracaoResponse atualizado e persistido (GET seguinte reflete a mudança).
    -> 422 para template inválido (variável desconhecida, chave sem par, vazio), horário fora de
       HH:MM 24h, valores negativos e null em campo NOT NULL (chave_pix aceita null).
    -> quando `horario_disparo` é enviado com valor DIFERENTE do atual, chama
       `app.jobs.billing_scheduler.reagendar_regua(novo_horario)` (acessado pelo módulo, para poder
       ser trocado via monkeypatch) DEPOIS de persistir. Sem mudança de horário -> não chama.
    -> `automacao_ativa` persistido é respeitado no próximo processamento da régua
       (POST /api/v1/faturas/executar-regua devolve automacao_ativa=false e não enfileira nada).
- POST  /api/v1/configuracao/preview-template   body {"template": str, "fatura_id": uuid | null}
    -> 200 {"mensagem": str} renderizada com `template_service.renderizar_template`:
       * com fatura_id: variáveis reais de `variaveis_da_fatura(fatura, associado, configuracao)`;
       * sem fatura_id: dados de exemplo coerentes com a Configuracao atual — valor_base =
         valor_mensalidade, convites_extras = max(0, convites_usados - franquia_convidados),
         valor_total = valor_base + convites_extras * valor_convidado_extra (moeda "R$ x,yy"),
         vencimento "dd/mm/aaaa", chave_pix = chave da configuração; nenhuma variável fica sem valor.
    -> 422 template inválido (mesma validação de ConfiguracaoUpdate: `validar_template`, não vazio).
    -> 404 fatura_id inexistente.
"""
import re
import uuid
from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.jobs import billing_scheduler
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.configuracao_repository import ConfiguracaoRepository

API = "/api/v1/configuracao"

CAMPOS_RESPOSTA = {
    "id",
    "valor_mensalidade",
    "franquia_convidados",
    "valor_convidado_extra",
    "chave_pix",
    "horario_disparo",
    "automacao_ativa",
    "template_d_menos_3",
    "template_d0",
    "template_recibo",
    "template_d_mais_3",
    "template_d_mais_7",
    "updated_at",
}


@pytest.fixture
def chamadas_reagendar(monkeypatch):
    """Substitui billing_scheduler.reagendar_regua por um gravador de chamadas."""
    chamadas: list[str] = []

    def _fake(horario: str) -> bool:
        chamadas.append(horario)
        return True

    monkeypatch.setattr(billing_scheduler, "reagendar_regua", _fake)
    return chamadas


async def _configurar(session, **campos):
    cfg = await ConfiguracaoRepository(session).get_or_create()
    for chave, valor in campos.items():
        setattr(cfg, chave, valor)
    await session.commit()
    return cfg


# ---------------------------------------------------------------------------
# GET /configuracao
# ---------------------------------------------------------------------------

async def test_get_configuracao_cria_com_defaults_quando_nao_existe(async_client: AsyncClient):
    res = await async_client.get(API)

    assert res.status_code == 200
    corpo = res.json()
    assert CAMPOS_RESPOSTA <= set(corpo)
    assert corpo["id"] == 1
    assert corpo["franquia_convidados"] == 8
    assert corpo["horario_disparo"] == "08:00"
    assert corpo["automacao_ativa"] is True
    assert "{nome}" in corpo["template_d0"]
    assert isinstance(corpo["valor_mensalidade"], str)
    Decimal(corpo["valor_mensalidade"])  # serializado como Decimal em string


async def test_get_configuracao_reflete_valores_salvos(async_client: AsyncClient, db_session):
    await _configurar(
        db_session,
        valor_mensalidade=Decimal("199.90"),
        chave_pix="financeiro@clubmaravilha.com.br",
        horario_disparo="07:15",
    )

    res = await async_client.get(API)

    assert res.status_code == 200
    corpo = res.json()
    assert Decimal(corpo["valor_mensalidade"]) == Decimal("199.90")
    assert corpo["chave_pix"] == "financeiro@clubmaravilha.com.br"
    assert corpo["horario_disparo"] == "07:15"


# ---------------------------------------------------------------------------
# PATCH /configuracao
# ---------------------------------------------------------------------------

async def test_patch_parcial_altera_somente_campos_enviados(
    async_client: AsyncClient, db_session, chamadas_reagendar
):
    await _configurar(db_session, valor_mensalidade=Decimal("150.00"), chave_pix="antiga@pix")
    antes = (await async_client.get(API)).json()

    res = await async_client.patch(API, json={"valor_mensalidade": "180.50", "franquia_convidados": 10})

    assert res.status_code == 200
    corpo = res.json()
    assert Decimal(corpo["valor_mensalidade"]) == Decimal("180.50")
    assert corpo["franquia_convidados"] == 10
    for campo in ("chave_pix", "horario_disparo", "automacao_ativa", "template_d0", "valor_convidado_extra"):
        assert corpo[campo] == antes[campo]

    persistido = (await async_client.get(API)).json()
    assert Decimal(persistido["valor_mensalidade"]) == Decimal("180.50")
    assert persistido["franquia_convidados"] == 10
    assert chamadas_reagendar == []


async def test_patch_templates_e_chave_pix(async_client: AsyncClient, chamadas_reagendar):
    payload = {
        "template_d_menos_3": "Oi {nome}, vence em {vencimento}: {valor_total}",
        "template_d0": "Hoje vence! Pix: {chave_pix}",
        "template_recibo": "Recebemos {valor_total}, {nome}. Obrigado!",
        "template_d_mais_3": "{nome}, sua fatura de {vencimento} está em aberto.",
        "template_d_mais_7": "{nome}, acesso bloqueado. Total {valor_total} ({convites_extras} extras, base {valor_base}, usados {convites_usados}).",
        "chave_pix": "novo@pix.com",
    }

    res = await async_client.patch(API, json=payload)

    assert res.status_code == 200
    corpo = res.json()
    for campo, valor in payload.items():
        assert corpo[campo] == valor
    assert (await async_client.get(API)).json()["template_d0"] == payload["template_d0"]


async def test_patch_corpo_vazio_nao_altera_nada(async_client: AsyncClient, chamadas_reagendar):
    antes = (await async_client.get(API)).json()

    res = await async_client.patch(API, json={})

    assert res.status_code == 200
    depois = res.json()
    antes.pop("updated_at")
    depois.pop("updated_at")
    assert depois == antes
    assert chamadas_reagendar == []


async def test_patch_chave_pix_aceita_null(async_client: AsyncClient, db_session, chamadas_reagendar):
    await _configurar(db_session, chave_pix="algo@pix")

    res = await async_client.patch(API, json={"chave_pix": None})

    assert res.status_code == 200
    assert res.json()["chave_pix"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"template_d0": "Olá {nom}"},
        {"template_d_menos_3": "Chave sem par { aqui"},
        {"template_recibo": "   "},
        {"template_d_mais_7": "Posicional {0}"},
        {"horario_disparo": "25:00"},
        {"horario_disparo": "8:00"},
        {"horario_disparo": "08:60"},
        {"valor_mensalidade": "-1.00"},
        {"valor_convidado_extra": "-0.01"},
        {"franquia_convidados": -1},
        {"template_d0": None},
        {"horario_disparo": None},
        {"automacao_ativa": None},
        {"valor_mensalidade": None},
    ],
)
async def test_patch_invalido_retorna_422_e_nao_persiste(
    async_client: AsyncClient, chamadas_reagendar, payload
):
    antes = (await async_client.get(API)).json()

    res = await async_client.patch(API, json=payload)

    assert res.status_code == 422
    assert "detail" in res.json()
    depois = (await async_client.get(API)).json()
    antes.pop("updated_at")
    depois.pop("updated_at")
    assert depois == antes
    assert chamadas_reagendar == []


async def test_patch_horario_reagenda_regua(async_client: AsyncClient, db_session, chamadas_reagendar):
    await _configurar(db_session, horario_disparo="08:00")

    res = await async_client.patch(API, json={"horario_disparo": "09:30"})

    assert res.status_code == 200
    assert res.json()["horario_disparo"] == "09:30"
    assert chamadas_reagendar == ["09:30"]
    assert (await async_client.get(API)).json()["horario_disparo"] == "09:30"


async def test_patch_mesmo_horario_nao_reagenda(async_client: AsyncClient, db_session, chamadas_reagendar):
    await _configurar(db_session, horario_disparo="08:00")

    res = await async_client.patch(API, json={"horario_disparo": "08:00", "chave_pix": "x@pix"})

    assert res.status_code == 200
    assert chamadas_reagendar == []


async def test_patch_sem_horario_nao_reagenda(async_client: AsyncClient, chamadas_reagendar):
    res = await async_client.patch(API, json={"automacao_ativa": False})

    assert res.status_code == 200
    assert chamadas_reagendar == []


async def test_patch_automacao_ativa_reflete_no_processamento_da_regua(
    async_client: AsyncClient, chamadas_reagendar
):
    res = await async_client.patch(API, json={"automacao_ativa": False})
    assert res.status_code == 200
    assert res.json()["automacao_ativa"] is False

    regua = await async_client.post("/api/v1/faturas/executar-regua")
    assert regua.status_code == 200
    assert regua.json()["automacao_ativa"] is False
    assert regua.json()["total_enfileirados"] == 0

    res = await async_client.patch(API, json={"automacao_ativa": True})
    assert res.status_code == 200

    regua = await async_client.post("/api/v1/faturas/executar-regua")
    assert regua.status_code == 200
    assert regua.json()["automacao_ativa"] is True


# ---------------------------------------------------------------------------
# POST /configuracao/preview-template
# ---------------------------------------------------------------------------

def _moeda(texto: str) -> Decimal:
    """Converte "R$ 1.234,56" em Decimal("1234.56")."""
    limpo = texto.replace("R$", "").replace("\xa0", "").strip().replace(".", "").replace(",", ".")
    return Decimal(limpo)


async def test_preview_sem_fatura_usa_dados_de_exemplo_coerentes(async_client: AsyncClient, db_session):
    await _configurar(
        db_session,
        valor_mensalidade=Decimal("150.00"),
        valor_convidado_extra=Decimal("35.00"),
        franquia_convidados=8,
        chave_pix="financeiro@clubmaravilha.com.br",
    )
    template = "{nome}|{valor_base}|{convites_usados}|{convites_extras}|{valor_total}|{vencimento}|{chave_pix}"

    res = await async_client.post(f"{API}/preview-template", json={"template": template})

    assert res.status_code == 200
    mensagem = res.json()["mensagem"]
    assert "{" not in mensagem and "}" not in mensagem
    nome, base, usados, extras, total, vencimento, chave = mensagem.split("|")
    assert nome.strip()
    assert _moeda(base) == Decimal("150.00")
    assert int(extras) == max(0, int(usados) - 8)
    assert _moeda(total) == _moeda(base) + int(extras) * Decimal("35.00")
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", vencimento)
    assert chave == "financeiro@clubmaravilha.com.br"


async def test_preview_preserva_texto_livre(async_client: AsyncClient):
    res = await async_client.post(
        f"{API}/preview-template", json={"template": "Olá {nome}! Texto fixo sem mudanças.", "fatura_id": None}
    )

    assert res.status_code == 200
    mensagem = res.json()["mensagem"]
    assert mensagem.startswith("Olá ")
    assert mensagem.endswith("! Texto fixo sem mudanças.")
    assert "{nome}" not in mensagem


async def test_preview_com_fatura_usa_dados_reais(async_client: AsyncClient, db_session):
    await _configurar(db_session, chave_pix="pix@clube.com")
    socio = Associado(
        nome="Carla Mendes",
        cpf="000.000.001-00",
        whatsapp="5575999990001",
        email="carla@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=10,
        data_adesao=date(2025, 1, 1),
    )
    db_session.add(socio)
    await db_session.flush()
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-11",
        valor_base=Decimal("150.00"),
        valor_convidados_excedentes=Decimal("70.00"),
        valor_total=Decimal("220.00"),
        convites_usados=10,
        convites_extras=2,
        data_vencimento=date(2026, 11, 10),
        status=StatusFatura.PENDENTE,
    )
    db_session.add(fatura)
    await db_session.commit()

    res = await async_client.post(
        f"{API}/preview-template",
        json={
            "template": "{nome}|{valor_base}|{convites_usados}|{convites_extras}|{valor_total}|{vencimento}|{chave_pix}",
            "fatura_id": str(fatura.id),
        },
    )

    assert res.status_code == 200
    assert res.json() == {
        "mensagem": "Carla Mendes|R$ 150,00|10|2|R$ 220,00|10/11/2026|pix@clube.com"
    }


@pytest.mark.parametrize("template", ["Olá {nom}", "Chave { solta", "", "   ", "{nome!r}"])
async def test_preview_template_invalido_retorna_422(async_client: AsyncClient, template):
    res = await async_client.post(f"{API}/preview-template", json={"template": template})

    assert res.status_code == 422
    assert "detail" in res.json()


async def test_preview_sem_template_retorna_422(async_client: AsyncClient):
    res = await async_client.post(f"{API}/preview-template", json={})
    assert res.status_code == 422


async def test_preview_fatura_inexistente_retorna_404(async_client: AsyncClient):
    res = await async_client.post(
        f"{API}/preview-template", json={"template": "Olá {nome}", "fatura_id": str(uuid.uuid4())}
    )
    assert res.status_code == 404
    assert "não encontrad" in res.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Proteção (admin)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "metodo,caminho,corpo",
    [
        ("GET", API, None),
        ("PATCH", API, {"chave_pix": "x"}),
        ("POST", f"{API}/preview-template", {"template": "Olá {nome}"}),
    ],
)
async def test_rotas_de_configuracao_exigem_admin(async_client_sem_auth: AsyncClient, metodo, caminho, corpo):
    res = await async_client_sem_auth.request(metodo, caminho, json=corpo)

    assert res.status_code == 401
    assert res.headers.get("www-authenticate", "").lower().startswith("bearer")
