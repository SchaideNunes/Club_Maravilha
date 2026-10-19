"""
Serviço de Mensageria WhatsApp desacoplado com suporte ao motor Baileys e Mock para testes.
"""
import logging
import re
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def normalize_whatsapp_number(phone: str) -> str:
    """
    Normaliza o número de telefone removendo pontuação e garantindo o DDI 55 (Brasil).
    Exemplos:
    - '+55 (11) 98888-7777' -> '5511988887777'
    - '11988887777' -> '5511988887777'
    - '5511988887777' -> '5511988887777'
    """
    digits = re.sub(r"\D", "", phone)
    if len(digits) in (10, 11) and not digits.startswith("55"):
        digits = f"55{digits}"
    return digits


class StatusConexaoWhatsApp(str, Enum):
    CONECTADO = "CONECTADO"
    DESCONECTADO = "DESCONECTADO"
    AGUARDANDO_QRCODE = "AGUARDANDO_QRCODE"


def mapear_estado_engine(state: Optional[str]) -> StatusConexaoWhatsApp:
    """
    Mapeia os estados do motor Baileys (open, connecting, close, etc.)
    para os estados normalizados da aplicação.
    """
    if state == "open":
        return StatusConexaoWhatsApp.CONECTADO
    if state == "connecting":
        return StatusConexaoWhatsApp.AGUARDANDO_QRCODE
    return StatusConexaoWhatsApp.DESCONECTADO


class WhatsAppMessageBuilder:
    """Gerador de templates de mensagens amigáveis e padronizadas para o WhatsApp."""

    @staticmethod
    def build_d_minus_3(nome: str, valor: Decimal, data_vencimento: date) -> str:
        venc_str = data_vencimento.strftime("%d/%m/%Y")
        return (
            f"Olá, {nome}! Lembramos que sua mensalidade do Club Maravilha vence em 3 dias ({venc_str}).\n"
            f"Valor: R$ {valor:.2f}.\n"
            f"Evite filas e garanta seu acesso contínuo às quadras e dependências do clube!"
        )

    @staticmethod
    def build_d_zero(nome: str, valor: Decimal, data_vencimento: date, pix_copia_cola: str) -> str:
        venc_str = data_vencimento.strftime("%d/%m/%Y")
        return (
            f"Bom dia, {nome}! Sua mensalidade do Club Maravilha vence hoje ({venc_str}).\n"
            f"Valor: R$ {valor:.2f}.\n\n"
            f"Pix Copia e Cola:\n"
            f"{pix_copia_cola}\n\n"
            f"Após o pagamento, a liberação do seu acesso na catraca facial é automática!"
        )

    @staticmethod
    def build_pos_pagamento(nome: str, valor: Decimal, referencia_mes: str) -> str:
        return (
            f"Olá, {nome}! Confirmamos o pagamento da sua mensalidade referente a {referencia_mes} "
            f"no valor de R$ {valor:.2f}.\n"
            f"Seu acesso à catraca facial está 100% LIBERADO!\n"
            f"Desejamos um excelente treino e momentos de lazer no Club Maravilha!"
        )

    @staticmethod
    def build_d_plus_3(nome: str, valor: Decimal, data_vencimento: date, pix_copia_cola: str) -> str:
        venc_str = data_vencimento.strftime("%d/%m/%Y")
        return (
            f"Olá, {nome}! Sua mensalidade do Club Maravilha está vencida há 3 dias ({venc_str}).\n"
            f"Valor: R$ {valor:.2f}.\n"
            f"Pague agora via Pix Copia e Cola para regularizar seu cadastro:\n\n"
            f"{pix_copia_cola}"
        )

    @staticmethod
    def build_d_plus_7(nome: str, valor: Decimal, data_vencimento: date, pix_copia_cola: str) -> str:
        venc_str = data_vencimento.strftime("%d/%m/%Y")
        return (
            f"Atenção, {nome}! Sua mensalidade está vencida há 7 dias ({venc_str}).\n"
            f"Valor: R$ {valor:.2f}.\n"
            f"Seu acesso à catraca facial será BLOQUEADO temporariamente até a regularização.\n"
            f"Pague agora via Pix para restabelecer seu acesso imediato:\n\n"
            f"{pix_copia_cola}"
        )


