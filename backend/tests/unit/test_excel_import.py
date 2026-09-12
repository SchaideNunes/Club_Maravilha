"""
Testes unitários para o motor de importação de planilhas Excel e validações cadastrais.
Seguindo rigorosamente a disciplina TDD (Red-Green-Refactor).
"""
import io
import pytest
import openpyxl
from app.services.excel_import_service import (
    validate_and_format_cpf,
    normalize_phone_number,
    parse_excel_or_csv_bytes,
)


def test_cpf_validation_valid():
    """Valida CPFs válidos conhecidos com e sem pontuação."""
    # CPFs matematicamente válidos
    valid_cpf_1 = "52998224725"
    valid_cpf_2 = "11144477735"

    formatted_1 = validate_and_format_cpf(valid_cpf_1)
    assert formatted_1 == "529.982.247-25"

    formatted_2 = validate_and_format_cpf("111.444.777-35")
    assert formatted_2 == "111.444.777-35"


def test_cpf_validation_invalid_digits():
    """Rejeita CPFs com dígitos verificadores incorretos."""
    with pytest.raises(ValueError, match="Dígitos verificadores do CPF inválidos"):
        validate_and_format_cpf("52998224700")


def test_cpf_validation_repeated_digits():
    """Rejeita sequências de dígitos repetidos conhecidas (ex: 111.111.111-11)."""
    with pytest.raises(ValueError, match="CPF inválido"):
        validate_and_format_cpf("11111111111")
    with pytest.raises(ValueError, match="CPF inválido"):
        validate_and_format_cpf("00000000000")


def test_cpf_validation_invalid_length():
    """Rejeita CPFs com comprimento inadequado."""
    with pytest.raises(ValueError, match="deve conter exatamente 11 dígitos"):
        validate_and_format_cpf("123456")


def test_phone_normalization():
    """Normaliza números de WhatsApp para formato consistente."""
    assert normalize_phone_number("(11) 98765-4321") == "+5511987654321"
    assert normalize_phone_number("11987654321") == "+5511987654321"
    assert normalize_phone_number("+5511987654321") == "+5511987654321"
    assert normalize_phone_number("11 98888 7777") == "+5511988887777"


def test_parse_excel_bytes_valid_and_invalid_rows():
    """Valida extração em memória de arquivo .xlsx com linhas válidas, duplicadas e com erro."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Socios"

    # Cabeçalho
    ws.append(["Nome", "CPF", "WhatsApp", "Email", "Status", "Observacoes"])
    
    # Linha 2: Sócio Válido 1
    ws.append(["Carlos Silva", "52998224725", "(11) 99999-1111", "carlos@club.com", "ATIVO", "Sócio Fundador"])
    
    # Linha 3: CPF Inválido
    ws.append(["Ana Santos", "12345678900", "(11) 99999-2222", "ana@club.com", "ATIVO", ""])
    
    # Linha 4: Duplicado interno do CPF da Linha 2
    ws.append(["Carlos Silva Repetido", "529.982.247-25", "(11) 99999-3333", "carlos.duplicado@club.com", "ATIVO", ""])
    
    # Linha 5: Linha em branco
    ws.append(["", "", "", "", "", ""])

    # Linha 6: Sócio Válido 2
    ws.append(["Mariana Lima", "11144477735", "+5511999994444", "mariana@club.com", "ATIVO", ""])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    file_bytes = stream.getvalue()

    rows, errors = parse_excel_or_csv_bytes(file_bytes, "socios.xlsx")

    # Espera 2 sócios válidos (Carlos e Mariana)
    assert len(rows) == 2
    assert rows[0].nome == "Carlos Silva"
    assert rows[0].cpf == "529.982.247-25"
    assert rows[0].whatsapp == "+5511999991111"
    assert rows[1].nome == "Mariana Lima"

    # Espera 2 erros reportados com linha identificada (linha 3 CPF inválido e linha 4 CPF duplicado)
    assert len(errors) == 2
    assert any(err.linha == 3 for err in errors)
    assert any("duplicado" in err.motivo.lower() for err in errors)


def test_parse_csv_bytes_semicolon_and_comma():
    """Valida extração de arquivo .csv delimitado por ponto e vírgula ou vírgula."""
    csv_content = (
        "Nome;CPF;WhatsApp;Email;Status\n"
        "Renato Gaúcho;52998224725;11988881234;renato@club.com;ATIVO\n"
    ).encode("utf-8")

    rows, errors = parse_excel_or_csv_bytes(csv_content, "socios.csv")
    assert len(rows) == 1
    assert rows[0].nome == "Renato Gaúcho"
    assert rows[0].cpf == "529.982.247-25"
    assert len(errors) == 0


def test_parse_unsupported_format():
    """Garante erro ao enviar arquivos com extensões não suportadas."""
    with pytest.raises(ValueError, match="Formato de arquivo não suportado"):
        parse_excel_or_csv_bytes(b"content", "socios.pdf")


def test_parse_missing_mandatory_column():
    """Garante erro explicativo quando uma coluna obrigatória não está no cabeçalho."""
    csv_missing = "Nome;Telefone;Email\nJoão;11999991111;joao@club.com\n".encode("utf-8")
    with pytest.raises(ValueError, match="Coluna obrigatória 'CPF' não encontrada"):
        parse_excel_or_csv_bytes(csv_missing, "socios.csv")

