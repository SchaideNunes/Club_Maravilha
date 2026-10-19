"""
Feature 4 - Testes do BaileysWhatsAppProvider (backend -> whatsapp-engine via HTTP), sem rede.

Contrato (app/services/whatsapp_service.py):
- `StatusConexaoWhatsApp(str, Enum)`: CONECTADO, DESCONECTADO, AGUARDANDO_QRCODE.
- `mapear_estado_engine(state) -> StatusConexaoWhatsApp`: "open" -> CONECTADO, "connecting" -> AGUARDANDO_QRCODE,
  qualquer outro valor (inclusive "close", None, desconhecido) -> DESCONECTADO.
- `BaileysWhatsAppProvider(base_url=None, api_key=None, client=None)` implementa `WhatsAppProvider`;
  defaults vêm de `settings.WHATSAPP_ENGINE_URL` / `settings.WHATSAPP_API_KEY`; barra final da URL é ignorada.
  Toda requisição envia o header `x-api-key`. Nenhum método lança exceção por erro HTTP/rede.
  * send_message(phone, message): POST {base}/send JSON {"numero": <só dígitos com DDI 55>, "mensagem": message}
      200 {id, jid} -> {"status": "success", "provider": "BaileysWhatsAppProvider", "phone", "message_id", "jid"}
      erro HTTP     -> {"status": "error", "provider", "phone", "error": <campo "error" do engine ou texto>,
                        "http_status": <código>, "code": <campo "code" do engine ou None>}
      erro de rede  -> {"status": "error", ..., "error": <descrição>, "http_status": None}
  * get_connection_status(): GET {base}/status -> {"status": <StatusConexaoWhatsApp>, "state": <state do engine>};
      erro HTTP/rede -> {"status": "DESCONECTADO", "error": <descrição>}
  * get_qr_code(): GET {base}/qr -> {"status", "qrcode": <data URL ou None>}; erro -> DESCONECTADO, qrcode None, "error".
  * logout(): POST {base}/logout; restart(): POST {base}/restart -> {"status": mapeado do state}; erro -> + "error".
- `get_whatsapp_provider("BAILEYS")` -> BaileysWhatsAppProvider configurado pelo settings.
"""
import json
from typing import Callable, List

import httpx
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.services.whatsapp_queue_service import LogContext, WhatsAppQueueService
from app.services.whatsapp_service import (
    BaileysWhatsAppProvider,
    StatusConexaoWhatsApp,
    WhatsAppProvider,
    get_whatsapp_provider,
    mapear_estado_engine,
)
from tests.conftest import TestingSessionLocal

BASE_URL = "http://engine:3001"
API_KEY = "chave-engine-teste"


def _provider(handler: Callable[[httpx.Request], httpx.Response], requests: List[httpx.Request] = None):
    def _registrar(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        return handler(request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(_registrar))
    return BaileysWhatsAppProvider(base_url=BASE_URL, api_key=API_KEY, client=client)


def _falha_de_rede(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("engine fora do ar", request=request)


# ------------------------------------------------------------------------------
# Mapeamento de estado
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "state,esperado",
    [
        ("open", StatusConexaoWhatsApp.CONECTADO),
        ("connecting", StatusConexaoWhatsApp.AGUARDANDO_QRCODE),
        ("close", StatusConexaoWhatsApp.DESCONECTADO),
        ("refused", StatusConexaoWhatsApp.DESCONECTADO),
        (None, StatusConexaoWhatsApp.DESCONECTADO),
    ],
)
def test_mapear_estado_engine(state, esperado):
    assert mapear_estado_engine(state) == esperado


def test_status_conexao_tem_os_valores_do_contrato():
    assert {s.value for s in StatusConexaoWhatsApp} == {"CONECTADO", "DESCONECTADO", "AGUARDANDO_QRCODE"}


def test_baileys_provider_implementa_a_interface():
    assert issubclass(BaileysWhatsAppProvider, WhatsAppProvider)


# ------------------------------------------------------------------------------
# send_message
# ------------------------------------------------------------------------------
async def test_send_message_posta_no_engine_com_api_key_e_numero_normalizado():
    requests: List[httpx.Request] = []
    provider = _provider(
        lambda r: httpx.Response(200, json={"id": "MSG1", "jid": "5575999999999@s.whatsapp.net"}),
        requests,
    )

    res = await provider.send_message("+55 (75) 99999-9999", "Olá, sócio!")

    assert len(requests) == 1
    req = requests[0]
    assert req.method == "POST"
    assert str(req.url) == f"{BASE_URL}/send"
    assert req.headers["x-api-key"] == API_KEY
    assert json.loads(req.content) == {"numero": "5575999999999", "mensagem": "Olá, sócio!"}

    assert res["status"] == "success"
    assert res["provider"] == "BaileysWhatsAppProvider"
    assert res["phone"] == "5575999999999"
    assert res["message_id"] == "MSG1"
    assert res["jid"] == "5575999999999@s.whatsapp.net"


async def test_barra_final_da_base_url_e_ignorada():
    requests: List[httpx.Request] = []
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: requests.append(r) or httpx.Response(200, json={"id": None, "jid": "x@s.whatsapp.net"})
        )
    )
    provider = BaileysWhatsAppProvider(base_url=f"{BASE_URL}/", api_key=API_KEY, client=client)

    await provider.send_message("75999999999", "Oi")

    assert str(requests[0].url) == f"{BASE_URL}/send"