class WhatsAppProvider(ABC):
    @abstractmethod
    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        """Envia mensagem de texto para o número especificado."""
        pass

    @abstractmethod
    async def get_connection_status(self) -> Dict[str, Any]:
        """Consulta o estado da conexão da instância com o WhatsApp."""
        pass

    @abstractmethod
    async def get_qr_code(self) -> Dict[str, Any]:
        """Obtém o QR Code para pareamento do WhatsApp."""
        pass

    @abstractmethod
    async def logout(self) -> Dict[str, Any]:
        """Desconecta a sessão ativa do WhatsApp."""
        pass

    @abstractmethod
    async def restart(self) -> Dict[str, Any]:
        """Reinicia a conexão do WhatsApp."""
        pass


class MockWhatsAppProvider(WhatsAppProvider):
    """Provedor em memória para testes unitários e de integração."""

    def __init__(self) -> None:
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        normalized_phone = normalize_whatsapp_number(phone)
        record = {
            "phone": normalized_phone,
            "message": message,
            "provider": "MockWhatsAppProvider",
            "status": "success",
            "message_id": "MSG-MOCK",
        }
        self.sent_messages.append(record)
        logger.info(f"[MockWhatsApp] Mensagem simulada enviada para {normalized_phone}: {message[:60]}...")
        return record

    async def get_connection_status(self) -> Dict[str, Any]:
        return {"status": StatusConexaoWhatsApp.CONECTADO.value}

    async def get_qr_code(self) -> Dict[str, Any]:
        return {"status": StatusConexaoWhatsApp.CONECTADO.value, "qrcode": None}

    async def logout(self) -> Dict[str, Any]:
        return {"status": StatusConexaoWhatsApp.DESCONECTADO.value}

    async def restart(self) -> Dict[str, Any]:
        return {"status": StatusConexaoWhatsApp.CONECTADO.value}


