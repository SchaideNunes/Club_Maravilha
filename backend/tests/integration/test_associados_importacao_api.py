"""
Feature 2 (MVP) - Importação em lote (.xlsx/.csv) da planilha da secretaria.

Contrato (a implementar):
- POST /api/v1/associados/importar  (multipart, campo "file")
    query: atualizar_existentes: bool = false
      * false (padrão): CPF já cadastrado => linha IGNORADA (conta em total_ignorados_duplicados).
      * true (upsert por CPF): CPF já cadastrado => atualiza nome, whatsapp, email e dia_vencimento
        (status, convidados e faturas preservados) e conta em total_atualizados.
    200: {
        "total_lidos": int,                  # linhas de dados não vazias
        "total_importados": int,
        "total_atualizados": int,            # sempre presente (0 no modo padrão)
        "total_ignorados_duplicados": int,
        "erros": [{"linha": int, "campo": str, "motivo": str}]   # linha = nº da linha na planilha (cabeçalho = 1)
    }
    * CPF novo cujo e-mail já pertence a OUTRO associado => erro (campo "email"), não importa nem ignora.
    400: extensão não suportada, arquivo vazio ou coluna obrigatória ausente.
"""
import io

import openpyxl
import pytest
from httpx import AsyncClient

from app.core.config import settings

URL = "/api/v1/associados/importar"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CPF_A = "529.982.247-25"
CPF_B = "111.444.777-35"
CPF_C = "123.456.789-09"


def _xlsx(linhas: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for linha in linhas:
        ws.append(linha)
    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()


async def _importar(client: AsyncClient, conteudo: bytes, nome: str = "secretaria.xlsx", **params):
    mime = XLSX_MIME if nome.endswith(".xlsx") else "text/csv"
    return await client.post(URL, params=params, files={"file": (nome, conteudo, mime)})


async def _buscar(client: AsyncClient, termo: str) -> dict:
    itens = (await client.get("/api/v1/associados/", params={"q": termo})).json()["items"]
    assert len(itens) == 1, itens
    return itens[0]


PLANILHA_SECRETARIA = [
    ["Nome Completo", "C.P.F.", "Celular", "E-mail", "Dia de Vencimento", "Observações"],
    ["Carlos Silva", "52998224725", "(75) 99999-1111", "carlos@club.com", 5, "Fundador"],
    ["Mariana Lima", CPF_B, "75 99999-2222", "mariana@club.com", 20, ""],
    ["", "", "", "", None, ""],
    ["Pedro Erro", "12345678900", "75999993333", "pedro@club.com", 10, ""],
]


async def test_importa_planilha_da_secretaria_com_relatorio(async_client: AsyncClient):
    res = await _importar(async_client, _xlsx(PLANILHA_SECRETARIA))

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total_lidos"] == 3
    assert body["total_importados"] == 2
    assert body["total_atualizados"] == 0
    assert body["total_ignorados_duplicados"] == 0
    assert [(e["linha"], e["campo"]) for e in body["erros"]] == [(5, "cpf")]

    carlos = await _buscar(async_client, "Carlos")
    assert carlos["cpf"] == CPF_A
    assert carlos["whatsapp"] == "5575999991111"
    assert carlos["dia_vencimento"] == 5
    mariana = await _buscar(async_client, "Mariana")
    assert mariana["dia_vencimento"] == 20


async def test_modo_padrao_ignora_cpf_ja_cadastrado_sem_alterar(async_client: AsyncClient):
    await _importar(async_client, _xlsx(PLANILHA_SECRETARIA))
    alterada = [
        PLANILHA_SECRETARIA[0],
        ["Carlos Silva Alterado", CPF_A, "(75) 98888-0000", "carlos.novo@club.com", 15, ""],
        ["Ana Nova", CPF_C, "75999994444", "ana@club.com", "", ""],
    ]

    body = (await _importar(async_client, _xlsx(alterada))).json()

    assert (body["total_lidos"], body["total_importados"], body["total_atualizados"],
            body["total_ignorados_duplicados"]) == (2, 1, 0, 1)
    assert body["erros"] == []
    carlos = await _buscar(async_client, "Carlos")
    assert carlos["nome"] == "Carlos Silva"
    assert carlos["dia_vencimento"] == 5
    ana = await _buscar(async_client, "Ana Nova")
    assert ana["dia_vencimento"] == settings.DIA_VENCIMENTO_PADRAO


async def test_modo_upsert_atualiza_por_cpf_preservando_status(async_client: AsyncClient):
    await _importar(async_client, _xlsx(PLANILHA_SECRETARIA))
    carlos = await _buscar(async_client, "Carlos")
    patch = await async_client.patch(f"/api/v1/associados/{carlos['id']}", json={"status": "BLOQUEADO"})
    assert patch.status_code == 200

    alterada = [
        ["Nome", "CPF", "Telefone", "Email", "Vencimento"],
        ["Carlos Silva Alterado", "529.982.247-25", "(75) 98888-0000", "carlos.novo@club.com", 15],
        ["Ana Nova", CPF_C, "75999994444", "ana@club.com", 7],
    ]
    res = await _importar(async_client, _xlsx(alterada), atualizar_existentes="true")

    assert res.status_code == 200, res.text
    body = res.json()
    assert (body["total_importados"], body["total_atualizados"], body["total_ignorados_duplicados"]) == (1, 1, 0)
    atualizado = (await async_client.get(f"/api/v1/associados/{carlos['id']}")).json()
    assert atualizado["nome"] == "Carlos Silva Alterado"
    assert atualizado["whatsapp"] == "5575988880000"
    assert atualizado["email"] == "carlos.novo@club.com"
    assert atualizado["dia_vencimento"] == 15
    assert atualizado["status"] == "BLOQUEADO"


async def test_email_de_outro_associado_vira_erro_da_linha(async_client: AsyncClient):
    criado = await async_client.post("/api/v1/associados/", json={
        "nome": "Dono do Email", "cpf": CPF_A, "whatsapp": "75999990000", "email": "ocupado@club.com",
    })
    assert criado.status_code == 201
    conteudo = _xlsx([
        ["Nome", "CPF", "WhatsApp", "Email"],
        ["Intruso", CPF_B, "75999991111", "Ocupado@club.com"],
        ["Legitimo", CPF_C, "75999992222", "legitimo@club.com"],
    ])

    body = (await _importar(async_client, conteudo)).json()

    assert body["total_importados"] == 1
    assert body["total_ignorados_duplicados"] == 0
    assert [(e["linha"], e["campo"]) for e in body["erros"]] == [(2, "email")]


async def test_csv_com_bom_e_ponto_e_virgula(async_client: AsyncClient):
    conteudo = "\ufeffNome;CPF;Telefone;E-mail;Dia Vencimento\nCarlos Silva;529.982.247-25;75999991111;carlos@club.com;12\n"

    res = await _importar(async_client, conteudo.encode("utf-8"), nome="secretaria.csv")

    assert res.status_code == 200, res.text
    assert res.json()["total_importados"] == 1
    assert (await _buscar(async_client, "Carlos"))["dia_vencimento"] == 12


@pytest.mark.parametrize(
    "nome,conteudo",
    [
        ("socios.pdf", b"%PDF-1.4"),
        ("socios.csv", b""),
        ("socios.csv", "Nome;Telefone;Email\nJoao;75999991111;joao@club.com\n".encode("utf-8")),
    ],
)
async def test_arquivo_invalido_retorna_400(async_client: AsyncClient, nome, conteudo):
    res = await _importar(async_client, conteudo, nome=nome)
    assert res.status_code == 400
    assert res.json()["detail"]
