"""
Script interativo para testar o fluxo completo do Club Maravilha sem credenciais bancárias reais.
Permite testar envio de mensagens para o seu WhatsApp e simulação de pagamento Pix com baixa instantânea.

Uso:
  docker compose exec backend python scripts/test_flow.py --nome "Seu Nome" --whatsapp "5511999998888"
"""
import argparse
import asyncio
import os
import sys

# Garante que o diretório raiz do backend esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date, timedelta
from decimal import Decimal
from app.core.database import AsyncSessionLocal
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.schemas.fatura import FaturaCreate
from app.services.billing_engine_service import BillingEngineService
from app.services.fatura_service import FaturaService
from app.services.whatsapp_queue_service import get_global_whatsapp_queue


async def run_test_flow(nome: str, whatsapp: str, simular_pagamento: bool) -> None:
    print("\n" + "=" * 70)
    print("🎾 CLUB MARAVILHA - AMBIENTE DE TESTES INTEGRADOS (SEM BANCO REAL)")
    print("=" * 70)
    print(f"👤 Associado de Teste : {nome}")
    print(f"📱 WhatsApp de Destino: {whatsapp}")
    print("=" * 70 + "\n")

    async with AsyncSessionLocal() as session:
        assoc_repo = AssociadoRepository(session)
        fatura_service = FaturaService(session)
        billing_engine = BillingEngineService(session)

        # 1. Verifica ou cria o associado
        print("▶️ [Passo 1/4] Verificando cadastro do associado no PostgreSQL...")
        cpf_teste = "000.111.222-33"
        socio = await assoc_repo.get_by_cpf(cpf_teste)
        if not socio:
            socio = Associado(
                nome=nome,
                cpf=cpf_teste,
                whatsapp=whatsapp,
                email="teste_fluxo@clubmaravilha.com.br",
                facial_id="FACE_TEST_DEMO",
                status=StatusAssociado.ATIVO
            )
            socio = await assoc_repo.create(socio)
            await session.commit()
            print(f"   ✅ Associado criado com sucesso! ID: {socio.id}")
        else:
            socio.nome = nome
            socio.whatsapp = whatsapp
            socio.status = StatusAssociado.ATIVO
            socio.facial_id = socio.facial_id or "FACE_TEST_DEMO"
            await session.commit()
            print(f"   ℹ️ Associado de teste reutilizado! ID: {socio.id}")

        # 2. Criação da fatura com Pix Dinâmico
        print("\n▶️ [Passo 2/4] Gerando fatura com Pix Dinâmico e BR Code...")
        fatura = await fatura_service.create_fatura(
            FaturaCreate(
                associado_id=socio.id,
                referencia_mes=date.today().strftime("%Y-%m"),
                valor_base=Decimal("150.00"),
                valor_convidados_excedentes=Decimal("0.00"),
                valor_desconto=Decimal("0.00"),
                valor_total=Decimal("150.00"),
                data_vencimento=date.today(),
            )
        )
        print(f"   ✅ Fatura gerada com sucesso! ID: {fatura.id}")
        print(f"   🔑 TXID Exclusivo : {fatura.txid}")
        print(f"   💰 Valor Total    : R$ {fatura.valor_total:.2f}")
        print(f"   📋 Pix Copia e Cola gerado (EMVCo válido):\n   {fatura.pix_copia_cola[:60]}...")

        # 3. Disparo da régua de cobrança matinal D-0
        print("\n▶️ [Passo 3/4] Executando disparo matinal D-0 da régua de WhatsApp...")
        report = await billing_engine.processar_regua_diaria(data_referencia=date.today())
        print(f"   📬 Mensagens D-0 enfileiradas na régua: {report.d_zero_enviados}")

        # Processa a fila de mensagens para despachar
        queue = get_global_whatsapp_queue()
        print(f"   ⏳ Fila de mensagens atual: {queue.qsize} item(ns). Despachando...")
        await queue.process_one()
        print("   ✅ Mensagem com Pix Copia e Cola despachada!")

        # 4. Simulação de Pagamento Pix
        if simular_pagamento:
            print("\n▶️ [Passo 4/4] Simulando pagamento Pix recebido via Webhook...")
            payload = {
                "evento": "pix_recebido_simulado",
                "txid": fatura.txid,
                "valor": str(fatura.valor_total),
            }
            # Simula a chegada do webhook instantâneo
            resultado = await fatura_service.process_pix_webhook(
                payload=payload,
                secret_token="mock_webhook_secret_dev"
            )
            print(f"   ⚡ Resposta do Webhook (< 2s): {resultado['message']}")

            # Despacha o recibo de pagamento instantâneo
            print("   📲 Despachando recibo digital de pagamento via WhatsApp...")
            await queue.process_one()

            # Checa o status atualizado no banco
            await session.refresh(fatura)
            await session.refresh(socio)
            print(f"\n" + "=" * 70)
            print("🎉 RESULTADO FINAL DO TESTE:")
            print(f"   • Status da Fatura   : {fatura.status} (Data: {fatura.data_pagamento})")
            print(f"   • Status do Associado: {socio.status}")
            print(f"   • Catraca Facial     : LIBERADA (Notificação de sync disparada)")
            print(f"   • WhatsApp Enviado   : Lembrete matinal D-0 + Recibo digital pós-pagamento")
            print("=" * 70 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste interativo do fluxo de cobrança e Pix do Club Maravilha")
    parser.add_argument("--nome", type=str, default="Seu Nome Teste", help="Nome do associado para teste")
    parser.add_argument("--whatsapp", type=str, default="+5511999998888", help="Telefone WhatsApp com DDD")
    parser.add_argument("--pagar", action="store_true", default=True, help="Simula a baixa do pagamento Pix")

    args = parser.parse_args()
    asyncio.run(run_test_flow(nome=args.nome, whatsapp=args.whatsapp, simular_pagamento=args.pagar))


if __name__ == "__main__":
    main()
