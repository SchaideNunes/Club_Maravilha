"""
Serviço de Gateway Pix Dinâmico e Geração de Payload EMVCo (Pix Copia e Cola)
em conformidade estrita com a especificação do Banco Central do Brasil.
"""
from dataclasses import dataclass
from decimal import Decimal
import secrets
import urllib.parse
from typing import Optional


def calculate_crc16(payload: str) -> str:
    """
    Calcula o checksum CRC-16-CCITT (polinômio 0x1021, inicial 0xFFFF)
    utilizado no padrão EMVCo do Banco Central do Brasil.
    """
    crc = 0xFFFF
    for char in payload.encode("utf-8"):
        crc ^= char << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _format_tlv(tag: str, value: str) -> str:
    """Formata um campo no padrão TLV (Tag-Length-Value)."""
    length = f"{len(value.encode('utf-8')):02d}"
    return f"{tag}{length}{value}"


def generate_pix_emv_copia_e_cola(
    chave_pix: str,
    beneficiario: str,
    cidade: str,
    valor: Decimal,
    txid: str
) -> str:
    """
    Gera a string Pix Copia e Cola completa seguindo a especificação do BCB.
    """
    # 00: Payload Format Indicator
    payload = _format_tlv("00", "01")
    # 01: Point of Initiation Method (12 = Dinâmico ou QR Code único)
    payload += _format_tlv("01", "12")

    # 26: Merchant Account Information (Pix)
    gui = _format_tlv("00", "br.gov.bcb.pix")
    key = _format_tlv("01", chave_pix)
    merchant_account = f"{gui}{key}"
    payload += _format_tlv("26", merchant_account)

    # 52: Merchant Category Code (0000 = Padrão)
    payload += _format_tlv("52", "0000")
    # 53: Transaction Currency (986 = BRL)
    payload += _format_tlv("53", "986")
    # 54: Transaction Amount
    payload += _format_tlv("54", f"{valor:.2f}")
    # 58: Country Code (BR)
    payload += _format_tlv("58", "BR")
    # 59: Merchant Name
    clean_name = beneficiario[:25]
    payload += _format_tlv("59", clean_name)
    # 60: Merchant City
    clean_city = cidade[:15]
    payload += _format_tlv("60", clean_city)

    # 62: Additional Data Field Template (txid)
    txid_field = _format_tlv("05", txid[:25])
    payload += _format_tlv("62", txid_field)

    # 63: CRC16
    payload_to_crc = f"{payload}6304"
    crc = calculate_crc16(payload_to_crc)

    return f"{payload_to_crc}{crc}"


@dataclass
class PixChargeResult:
    txid: str
    pix_copia_cola: str
    pix_qr_code_url: str


class MockPixGateway:
    """
    Adapter do Gateway Pix para desenvolvimento local e ambiente de testes.
    Simula perfeitamente a geração de txid exclusivo, EMVCo e URL de QR Code.
    """
    def __init__(
        self,
        chave_pix: str = "financeiro@clubmaravilha.com.br",
        beneficiario: str = "Club Maravilha",
        cidade: str = "Sao Paulo",
        secret_key: Optional[str] = "mock_webhook_secret_dev"
    ) -> None:
        self.chave_pix = chave_pix
        self.beneficiario = beneficiario
        self.cidade = cidade
        self.secret_key = secret_key

    def create_dynamic_pix_charge(
        self,
        fatura_id: str,
        valor: Decimal,
        referencia_mes: str,
        nome_associado: str,
        cpf_associado: str
    ) -> PixChargeResult:
        # Gera txid único e rastreável: CM-AAAA-MM-RANDOMHEX
        random_hex = secrets.token_hex(4).upper()
        clean_mes = referencia_mes.replace("-", "")
        txid = f"CM-{clean_mes}-{random_hex}"

        pix_copia_cola = generate_pix_emv_copia_e_cola(
            chave_pix=self.chave_pix,
            beneficiario=self.beneficiario,
            cidade=self.cidade,
            valor=valor,
            txid=txid
        )

        # URL de renderização do QR Code oficial a partir da string EMV
        encoded_payload = urllib.parse.quote(pix_copia_cola)
        pix_qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_payload}"

        return PixChargeResult(
            txid=txid,
            pix_copia_cola=pix_copia_cola,
            pix_qr_code_url=pix_qr_code_url
        )

    def verify_webhook_token(self, token_received: Optional[str]) -> bool:
        if not self.secret_key or not token_received:
            return False
        return secrets.compare_digest(self.secret_key, token_received)
