"""
Feature 2 (MVP) - Importação da planilha da secretaria: cabeçalhos variados, dia de vencimento
e CPF numérico vindo do Excel.

Contratos definidos aqui (a implementar em app.services.excel_import_service.parse_excel_or_csv_bytes,
mantendo a assinatura (bytes, filename) -> (List[AssociadoCreate], List[ImportErrorDetail])):
- Cabeçalhos são normalizados sem acento/pontuação/caixa. Aliases aceitos:
    nome     : "Nome", "NOME COMPLETO", "Nome do Sócio", "Associado"
    cpf      : "CPF", "C.P.F."
    whatsapp : "WhatsApp", "Telefone", "Celular", "Telefone/WhatsApp", "Celular (WhatsApp)"
    email    : "Email", "E-mail", "E-MAIL"
    dia_vencimento (OPCIONAL): "Dia Vencimento", "Vencimento", "Dia de Vencimento", "dia_vencimento",
               "Dia do Vencimento"
- dia_vencimento: inteiro 1..31 ("10", 10, "10.0"); célula vazia ou coluna ausente -> settings.DIA_VENCIMENTO_PADRAO;
  valor inválido -> ImportErrorDetail(campo="dia_vencimento") e a linha não é importada.
- CPF numérico com 9 ou 10 dígitos (Excel removeu zeros à esquerda) é completado com zeros à esquerda.
"""
import io

import openpyxl
import pytest

from app.core.config import settings
from app.services.excel_import_service import parse_excel_or_csv_bytes

CPF_A = "529.982.247-25"
CPF_B = "111.444.777-35"


def _cpf_valido(base9: str) -> str:
    def digito(digitos: str, peso_inicial: int) -> str:
        soma = sum(int(d) * p for d, p in zip(digitos, range(peso_inicial, 1, -1)))
        resto = (soma * 10) % 11
        return str(0 if resto == 10 else resto)

    d1 = digito(base9, 10)
    return base9 + d1 + digito(base9 + d1, 11)


def _xlsx(linhas: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for linha in linhas:
        ws.append(linha)
    stream = io.BytesIO()
    wb.save(stream)
    return stream.getvalue()


def _csv(linhas: list) -> bytes:
    return ("\n".join(";".join(str(c) for c in linha) for linha in linhas) + "\n").encode("utf-8")


@pytest.mark.parametrize(
    "cab_nome,cab_cpf,cab_tel,cab_email",
    [
        ("Nome", "CPF", "WhatsApp", "Email"),
        ("NOME COMPLETO", "C.P.F.", "Telefone", "E-mail"),
        ("Nome do Sócio", "cpf", "Celular", "E-MAIL"),
        ("Associado", "CPF", "Telefone/WhatsApp", "email"),
        ("Nome", "CPF", "Celular (WhatsApp)", "E-mail"),
    ],
)
def test_aceita_cabecalhos_variados_da_secretaria(cab_nome, cab_cpf, cab_tel, cab_email):
    conteudo = _xlsx([
        [cab_nome, cab_cpf, cab_tel, cab_email],
        ["Carlos Silva", "52998224725", "(75) 99999-1111", "carlos@club.com"],
    ])

    rows, errors = parse_excel_or_csv_bytes(conteudo, "secretaria.xlsx")

    assert errors == []
    assert len(rows) == 1
    assert rows[0].nome == "Carlos Silva"
    assert rows[0].cpf == CPF_A
    assert rows[0].whatsapp == "5575999991111"
    assert rows[0].email == "carlos@club.com"


@pytest.mark.parametrize(
    "cab_dia",
    ["Dia Vencimento", "Vencimento", "Dia de Vencimento", "dia_vencimento", "Dia do Vencimento"],
)
def test_le_dia_vencimento_com_cabecalhos_variados(cab_dia):
    conteudo = _csv([
        ["Nome", "CPF", "Telefone", "E-mail", cab_dia],
        ["Carlos Silva", CPF_A, "75999991111", "carlos@club.com", "15"],
    ])

    rows, errors = parse_excel_or_csv_bytes(conteudo, "secretaria.csv")

    assert errors == []
    assert rows[0].dia_vencimento == 15


def test_dia_vencimento_numerico_do_excel():
    conteudo = _xlsx([
        ["Nome", "CPF", "Celular", "Email", "Vencimento"],
        ["Carlos Silva", CPF_A, "75999991111", "carlos@club.com", 5],
        ["Mariana Lima", CPF_B, "75999992222", "mariana@club.com", 20.0],
    ])

    rows, errors = parse_excel_or_csv_bytes(conteudo, "secretaria.xlsx")

    assert errors == []
    assert [r.dia_vencimento for r in rows] == [5, 20]


def test_dia_vencimento_vazio_ou_coluna_ausente_usa_padrao():
    com_coluna = _csv([
        ["Nome", "CPF", "Telefone", "Email", "Vencimento"],
        ["Carlos Silva", CPF_A, "75999991111", "carlos@club.com", ""],
    ])
    sem_coluna = _csv([
        ["Nome", "CPF", "Telefone", "Email"],
        ["Carlos Silva", CPF_A, "75999991111", "carlos@club.com"],
    ])

    for conteudo in (com_coluna, sem_coluna):
        rows, errors = parse_excel_or_csv_bytes(conteudo, "secretaria.csv")
        assert errors == []
        assert rows[0].dia_vencimento == settings.DIA_VENCIMENTO_PADRAO


@pytest.mark.parametrize("valor", ["0", "32", "abc", "-5"])
def test_dia_vencimento_invalido_vira_erro_da_linha(valor):
    conteudo = _csv([
        ["Nome", "CPF", "Telefone", "Email", "Dia Vencimento"],
        ["Carlos Silva", CPF_A, "75999991111", "carlos@club.com", valor],
        ["Mariana Lima", CPF_B, "75999992222", "mariana@club.com", "10"],
    ])

    rows, errors = parse_excel_or_csv_bytes(conteudo, "secretaria.csv")

    assert [r.nome for r in rows] == ["Mariana Lima"]
    assert [(e.linha, e.campo) for e in errors] == [(2, "dia_vencimento")]
    assert errors[0].motivo


def test_cpf_numerico_sem_zeros_a_esquerda_e_completado():
    cpf = _cpf_valido("012345678")  # começa com 0 -> Excel grava como número de 10 dígitos
    assert cpf.startswith("0")
    conteudo = _xlsx([
        ["Nome", "CPF", "Telefone", "Email"],
        ["Zeca Zero", int(cpf), "75999993333", "zeca@club.com"],
    ])

    rows, errors = parse_excel_or_csv_bytes(conteudo, "secretaria.xlsx")

    assert errors == []
    assert rows[0].cpf == f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def test_email_duplicado_dentro_da_planilha_vira_erro():
    conteudo = _csv([
        ["Nome", "CPF", "Telefone", "Email"],
        ["Carlos Silva", CPF_A, "75999991111", "mesmo@club.com"],
        ["Mariana Lima", CPF_B, "75999992222", "MESMO@club.com"],
    ])

    rows, errors = parse_excel_or_csv_bytes(conteudo, "secretaria.csv")

    assert [r.nome for r in rows] == ["Carlos Silva"]
    assert [(e.linha, e.campo) for e in errors] == [(3, "email")]
