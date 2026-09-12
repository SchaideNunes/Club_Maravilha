"""
Serviço de Mensageria WhatsApp desacoplado com suporte a Evolution API e Mock para testes.
"""
import re
import logging
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
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


class MockWhatsAppProvider(WhatsAppProvider):
    """Provedor em memória para testes unitários e integração."""

    def __init__(self) -> None:
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        normalized_phone = normalize_whatsapp_number(phone)
        record = {
            "phone": normalized_phone,
            "message": message,
            "provider": "MockWhatsAppProvider",
            "status": "success"
        }
        self.sent_messages.append(record)
        logger.info(f"[MockWhatsApp] Mensagem simulada enviada para {normalized_phone}: {message[:60]}...")
        return record


class EvolutionApiWhatsAppProvider(WhatsAppProvider):
    """Integração oficial com a API Evolution API."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        instance_name: Optional[str] = None
    ) -> None:
        self.api_url = (api_url or settings.WHATSAPP_API_URL).rstrip("/")
        self.api_key = api_key or settings.WHATSAPP_API_KEY
        self.instance_name = instance_name or settings.WHATSAPP_INSTANCE_NAME

    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        normalized_phone = normalize_whatsapp_number(phone)
        url = f"{self.api_url}/message/sendText/{self.instance_name}"
        headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "number": normalized_phone,
            "text": message
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                message_id = data.get("key", {}).get("id", "UNKNOWN_ID")
                return {
                    "status": "success",
                    "provider": "EvolutionApiWhatsAppProvider",
                    "phone": normalized_phone,
                    "message_id": message_id,
                    "raw_response": data
                }
            except httpx.HTTPError as err:
                logger.error(f"[EvolutionAPI] Erro ao enviar mensagem para {normalized_phone}: {err}")
                return {
                    "status": "error",
                    "provider": "EvolutionApiWhatsAppProvider",
                    "phone": normalized_phone,
                    "error": str(err)
                }


def get_whatsapp_provider(provider_type: Optional[str] = None) -> WhatsAppProvider:
    tipo = (provider_type or settings.WHATSAPP_PROVIDER).upper()
    if tipo == "MOCK" or tipo == "TEST":
        return MockWhatsAppProvider()
    return EvolutionApiWhatsAppProvider()