async def test_send_message_numero_sem_whatsapp_422_vira_erro_com_mensagem():
    provider = _provider(
        lambda r: httpx.Response(
            422,
            json={"error": "O número 5575000000000 não possui WhatsApp", "code": "NUMERO_SEM_WHATSAPP"},
        )
    )

    res = await provider.send_message("5575000000000", "Oi")

    assert res["status"] == "error"
    assert res["http_status"] == 422
    assert res["code"] == "NUMERO_SEM_WHATSAPP"
    assert "não possui WhatsApp" in res["error"]


async def test_send_message_engine_desconectado_503_vira_erro_com_mensagem():
    provider = _provider(
        lambda r: httpx.Response(503, json={"error": "WhatsApp desconectado", "code": "WHATSAPP_DESCONECTADO"})
    )

    res = await provider.send_message("5575999999999", "Oi")

    assert res["status"] == "error"
    assert res["http_status"] == 503
    assert res["code"] == "WHATSAPP_DESCONECTADO"
    assert "desconectado" in res["error"].lower()


@pytest.mark.parametrize("codigo", [400, 401, 500])
async def test_send_message_outros_erros_http_nao_lancam(codigo):
    provider = _provider(lambda r: httpx.Response(codigo, text="falha sem json"))

    res = await provider.send_message("5575999999999", "Oi")

    assert res["status"] == "error"
    assert res["http_status"] == codigo
    assert res["error"]


@pytest.mark.parametrize(
    "excecao",
    [
        lambda r: httpx.ConnectError("engine fora do ar", request=r),
        lambda r: httpx.ReadTimeout("demorou", request=r),
    ],
)
async def test_send_message_erro_de_rede_vira_erro_sem_lancar(excecao):
    def handler(request):
        raise excecao(request)

    provider = _provider(handler)

    res = await provider.send_message("5575999999999", "Oi")

    assert res["status"] == "error"
    assert res["http_status"] is None
    assert res["error"]


async def test_fila_grava_log_erro_com_a_mensagem_do_engine(db_session):
    provider = _provider(
        lambda r: httpx.Response(
            422,
            json={"error": "O número 5575000000000 não possui WhatsApp", "code": "NUMERO_SEM_WHATSAPP"},
        )
    )
    fila = WhatsAppQueueService(
        provider=provider, min_delay_seconds=0.0, max_delay_seconds=0.0, session_factory=TestingSessionLocal
    )

    await fila.enqueue("5575000000000", "Cobrança", log_context=LogContext(etapa=EtapaRegua.TESTE))
    await fila.process_one()

    async with TestingSessionLocal() as s:
        logs = list((await s.execute(select(LogMensagem))).scalars().all())
    assert len(logs) == 1
    assert logs[0].status == StatusEnvio.ERRO
    assert "não possui WhatsApp" in logs[0].erro


