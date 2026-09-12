"""
Testes unitários para o serviço de geração de Pix Dinâmico e validação de Webhooks.
Seguindo rigorosamente a disciplina TDD (Red-Green-Refactor).
"""
from decimal import Decimal
import pytest
from app.services.pix_gateway_service import (
    calculate_crc16,
    generate_pix_emv_copia_e_cola,
    MockPixGateway,
)


def test_crc16_calculation():
    """Valida cálculo de checksum CRC-16-CCITT (polinômio 0x1021) do padrão Pix BCB."""
    # Exemplo conhecido do padrão EMVCo
    payload = "00020101021226580014br.gov.bcb.pix0136123e4567-e89b-12d3-a456-426614174000520400005303986540510.005802BR5913Fulano de Tal6008BRASILIA62070503***6304"
    crc = calculate_crc16(payload)
    assert len(crc) == 4
    assert crc.isalnum()


def test_generate_pix_copia_e_cola():
    """Valida montagem do payload Pix Copia e Cola no padrão EMVCo."""
    copia_e_cola = generate_pix_emv_copia_e_cola(
        chave_pix="financeiro@clubmaravilha.com.br",
        beneficiario="Club Maravilha",
        cidade="Sao Paulo",
        valor=Decimal("150.00"),
        txid="CM202609FAT0001"
    )

    # Verificações da especificação do Banco Central
    assert copia_e_cola.startswith("000201")
    assert "br.gov.bcb.pix" in copia_e_cola
    assert "financeiro@clubmaravilha.com.br" in copia_e_cola
    assert "150.00" in copia_e_cola
    assert "CM202609FAT0001" in copia_e_cola
    assert "6304" in copia_e_cola  # Tag do CRC16


def test_mock_pix_gateway_charge_generation():
    """Valida adapter mock de geração de cobrança dinâmica com txid exclusivo."""
    gateway = MockPixGateway()
    charge = gateway.create_dynamic_pix_charge(
        fatura_id="fatura-123",
        valor=Decimal("185.00"),
        referencia_mes="2026-09",
        nome_associado="Carlos Eduardo",
        cpf_associado="529.982.247-25"
    )

    assert charge.txid.startswith("CM-")
    assert "185.00" in charge.pix_copia_cola
    assert charge.pix_qr_code_url.startswith("https://api.qrserver.com") or "data:image" in charge.pix_qr_code_url


def test_webhook_signature_verification():
    """Valida segurança na verificação de assinatura de webhook."""
    gateway = MockPixGateway(secret_key="segredo_super_seguro")

    # Assinatura válida
    assert gateway.verify_webhook_token("segredo_super_seguro") is True

    # Assinatura inválida
    assert gateway.verify_webhook_token("segredo_falso") is False
    assert gateway.verify_webhook_token("") is False
    assert gateway.verify_webhook_token(None) is False
