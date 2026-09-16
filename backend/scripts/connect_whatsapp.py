"""
Club Maravilha - Assistente de Conexão WhatsApp (Evolution API)
Permite inicializar a instância, gerar o QR Code para leitura no celular e testar envios.

Uso:
  python scripts/connect_whatsapp.py
  python scripts/connect_whatsapp.py --status
  python scripts/connect_whatsapp.py --send-test 5511999998888
"""
import argparse
import asyncio
import base64
import os
import sys
import time

# Garante importações corretas de módulos app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.whatsapp_service import (
    EvolutionApiWhatsAppProvider,
    normalize_whatsapp_number,
)


async def check_or_create_connection(send_test_phone: str = None, check_only: bool = False):
    print("=" * 70)
    print(" 🚀 CLUB MARAVILHA - CONEXÃO DE WHATSAPP (EVOLUTION API)")
    print("=" * 70)
    print(f" Provedor Configurado : {settings.WHATSAPP_PROVIDER}")
    print(f" API URL              : {settings.WHATSAPP_API_URL}")
    print(f" Instância Alvo       : {settings.WHATSAPP_INSTANCE_NAME}")
    print("-" * 70)

    provider = EvolutionApiWhatsAppProvider()

    # 1. Verificar Status Atual
    print("\n🔍 Consultando estado da instância...")
    status = await provider.get_connection_status()
    instance_info = status.get("instance", {})
    state = instance_info.get("state", "unknown")

    print(f"   Estado Atual: [{state.upper()}]")

    if check_only:
        if state == "open":
            print("   ✅ Instância CONECTADA e pronta para envio!")
        else:
            print(f"   ⚠️ Instância NÃO conectada (estado: {state}).")
        return

    # 2. Se já conectado
    if state == "open":
        print("\n✅ O WhatsApp já está CONECTADO e operando normalmente!")
    else:
        # 3. Se não conectado, inicializa ou busca QR Code
        print("\n⚙️ Garantindo criação da instância...")
        await provider.create_instance_if_not_exists()

        print("📲 Solicitando QR Code para pareamento...")
        qr_data = await provider.get_qr_code()
        base64_img = qr_data.get("base64")

        if base64_img:
            # Salva o arquivo PNG local para visualização fácil
            try:
                if "," in base64_img:
                    raw_b64 = base64_img.split(",", 1)[1]
                else:
                    raw_b64 = base64_img
                
                qr_path = os.path.abspath("qr_code.png")
                with open(qr_path, "wb") as f:
                    f.write(base64.b64decode(raw_b64))
                print(f"   💾 Imagem do QR Code salva em: {qr_path}")
            except Exception as e:
                print(f"   ⚠️ Não foi possível salvar qr_code.png localmente: {e}")

            print("\n" + "=" * 70)
            print(" 📱 COMO CONECTAR SEU WHATSAPP AGORA:")
            print("=" * 70)
            print(" Opção 1: Abra seu navegador em:")
            print(f"    👉 http://localhost:{settings.PORT_BACKEND}/api/v1/whatsapp/qr")
            print("    (O QR Code aparece na tela e atualiza sozinho quando conectar!)")
            print("\n Opção 2: Abra a imagem salva 'qr_code.png' no seu computador.")
            print("\n No seu celular:")
            print(" 1. Abra o WhatsApp")
            print(" 2. Toque nos 3 pontinhos (ou Configurações) > 'Aparelhos Conectados'")
            print(" 3. Toque em 'Conectar um aparelho' e aponte a câmera para o QR Code")
            print("=" * 70)

            print("\n⏳ Aguardando leitura do QR Code (timeout de 60s)...")
            for i in range(30):
                await asyncio.sleep(2)
                st = await provider.get_connection_status()
                curr_state = st.get("instance", {}).get("state")
                if curr_state == "open":
                    print("\n🎉 PARABÉNS! WhatsApp CONECTADO COM SUCESSO!")
                    state = "open"
                    break
                sys.stdout.write(".")
                sys.stdout.flush()
            print()
        else:
            print("   ⚠️ QR Code ainda não disponível ou instância em transição.")

    # 4. Envio de Teste Opcional
    if send_test_phone:
        normalized = normalize_whatsapp_number(send_test_phone)
        print(f"\n📤 Enviando mensagem de teste para: {normalized}...")
        test_msg = (
            "🎉 Olá! Esta é uma mensagem de teste do sistema de gestão do Club Maravilha.\n"
            "Sua integração com o WhatsApp está funcionando perfeitamente!"
        )
        res = await provider.send_message(normalized, test_msg)
        if res.get("status") == "success":
            print(f"   ✅ Mensagem enviada com sucesso! Message ID: {res.get('message_id')}")
        else:
            print(f"   ❌ Erro ao enviar mensagem: {res.get('error')}")

    print("\n" + "=" * 70)
    print(" 🏁 Procedimento concluído.")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Conectar WhatsApp ao Club Maravilha")
    parser.add_argument("--status", action="store_true", help="Apenas verifica o status da conexão")
    parser.add_argument("--send-test", type=str, help="Envia mensagem de teste para o número especificado")
    args = parser.parse_args()

    asyncio.run(check_or_create_connection(
        send_test_phone=args.send_test,
        check_only=args.status
    ))


if __name__ == "__main__":
    main()
