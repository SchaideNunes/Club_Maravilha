"""
Feature 4 - Testes de integração dos endpoints de WhatsApp (painel admin <-> motor Baileys).

Substitui os testes da API antiga baseada na Evolution API (/status com instance/state/connected,
/qr em HTML e /send-test), removida junto com o provedor legado.

Contrato (prefixo /api/v1/whatsapp, app/api/v1/endpoints/whatsapp.py):
- Dependência `get_provider()` (FastAPI Depends) devolve o WhatsAppProvider configurado
  (`get_whatsapp_provider()`); os testes a sobrescrevem via `app.dependency_overrides`.
- GET  /status        -> 200 {"status": "CONECTADO" | "DESCONECTADO" | "AGUARDANDO_QRCODE"}
- GET  /qrcode        -> 200 {"status": ..., "qrcode": <data URL> | null}
- POST /desconectar   -> 200 {"status": ...} (provider.logout()); provider com "error" -> 502 {"detail"}
- POST /reiniciar     -> 200 {"status": ...} (provider.restart()); provider com "error" -> 502 {"detail"}
- POST /teste-envio   body {"numero": str, "mensagem": str | null}
    envio DIRETO pelo provider (sem esperar a fila anti-ban) para o número higienizado
    (sanitize_whatsapp_number); mensagem padrão não vazia quando omitida;
    grava LogMensagem etapa TESTE (SUCESSO/ERRO, associado_id/fatura_id nulos).
    200 {"status": "SUCESSO", "destinatario", "mensagem", "message_id", "log_id"}
    número inválido -> 422 (nada enviado); provider responde status "error" -> 502 {"detail": <erro>} + log ERRO.
- GET  /logs?limit=50&etapa=&status=&associado_id=
    -> 200 lista de LogMensagemResponse (+ "associado_nome": str | null), ordenada por enviado_em DESC;
    limit padrão 50, 1..500 (fora disso 422); etapa/status inválidos -> 422.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.v1.endpoints.whatsapp import get_provider
from app.main import app
from app.models.associado import Associado, StatusAssociado
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.services.whatsapp_service import MockWhatsAppProvider
from tests.conftest import TestingSessionLocal


class ProviderFalso(MockWhatsAppProvider):
    """Provider controlável pelos testes, seguindo o contrato normalizado da interface."""

    def __init__(
        self,
        status: str = "CONECTADO",
        qrcode: Optional[str] = None,
        resposta_envio: Optional[Dict[str, Any]] = None,
        erro_operacao: Optional[str] = None,
    ) -> None:
        super().__init__()
        self.status = status
        self.qrcode = qrcode
        self.resposta_envio = resposta_envio
        self.erro_operacao = erro_operacao
        self.chamadas: List[str] = []

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        self.chamadas.append("send")
        if self.resposta_envio is not None:
            self.sent_messages.append({"phone": phone, "message": message})
            return self.resposta_envio
        record = await super().send_message(phone, message)
        record["message_id"] = "MSG-TESTE"
        return record

    async def get_connection_status(self) -> Dict[str, Any]:
        return {"status": self.status}

    async def get_qr_code(self) -> Dict[str, Any]:
        return {"status": self.status, "qrcode": self.qrcode}

    async def logout(self) -> Dict[str, Any]:
        self.chamadas.append("logout")
        if self.erro_operacao:
            return {"status": "DESCONECTADO", "error": self.erro_operacao}
        return {"status": "DESCONECTADO"}

    async def restart(self) -> Dict[str, Any]:
        self.chamadas.append("restart")
        if self.erro_operacao:
            return {"status": "DESCONECTADO", "error": self.erro_operacao}
        return {"status": "AGUARDANDO_QRCODE"}


def _usar(provider: ProviderFalso) -> ProviderFalso:
    app.dependency_overrides[get_provider] = lambda: provider
    return provider


async def _logs() -> List[LogMensagem]:
    async with TestingSessionLocal() as s:
        return list((await s.execute(select(LogMensagem))).scalars().all())


# ------------------------------------------------------------------------------
# Status e QR Code
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("status", ["CONECTADO", "DESCONECTADO", "AGUARDANDO_QRCODE"])
async def test_status(async_client: AsyncClient, status):
    _usar(ProviderFalso(status=status))

    res = await async_client.get("/api/v1/whatsapp/status")

    assert res.status_code == 200
    assert res.json()["status"] == status


async def test_status_com_provider_padrao_mock(async_client: AsyncClient):
    """Sem override, usa o provider configurado (MOCK nos testes), que se declara conectado."""
    res = await async_client.get("/api/v1/whatsapp/status")

    assert res.status_code == 200
    assert res.json()["status"] == "CONECTADO"


async def test_qrcode_aguardando_leitura(async_client: AsyncClient):
    _usar(ProviderFalso(status="AGUARDANDO_QRCODE", qrcode="data:image/png;base64,QR"))

    res = await async_client.get("/api/v1/whatsapp/qrcode")

    assert res.status_code == 200
    assert res.json() == {"status": "AGUARDANDO_QRCODE", "qrcode": "data:image/png;base64,QR"}


async def test_qrcode_quando_conectado_e_nulo(async_client: AsyncClient):
    _usar(ProviderFalso(status="CONECTADO", qrcode=None))

    res = await async_client.get("/api/v1/whatsapp/qrcode")

    assert res.status_code == 200
    assert res.json() == {"status": "CONECTADO", "qrcode": None}


# ------------------------------------------------------------------------------
# Desconectar / reiniciar
# ------------------------------------------------------------------------------
async def test_desconectar(async_client: AsyncClient):
    provider = _usar(ProviderFalso())

    res = await async_client.post("/api/v1/whatsapp/desconectar")

    assert res.status_code == 200
    assert res.json()["status"] == "DESCONECTADO"
    assert provider.chamadas == ["logout"]


async def test_reiniciar(async_client: AsyncClient):
    provider = _usar(ProviderFalso())

    res = await async_client.post("/api/v1/whatsapp/reiniciar")

    assert res.status_code == 200
    assert res.json()["status"] == "AGUARDANDO_QRCODE"
    assert provider.chamadas == ["restart"]


@pytest.mark.parametrize("rota", ["/api/v1/whatsapp/desconectar", "/api/v1/whatsapp/reiniciar"])
async def test_desconectar_e_reiniciar_com_engine_fora_do_ar_retornam_502(async_client: AsyncClient, rota):
    _usar(ProviderFalso(erro_operacao="engine fora do ar"))

    res = await async_client.post(rota)

    assert res.status_code == 502
    assert "engine fora do ar" in res.json()["detail"]


# ------------------------------------------------------------------------------
# Teste de envio
# ------------------------------------------------------------------------------
async def test_teste_envio_envia_direto_e_grava_log_teste(async_client: AsyncClient):
    provider = _usar(ProviderFalso())

    res = await async_client.post(
        "/api/v1/whatsapp/teste-envio",
        json={"numero": "(75) 99999-0001", "mensagem": "Olá! Teste do painel."},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCESSO"
    assert data["destinatario"] == "5575999990001"
    assert data["mensagem"] == "Olá! Teste do painel."
    assert data["message_id"] == "MSG-TESTE"

    assert provider.sent_messages[-1]["message"] == "Olá! Teste do painel."
    assert "".join(c for c in provider.sent_messages[-1]["phone"] if c.isdigit()) == "5575999990001"

    logs = await _logs()
    assert len(logs) == 1
    log = logs[0]
    assert str(log.id) == data["log_id"]
    assert log.etapa == EtapaRegua.TESTE
    assert log.status == StatusEnvio.SUCESSO
    assert log.destinatario == "5575999990001"
    assert log.mensagem == "Olá! Teste do painel."
    assert log.associado_id is None and log.fatura_id is None


async def test_teste_envio_sem_mensagem_usa_texto_padrao(async_client: AsyncClient):
    provider = _usar(ProviderFalso())

    res = await async_client.post("/api/v1/whatsapp/teste-envio", json={"numero": "5575999990001"})

    assert res.status_code == 200
    enviada = provider.sent_messages[-1]["message"]
    assert enviada.strip()
    assert res.json()["mensagem"] == enviada
    assert (await _logs())[0].mensagem == enviada


@pytest.mark.parametrize("numero", ["123", "abc", "", "+1 202 555 0100"])
async def test_teste_envio_numero_invalido_422_sem_envio(async_client: AsyncClient, numero):
    provider = _usar(ProviderFalso())

    res = await async_client.post("/api/v1/whatsapp/teste-envio", json={"numero": numero, "mensagem": "Oi"})

    assert res.status_code == 422
    assert provider.sent_messages == []
    assert await _logs() == []


async def test_teste_envio_falha_no_engine_retorna_502_e_grava_log_erro(async_client: AsyncClient):
    _usar(
        ProviderFalso(
            resposta_envio={
                "status": "error",
                "error": "O número 5575000000000 não possui WhatsApp",
                "http_status": 422,
            }
        )
    )

    res = await async_client.post(
        "/api/v1/whatsapp/teste-envio", json={"numero": "5575000000000", "mensagem": "Oi"}
    )

    assert res.status_code == 502
    assert "não possui WhatsApp" in res.json()["detail"]
    logs = await _logs()
    assert len(logs) == 1
    assert logs[0].etapa == EtapaRegua.TESTE
    assert logs[0].status == StatusEnvio.ERRO
    assert "não possui WhatsApp" in logs[0].erro


# ------------------------------------------------------------------------------
# Logs de disparos
# ------------------------------------------------------------------------------
async def _seed_logs(db_session) -> Associado:
    socio = Associado(
        nome="Sócia dos Logs",
        cpf="390.533.447-05",
        whatsapp="5575999990009",
        email="logs@clube.com",
        status=StatusAssociado.ATIVO,
    )
    db_session.add(socio)
    await db_session.commit()

    base = datetime(2026, 10, 1, 11, 0, tzinfo=timezone.utc)
    registros = [
        (EtapaRegua.D_MENOS_3, StatusEnvio.SUCESSO, 0, socio.id),
        (EtapaRegua.D0, StatusEnvio.ERRO, 1, socio.id),
        (EtapaRegua.D0, StatusEnvio.SUCESSO, 2, socio.id),
        (EtapaRegua.TESTE, StatusEnvio.SUCESSO, 3, None),
        (EtapaRegua.D_MAIS_7, StatusEnvio.SUCESSO, 4, socio.id),
    ]
    for etapa, status, horas, associado_id in registros:
        db_session.add(
            LogMensagem(
                associado_id=associado_id,
                destinatario="5575999990009",
                etapa=etapa,
                mensagem=f"msg {etapa.value} {horas}",
                status=status,
                erro="falhou" if status == StatusEnvio.ERRO else None,
                enviado_em=base + timedelta(hours=horas),
            )
        )
    await db_session.commit()
    return socio


async def test_logs_ordenados_do_mais_recente_para_o_mais_antigo(async_client: AsyncClient, db_session):
    socio = await _seed_logs(db_session)

    res = await async_client.get("/api/v1/whatsapp/logs")

    assert res.status_code == 200
    data = res.json()
    assert [item["etapa"] for item in data] == ["D_MAIS_7", "TESTE", "D0", "D0", "D_MENOS_3"]
    primeiro = data[0]
    assert primeiro["associado_id"] == str(socio.id)
    assert primeiro["associado_nome"] == "Sócia dos Logs"
    assert primeiro["destinatario"] == "5575999990009"
    assert primeiro["status"] == "SUCESSO"
    assert {"id", "fatura_id", "mensagem", "erro", "enviado_em"} <= set(primeiro)
    assert data[1]["associado_nome"] is None


async def test_logs_limit(async_client: AsyncClient, db_session):
    await _seed_logs(db_session)

    res = await async_client.get("/api/v1/whatsapp/logs", params={"limit": 2})

    assert res.status_code == 200
    assert [item["etapa"] for item in res.json()] == ["D_MAIS_7", "TESTE"]


async def test_logs_filtra_por_etapa_e_status(async_client: AsyncClient, db_session):
    await _seed_logs(db_session)

    por_etapa = await async_client.get("/api/v1/whatsapp/logs", params={"etapa": "D0"})
    assert [item["status"] for item in por_etapa.json()] == ["SUCESSO", "ERRO"]

    por_status = await async_client.get("/api/v1/whatsapp/logs", params={"status": "ERRO"})
    assert len(por_status.json()) == 1
    assert por_status.json()[0]["erro"] == "falhou"

    combinados = await async_client.get(
        "/api/v1/whatsapp/logs", params={"etapa": "D0", "status": "SUCESSO"}
    )
    assert len(combinados.json()) == 1


async def test_logs_filtra_por_associado(async_client: AsyncClient, db_session):
    socio = await _seed_logs(db_session)

    res = await async_client.get("/api/v1/whatsapp/logs", params={"associado_id": str(socio.id)})

    assert res.status_code == 200
    assert len(res.json()) == 4
    assert all(item["associado_id"] == str(socio.id) for item in res.json())

    vazio = await async_client.get("/api/v1/whatsapp/logs", params={"associado_id": str(uuid.uuid4())})
    assert vazio.json() == []


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 501}, {"etapa": "D_MAIS_99"}, {"status": "TALVEZ"}],
)
async def test_logs_parametros_invalidos_422(async_client: AsyncClient, params):
    res = await async_client.get("/api/v1/whatsapp/logs", params=params)
    assert res.status_code == 422