class BaileysWhatsAppProvider(WhatsAppProvider):
    """
    Provedor oficial do WhatsApp integrado via HTTP ao microsserviço whatsapp-engine (Baileys).
    Nunca propaga exceções de rede ou erro HTTP para fora dos métodos.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = (base_url or settings.WHATSAPP_ENGINE_URL).rstrip("/")
        self.api_key = api_key or settings.WHATSAPP_API_KEY
        self._client = client

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[httpx.AsyncClient]:
        if self._client is not None:
            yield self._client
        else:
            async with httpx.AsyncClient(timeout=15.0) as client:
                yield client

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        normalized_phone = normalize_whatsapp_number(phone)
        url = f"{self.base_url}/send"
        payload = {"numero": normalized_phone, "mensagem": message}

        try:
            async with self._get_client() as client:
                response = await client.post(url, headers=self._headers(), json=payload)

            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "success",
                    "provider": "BaileysWhatsAppProvider",
                    "phone": normalized_phone,
                    "message_id": data.get("id"),
                    "jid": data.get("jid"),
                }

            error_msg = response.text
            code = None
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    error_msg = err_data.get("error", response.text)
                    code = err_data.get("code")
            except Exception:
                pass

            return {
                "status": "error",
                "provider": "BaileysWhatsAppProvider",
                "phone": normalized_phone,
                "error": error_msg,
                "http_status": response.status_code,
                "code": code,
            }

        except Exception as exc:
            logger.error(f"[BaileysProvider] Erro de rede ao enviar mensagem para {normalized_phone}: {exc}")
            return {
                "status": "error",
                "provider": "BaileysWhatsAppProvider",
                "phone": normalized_phone,
                "error": str(exc),
                "http_status": None,
            }

    async def get_connection_status(self) -> Dict[str, Any]:
        url = f"{self.base_url}/status"
        try:
            async with self._get_client() as client:
                response = await client.get(url, headers=self._headers())

            if response.status_code == 200:
                data = response.json()
                state = data.get("state")
                status = mapear_estado_engine(state)
                return {"status": status.value, "state": state}

            error_msg = response.text
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    error_msg = err_data.get("error", response.text)
            except Exception:
                pass

            return {"status": StatusConexaoWhatsApp.DESCONECTADO.value, "error": error_msg}

        except Exception as exc:
            logger.warning(f"[BaileysProvider] Falha ao verificar status: {exc}")
            return {"status": StatusConexaoWhatsApp.DESCONECTADO.value, "error": str(exc)}

    async def get_qr_code(self) -> Dict[str, Any]:
        url = f"{self.base_url}/qr"
        try:
            async with self._get_client() as client:
                response = await client.get(url, headers=self._headers())

            if response.status_code == 200:
                data = response.json()
                state = data.get("state")
                status = mapear_estado_engine(state)
                return {"status": status.value, "qrcode": data.get("qrcode")}

            error_msg = response.text
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    error_msg = err_data.get("error", response.text)
            except Exception:
                pass

            return {
                "status": StatusConexaoWhatsApp.DESCONECTADO.value,
                "qrcode": None,
                "error": error_msg,
            }

        except Exception as exc:
            logger.error(f"[BaileysProvider] Erro ao obter QR Code: {exc}")
            return {
                "status": StatusConexaoWhatsApp.DESCONECTADO.value,
                "qrcode": None,
                "error": str(exc),
            }

    async def logout(self) -> Dict[str, Any]:
        url = f"{self.base_url}/logout"
        try:
            async with self._get_client() as client:
                response = await client.post(url, headers=self._headers())

            if response.status_code == 200:
                data = response.json()
                status = mapear_estado_engine(data.get("state"))
                return {"status": status.value}

            error_msg = response.text
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    error_msg = err_data.get("error", response.text)
            except Exception:
                pass

            return {"status": StatusConexaoWhatsApp.DESCONECTADO.value, "error": error_msg}

        except Exception as exc:
            logger.error(f"[BaileysProvider] Erro ao realizar logout: {exc}")
            return {"status": StatusConexaoWhatsApp.DESCONECTADO.value, "error": str(exc)}

    async def restart(self) -> Dict[str, Any]:
        url = f"{self.base_url}/restart"
        try:
            async with self._get_client() as client:
                response = await client.post(url, headers=self._headers())

            if response.status_code == 200:
                data = response.json()
                status = mapear_estado_engine(data.get("state"))
                return {"status": status.value}

            error_msg = response.text
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    error_msg = err_data.get("error", response.text)
            except Exception:
                pass

            return {"status": StatusConexaoWhatsApp.DESCONECTADO.value, "error": error_msg}

        except Exception as exc:
            logger.error(f"[BaileysProvider] Erro ao reiniciar conexão: {exc}")
            return {"status": StatusConexaoWhatsApp.DESCONECTADO.value, "error": str(exc)}


PROVEDORES_ACEITOS = ("MOCK", "TEST", "BAILEYS")


def get_whatsapp_provider(provider_type: Optional[str] = None) -> WhatsAppProvider:
    """
    Instancia o provedor de WhatsApp configurado (WHATSAPP_PROVIDER).
    Valores aceitos: MOCK, TEST, BAILEYS.
    """
    raw = provider_type if provider_type is not None else settings.WHATSAPP_PROVIDER
    if not raw or not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            f"Provedor de WhatsApp desconhecido: '{raw}'. "
            f"Valores aceitos em WHATSAPP_PROVIDER: {', '.join(PROVEDORES_ACEITOS)}."
        )

    tipo = raw.strip().upper()
    if tipo in ("MOCK", "TEST"):
        return MockWhatsAppProvider()
    if tipo == "BAILEYS":
        return BaileysWhatsAppProvider(
            base_url=settings.WHATSAPP_ENGINE_URL,
            api_key=settings.WHATSAPP_API_KEY,
        )

    raise ValueError(
        f"Provedor de WhatsApp desconhecido: '{raw}'. "
        f"Valores aceitos em WHATSAPP_PROVIDER: {', '.join(PROVEDORES_ACEITOS)}."
    )


def check_whatsapp_provider_on_startup() -> None:
    """
    Validação executada no startup da API:
    - um WHATSAPP_PROVIDER desconhecido interrompe a subida (ValueError);
    - o provedor MOCK em produção gera um aviso.
    """
    provider = get_whatsapp_provider()
    if isinstance(provider, MockWhatsAppProvider) and settings.ENVIRONMENT == "production":
        logger.warning(
            "[WhatsApp] WHATSAPP_PROVIDER=MOCK com ENVIRONMENT=production: nenhuma mensagem será enviada "
            "(a régua de cobrança e os recibos apenas serão registrados em memória). "
            "Configure um provedor real quando a integração com o motor Baileys estiver disponível."
        )