# ------------------------------------------------------------------------------
# Status / QR / logout / restart
# ------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "state,esperado",
    [("open", "CONECTADO"), ("connecting", "AGUARDANDO_QRCODE"), ("close", "DESCONECTADO")],
)
async def test_get_connection_status_mapeia_estado(state, esperado):
    requests: List[httpx.Request] = []
    provider = _provider(lambda r: httpx.Response(200, json={"state": state}), requests)

    res = await provider.get_connection_status()

    assert res["status"] == esperado
    assert res["state"] == state
    assert requests[0].method == "GET"
    assert str(requests[0].url) == f"{BASE_URL}/status"
    assert requests[0].headers["x-api-key"] == API_KEY


async def test_get_connection_status_erro_de_rede_e_desconectado():
    res = await _provider(_falha_de_rede).get_connection_status()

    assert res["status"] == "DESCONECTADO"
    assert res["error"]


async def test_get_connection_status_api_key_recusada_e_desconectado():
    res = await _provider(lambda r: httpx.Response(401, json={"error": "Não autorizado"})).get_connection_status()

    assert res["status"] == "DESCONECTADO"
    assert res["error"]


async def test_get_qr_code_aguardando_leitura():
    requests: List[httpx.Request] = []
    provider = _provider(
        lambda r: httpx.Response(200, json={"state": "connecting", "qrcode": "data:image/png;base64,QR"}),
        requests,
    )

    res = await provider.get_qr_code()

    assert res["status"] == "AGUARDANDO_QRCODE"
    assert res["qrcode"] == "data:image/png;base64,QR"
    assert str(requests[0].url) == f"{BASE_URL}/qr"
    assert requests[0].headers["x-api-key"] == API_KEY


async def test_get_qr_code_conectado_nao_tem_qr():
    provider = _provider(lambda r: httpx.Response(200, json={"state": "open", "qrcode": None}))

    res = await provider.get_qr_code()

    assert res["status"] == "CONECTADO"
    assert res["qrcode"] is None


async def test_get_qr_code_erro_de_rede():
    res = await _provider(_falha_de_rede).get_qr_code()

    assert res["status"] == "DESCONECTADO"
    assert res["qrcode"] is None
    assert res["error"]


async def test_logout_posta_no_engine():
    requests: List[httpx.Request] = []
    provider = _provider(lambda r: httpx.Response(200, json={"state": "close"}), requests)

    res = await provider.logout()

    assert res["status"] == "DESCONECTADO"
    assert "error" not in res
    assert requests[0].method == "POST"
    assert str(requests[0].url) == f"{BASE_URL}/logout"
    assert requests[0].headers["x-api-key"] == API_KEY


async def test_restart_posta_no_engine():
    requests: List[httpx.Request] = []
    provider = _provider(lambda r: httpx.Response(200, json={"state": "connecting"}), requests)

    res = await provider.restart()

    assert res["status"] == "AGUARDANDO_QRCODE"
    assert requests[0].method == "POST"
    assert str(requests[0].url) == f"{BASE_URL}/restart"


@pytest.mark.parametrize("metodo", ["logout", "restart"])
async def test_logout_e_restart_com_engine_fora_do_ar_retornam_erro(metodo):
    res = await getattr(_provider(_falha_de_rede), metodo)()

    assert res["error"]


# ------------------------------------------------------------------------------
# Factory
# ------------------------------------------------------------------------------
@pytest.mark.parametrize("valor", ["BAILEYS", "baileys", "  Baileys "])
def test_factory_baileys_usa_url_e_chave_do_settings(monkeypatch, valor):
    monkeypatch.setattr(settings, "WHATSAPP_ENGINE_URL", "http://whatsapp-engine:3001")
    monkeypatch.setattr(settings, "WHATSAPP_API_KEY", "chave-do-settings")

    provider = get_whatsapp_provider(valor)

    assert isinstance(provider, BaileysWhatsAppProvider)
    assert provider.base_url == "http://whatsapp-engine:3001"
    assert provider.api_key == "chave-do-settings"


def test_factory_sem_argumento_com_settings_baileys(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_PROVIDER", "BAILEYS")
    assert isinstance(get_whatsapp_provider(), BaileysWhatsAppProvider)

