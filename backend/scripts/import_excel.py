"""
Script CLI para Importação em Lote de Sócios a partir de Planilhas Excel/CSV.
Permite aos administradores carregar a base de sócios diretamente pelo terminal ou container Docker.

Exemplo de uso:
    python scripts/import_excel.py --file /caminho/para/planilha_socios.xlsx
    docker compose exec backend python scripts/import_excel.py --file /app/dados.xlsx
"""
import argparse
import asyncio
import os
import sys

# Garante que o diretório raiz do backend esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import AsyncSessionLocal
from app.services.associado_service import AssociadoService


async def run_import(file_path: str) -> None:
    if not os.path.exists(file_path):
        print(f"❌ Erro: Arquivo '{file_path}' não foi encontrado.")
        sys.exit(1)

    filename = os.path.basename(file_path)
    print(f"📂 Lendo arquivo '{filename}'...")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    async with AsyncSessionLocal() as session:
        service = AssociadoService(session)
        print("⏳ Processando e validando dados dos sócios...")
        result = await service.import_associados_planilha(file_bytes, filename)

    print("\n" + "=" * 55)
    print("📊 RESULTADO DA IMPORTAÇÃO - CLUB MARAVILHA")
    print("=" * 55)
    print(f"Total de registros lidos:     {result.total_lidos}")
    print(f"✅ Novos sócios importados:    {result.total_importados}")
    print(f"⚠️  Ignorados (Já cadastrados): {result.total_ignorados_duplicados}")
    print(f"❌ Linhas com erro:            {len(result.erros)}")
    print("=" * 55)

    if result.erros:
        print("\n🔍 DETALHE DOS ERROS ENCONTRADOS:")
        for err in result.erros:
            print(f"  • Linha {err.linha} [{err.campo}]: {err.motivo}")
    print("\n✨ Operação concluída com sucesso.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importador de Associados do Club Maravilha a partir de .xlsx ou .csv"
    )
    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Caminho para o arquivo .xlsx ou .csv a ser importado"
    )
    args = parser.parse_args()
    asyncio.run(run_import(args.file))


if __name__ == "__main__":
    main()
