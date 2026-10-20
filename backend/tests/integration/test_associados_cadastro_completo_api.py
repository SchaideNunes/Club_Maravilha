"""
Cadastro de Sócios - ficha completa do associado e inativação no lugar da exclusão.

Contratos:
- POST/PATCH /api/v1/associados/ aceitam (todos opcionais):
    data_nascimento (não pode ser futura), rg (<= 20), sexo (MASCULINO|FEMININO|OUTRO),
    profissao (<= 100), cep (8 dígitos, com ou sem máscara -> "00000-000"), logradouro, numero,
    complemento, bairro, cidade, uf (sigla válida, normalizada para maiúsculas), plano_id.
  Textos opcionais vazios ("   ") viram null. plano_id precisa existir e estar ativo (422);
  no PATCH, plano_id null desvincula o plano.
- A resposta traz os campos acima, `plano` ({id, nome, valor_mensalidade} | null),
  `data_inativacao` e `motivo_inativacao`.
- POST /associados/{id}/inativar {motivo?}  200 {associado, faturas_canceladas, convites_cancelados,
  reservas_canceladas} | 404 | 409 já inativo.
    * status INATIVO, data_inativacao = hoje do clube, motivo gravado;
    * cancela faturas PENDENTES ainda não vencidas (data_vencimento >= hoje); as vencidas
      continuam em aberto como dívida;
    * cancela convites EMITIDOS com visita a partir de hoje e reservas CONFIRMADAS futuras.
- POST /associados/{id}/reativar  200 associado ATIVO (limpa data/motivo) | 404 | 409 não inativo.
- DELETE /associados/{id} não existe mais (405): sócio nunca é apagado, preservando o histórico.
- PATCH não aceita status INATIVO nem tira um sócio de INATIVO (400: use inativar/reativar).
- GET /associados/ oculta INATIVOS por padrão; status=INATIVO lista somente os inativos.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core import clock
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura

URL = "/api/v1/associados/"
HOJE = date(2026, 10, 15)


@pytest.fixture(autouse=True)
def _congelar_hoje(monkeypatch):
    instante = datetime(HOJE.year, HOJE.month, HOJE.day, 12, 0, tzinfo=clock.get_clube_tz())
    monkeypatch.setattr(clock, "agora_clube", lambda: instante)


def _payload(**extra) -> dict:
    return {
        "nome": "Maria Maravilha",
        "cpf": "529.982.247-25",
        "whatsapp": "(75) 99999-9999",
        "email": "maria@maravilha.com",
        **extra,
    }


async def _criar(client: AsyncClient, **extra) -> dict:
    res = await client.post(URL, json=_payload(**extra))
    assert res.status_code == 201, res.text
    return res.json()


async def _plano(client: AsyncClient, **extra) -> dict:
    res = await client.post("/api/v1/planos/", json={"nome": "Familiar", "valor_mensalidade": "220.00", **extra})
    assert res.status_code == 201, res.text
    return res.json()


# ------------------------------------------------------------------------------
# Campos da ficha
# ------------------------------------------------------------------------------
async def test_cria_associado_com_ficha_completa(async_client: AsyncClient):
    plano = await _plano(async_client)
    socio = await _criar(
        async_client,
        data_nascimento="1985-04-12",
        rg="12.345.678-9",
        sexo="FEMININO",
        profissao="Professora",
        cep="44001000",
        logradouro="Rua das Flores",
        numero="120",
        complemento="Casa 2",
        bairro="Centro",
        cidade="Feira de Santana",
        uf="ba",
        plano_id=plano["id"],
    )

    assert socio["data_nascimento"] == "1985-04-12"
    assert socio["rg"] == "12.345.678-9"
    assert socio["sexo"] == "FEMININO"
    assert socio["profissao"] == "Professora"
    assert socio["cep"] == "44001-000"
    assert socio["uf"] == "BA"
    assert socio["cidade"] == "Feira de Santana"
    assert socio["plano"]["id"] == plano["id"]
    assert socio["plano"]["nome"] == "Familiar"
    assert Decimal(socio["plano"]["valor_mensalidade"]) == Decimal("220.00")
    assert socio["status"] == "ATIVO"
    assert socio["data_inativacao"] is None

    detalhe = (await async_client.get(f"{URL}{socio['id']}")).json()
    assert detalhe["plano"]["nome"] == "Familiar"
    assert detalhe["bairro"] == "Centro"


async def test_cadastro_minimo_continua_valido(async_client: AsyncClient):
    socio = await _criar(async_client)
    assert socio["plano"] is None
    assert socio["cep"] is None
    assert socio["data_nascimento"] is None


async def test_textos_opcionais_em_branco_viram_null(async_client: AsyncClient):
    socio = await _criar(async_client, rg="   ", complemento="", profissao=" ")
    assert socio["rg"] is None
    assert socio["complemento"] is None
    assert socio["profissao"] is None


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("cep", "4400100"),
        ("cep", "abcde-fgh"),
        ("uf", "XX"),
        ("uf", "BAH"),
        ("sexo", "M"),
        ("data_nascimento", (HOJE + timedelta(days=1)).isoformat()),
        ("rg", "1" * 21),
    ],
)
async def test_validacoes_dos_novos_campos_retornam_422(async_client: AsyncClient, campo, valor):
    res = await async_client.post(URL, json=_payload(**{campo: valor}))
    assert res.status_code == 422, res.text


async def test_plano_inexistente_ou_inativo_retorna_422(async_client: AsyncClient):
    res = await async_client.post(URL, json=_payload(plano_id=str(uuid.uuid4())))
    assert res.status_code == 422

    plano = await _plano(async_client)
    await async_client.patch(f"/api/v1/planos/{plano['id']}", json={"ativo": False})
    res = await async_client.post(URL, json=_payload(plano_id=plano["id"]))
    assert res.status_code == 422
    assert "plano" in res.json()["detail"].lower()


async def test_patch_atualiza_endereco_troca_e_remove_plano(async_client: AsyncClient):
    familiar = await _plano(async_client)
    individual = await _plano(async_client, nome="Individual", valor_mensalidade="150")
    socio = await _criar(async_client, plano_id=familiar["id"])

    res = await async_client.patch(f"{URL}{socio['id']}", json={"cep": "44.001-000", "numero": "7", "plano_id": individual["id"]})
    assert res.status_code == 200, res.text
    assert res.json()["cep"] == "44001-000"
    assert res.json()["numero"] == "7"
    assert res.json()["plano"]["nome"] == "Individual"

    res = await async_client.patch(f"{URL}{socio['id']}", json={"plano_id": None})
    assert res.status_code == 200
    assert res.json()["plano"] is None


async def test_patch_mantem_plano_ja_vinculado_mesmo_se_desativado(async_client: AsyncClient):
    plano = await _plano(async_client)
    socio = await _criar(async_client, plano_id=plano["id"])
    await async_client.patch(f"/api/v1/planos/{plano['id']}", json={"ativo": False})

    res = await async_client.patch(f"{URL}{socio['id']}", json={"nome": "Maria M. Silva", "plano_id": plano["id"]})
    assert res.status_code == 200, res.text
    assert res.json()["plano"]["id"] == plano["id"]


# ------------------------------------------------------------------------------
# Inativação e reativação
# ------------------------------------------------------------------------------
def _fatura(associado_id: str, referencia: str, vencimento: date, status: StatusFatura) -> Fatura:
    return Fatura(
        associado_id=uuid.UUID(associado_id),
        referencia_mes=referencia,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=vencimento,
        status=status,
    )


async def test_inativar_preserva_historico_e_cancela_somente_o_futuro(async_client: AsyncClient, db_session):
    socio = await _criar(async_client)
    sid = uuid.UUID(socio["id"])

    vencida = _fatura(socio["id"], "2026-09", HOJE - timedelta(days=20), StatusFatura.ATRASADA)
    paga = _fatura(socio["id"], "2026-08", HOJE - timedelta(days=50), StatusFatura.PAGO)
    a_vencer = _fatura(socio["id"], "2026-10", HOJE + timedelta(days=5), StatusFatura.PENDENTE)
    convite_passado = Convidado(associado_titular_id=sid, nome="Visita Antiga", data_visita=HOJE - timedelta(days=3),
                                status=StatusConvidado.UTILIZADO)
    convite_futuro = Convidado(associado_titular_id=sid, nome="Visita Futura", data_visita=HOJE + timedelta(days=2),
                               status=StatusConvidado.EMITIDO)
    inicio = datetime(HOJE.year, HOJE.month, HOJE.day, 18, 0, tzinfo=timezone.utc) + timedelta(days=1)
    reserva_futura = AgendamentoQuadra(associado_id=sid, quadra=list(TipoQuadra)[0], data_inicio=inicio,
                                       data_fim=inicio + timedelta(hours=1), status=StatusAgendamento.CONFIRMADO)
    db_session.add_all([vencida, paga, a_vencer, convite_passado, convite_futuro, reserva_futura])
    await db_session.commit()
    ids = {"passado": convite_passado.id, "futuro": convite_futuro.id, "reserva": reserva_futura.id}

    res = await async_client.post(f"{URL}{socio['id']}/inativar", json={"motivo": "Mudou de cidade"})
    assert res.status_code == 200, res.text
    corpo = res.json()
    assert corpo["associado"]["status"] == "INATIVO"
    assert corpo["associado"]["data_inativacao"] == HOJE.isoformat()
    assert corpo["associado"]["motivo_inativacao"] == "Mudou de cidade"
    assert corpo["faturas_canceladas"] == 1
    assert corpo["convites_cancelados"] == 1
    assert corpo["reservas_canceladas"] == 1

    status_faturas = dict((await db_session.execute(
        select(Fatura.referencia_mes, Fatura.status).where(Fatura.associado_id == sid))).all())
    assert status_faturas == {
        "2026-09": StatusFatura.ATRASADA,
        "2026-08": StatusFatura.PAGO,
        "2026-10": StatusFatura.CANCELADO,
    }
    status_convites = dict((await db_session.execute(
        select(Convidado.id, Convidado.status).where(Convidado.associado_titular_id == sid))).all())
    assert status_convites == {ids["passado"]: StatusConvidado.UTILIZADO, ids["futuro"]: StatusConvidado.CANCELADO}
    status_reserva = await db_session.scalar(
        select(AgendamentoQuadra.status).where(AgendamentoQuadra.id == ids["reserva"]))
    assert status_reserva == StatusAgendamento.CANCELADO

    # O sócio continua existindo com todo o histórico
    assert (await async_client.get(f"{URL}{socio['id']}")).status_code == 200


async def test_inativar_duas_vezes_retorna_409_e_inexistente_404(async_client: AsyncClient):
    socio = await _criar(async_client)
    assert (await async_client.post(f"{URL}{socio['id']}/inativar", json={})).status_code == 200
    assert (await async_client.post(f"{URL}{socio['id']}/inativar", json={})).status_code == 409
    assert (await async_client.post(f"{URL}{uuid.uuid4()}/inativar", json={})).status_code == 404


async def test_reativar_volta_para_ativo_e_limpa_motivo(async_client: AsyncClient):
    socio = await _criar(async_client)
    assert (await async_client.post(f"{URL}{socio['id']}/reativar")).status_code == 409

    await async_client.post(f"{URL}{socio['id']}/inativar", json={"motivo": "Pausa"})
    res = await async_client.post(f"{URL}{socio['id']}/reativar")
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "ATIVO"
    assert res.json()["data_inativacao"] is None
    assert res.json()["motivo_inativacao"] is None

    assert (await async_client.post(f"{URL}{uuid.uuid4()}/reativar")).status_code == 404


async def test_delete_nao_existe_mais(async_client: AsyncClient):
    socio = await _criar(async_client)
    assert (await async_client.delete(f"{URL}{socio['id']}")).status_code == 405
    assert (await async_client.get(f"{URL}{socio['id']}")).status_code == 200


async def test_patch_nao_inativa_nem_reativa(async_client: AsyncClient):
    socio = await _criar(async_client)
    res = await async_client.patch(f"{URL}{socio['id']}", json={"status": "INATIVO"})
    assert res.status_code == 400

    await async_client.post(f"{URL}{socio['id']}/inativar", json={})
    res = await async_client.patch(f"{URL}{socio['id']}", json={"status": "ATIVO"})
    assert res.status_code == 400

    # Dados cadastrais de um inativo continuam editáveis
    res = await async_client.patch(f"{URL}{socio['id']}", json={"profissao": "Aposentada"})
    assert res.status_code == 200
    assert res.json()["status"] == "INATIVO"


async def test_listagem_oculta_inativos_por_padrao(async_client: AsyncClient):
    ativo = await _criar(async_client)
    inativo = await _criar(async_client, nome="Ivo Inativo", cpf="111.444.777-35", email="ivo@x.com")
    await async_client.post(f"{URL}{inativo['id']}/inativar", json={})

    padrao = (await async_client.get(URL)).json()
    assert [s["id"] for s in padrao["items"]] == [ativo["id"]]
    assert padrao["total"] == 1

    so_inativos = (await async_client.get(URL, params={"status": "INATIVO"})).json()
    assert [s["id"] for s in so_inativos["items"]] == [inativo["id"]]


async def test_dashboard_nao_conta_inativos(async_client: AsyncClient):
    await _criar(async_client)
    inativo = await _criar(async_client, nome="Ivo Inativo", cpf="111.444.777-35", email="ivo@x.com")
    await async_client.post(f"{URL}{inativo['id']}/inativar", json={})

    dados = (await async_client.get("/api/v1/dashboard/resumo")).json()
    assert dados["total_associados"] == 1
