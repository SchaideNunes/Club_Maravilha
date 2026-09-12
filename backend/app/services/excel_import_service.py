"""
Serviço de importação e validação de planilhas Excel (.xlsx) e arquivos (.csv).
Validação matemática estrita de CPF, normalização de telefones e extração em lote.
"""
import csv
import io
import re
from typing import List, Optional, Set, Tuple
import openpyxl
from app.schemas.associado import AssociadoCreate, ImportErrorDetail


def validate_and_format_cpf(cpf_raw: str) -> str:
    """
    Valida matematicamente os dígitos verificadores do CPF (módulo 11)
    e retorna o CPF formatado: 000.000.000-00.
    """
    if not cpf_raw:
        raise ValueError("CPF é obrigatório e não pode ser vazio.")

    # Remove todos os caracteres não numéricos
    digits = re.sub(r"\D", "", str(cpf_raw).strip())

    if len(digits) != 11:
        raise ValueError(f"CPF deve conter exatamente 11 dígitos numéricos (recebido: {len(digits)}).")

    # Rejeita sequências conhecidas de dígitos repetidos (ex: 111.111.111-11)
    if digits == digits[0] * 11:
        raise ValueError("CPF inválido: sequência de dígitos idênticos.")

    # Cálculo do 1º Dígito Verificador
    soma_1 = sum(int(digits[i]) * (10 - i) for i in range(9))
    resto_1 = (soma_1 * 10) % 11
    d1 = 0 if resto_1 == 10 else resto_1
    if d1 != int(digits[9]):
        raise ValueError("Dígitos verificadores do CPF inválidos.")

    # Cálculo do 2º Dígito Verificador
    soma_2 = sum(int(digits[i]) * (11 - i) for i in range(10))
    resto_2 = (soma_2 * 10) % 11
    d2 = 0 if resto_2 == 10 else resto_2
    if d2 != int(digits[10]):
        raise ValueError("Dígitos verificadores do CPF inválidos.")

    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def normalize_phone_number(phone_raw: str) -> str:
    """
    Normaliza números de WhatsApp / telefone para o formato padrão internacional E.164.
    Ex: (11) 98765-4321 -> +5511987654321
    """
    if not phone_raw:
        return ""

    raw_str = str(phone_raw).strip()
    has_plus = raw_str.startswith("+")
    digits = re.sub(r"\D", "", raw_str)

    if not digits:
        return ""

    if has_plus:
        return f"+{digits}"

    # Padrão brasileiro: 10 dígitos (fixo com DDD) ou 11 dígitos (celular com DDD)
    if len(digits) in (10, 11):
        return f"+55{digits}"

    return f"+{digits}"


def _normalize_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(header).lower())


def parse_excel_or_csv_bytes(
    file_bytes: bytes,
    filename: str
) -> Tuple[List[AssociadoCreate], List[ImportErrorDetail]]:
    """
    Lê o conteúdo em bytes de uma planilha .xlsx ou .csv e extrai associados válidos,
    coletando erros linha a linha sem interromper o processo global.
    """
    lower_filename = filename.lower()
    raw_rows: List[List[str]] = []

    if lower_filename.endswith(".xlsx") or lower_filename.endswith(".xlsm"):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        for row in sheet.iter_rows(values_only=True):
            raw_rows.append([str(c) if c is not None else "" for c in row])
    elif lower_filename.endswith(".csv"):
        # Tenta decodificar como UTF-8, com fallback para Latin-1
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        # Detecta delimitador (, ou ;)
        sample = text[:1024]
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        for row in reader:
            raw_rows.append(row)
    else:
        raise ValueError("Formato de arquivo não suportado. Envie um arquivo .xlsx ou .csv.")

    if not raw_rows:
        return [], []

    # Localização das colunas no cabeçalho
    header_row = raw_rows[0]
    col_map = {}
    for idx, col in enumerate(header_row):
        norm = _normalize_header(col)
        if norm in ("nome", "nomecompleto", "socio", "associado"):
            col_map["nome"] = idx
        elif norm in ("cpf", "documento", "numcpf"):
            col_map["cpf"] = idx
        elif norm in ("whatsapp", "celular", "telefone", "contato", "fone", "tel"):
            col_map["whatsapp"] = idx
        elif norm in ("email", "e-mail", "correioeletronico"):
            col_map["email"] = idx
        elif norm in ("observacoes", "observacao", "obs"):
            col_map["observacoes"] = idx
        elif norm in ("foto", "fotourl", "urlfoto"):
            col_map["foto_url"] = idx

    # Verifica colunas essenciais
    for req in ("nome", "cpf", "whatsapp", "email"):
        if req not in col_map:
            raise ValueError(
                f"Coluna obrigatória '{req.upper()}' não encontrada no cabeçalho da planilha. "
                f"Colunas presentes: {list(header_row)}"
            )

    parsed_members: List[AssociadoCreate] = []
    errors: List[ImportErrorDetail] = []
    seen_cpfs_in_file: Set[str] = set()

    # Itera sobre as linhas de dados (1-indexed considerando cabeçalho na linha 1)
    for line_num, row in enumerate(raw_rows[1:], start=2):
        # Ignora linhas totalmente vazias
        if not any(str(cell).strip() for cell in row):
            continue

        nome = str(row[col_map["nome"]]).strip() if col_map["nome"] < len(row) else ""
        cpf_raw = str(row[col_map["cpf"]]).strip() if col_map["cpf"] < len(row) else ""
        whatsapp_raw = str(row[col_map["whatsapp"]]).strip() if col_map["whatsapp"] < len(row) else ""
        email_raw = str(row[col_map["email"]]).strip() if col_map["email"] < len(row) else ""
        obs = str(row[col_map["observacoes"]]).strip() if "observacoes" in col_map and col_map["observacoes"] < len(row) else None
        foto = str(row[col_map["foto_url"]]).strip() if "foto_url" in col_map and col_map["foto_url"] < len(row) else None

        # 1. Validação de Nome
        if len(nome) < 3:
            errors.append(ImportErrorDetail(
                linha=line_num,
                campo="nome",
                motivo="Nome deve ter pelo menos 3 caracteres."
            ))
            continue

        # 2. Validação e formatação de CPF
        try:
            formatted_cpf = validate_and_format_cpf(cpf_raw)
        except ValueError as exc:
            errors.append(ImportErrorDetail(
                linha=line_num,
                campo="cpf",
                motivo=str(exc)
            ))
            continue

        # Verifica duplicidade de CPF dentro do próprio arquivo
        if formatted_cpf in seen_cpfs_in_file:
            errors.append(ImportErrorDetail(
                linha=line_num,
                campo="cpf",
                motivo=f"CPF {formatted_cpf} duplicado dentro da própria planilha."
            ))
            continue
        seen_cpfs_in_file.add(formatted_cpf)

        # 3. Validação e normalização de WhatsApp
        norm_phone = normalize_phone_number(whatsapp_raw)
        if len(norm_phone) < 10:
            errors.append(ImportErrorDetail(
                linha=line_num,
                campo="whatsapp",
                motivo=f"Número de WhatsApp inválido: '{whatsapp_raw}'."
            ))
            continue

        # 4. Validação de E-mail
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email_raw):
            errors.append(ImportErrorDetail(
                linha=line_num,
                campo="email",
                motivo=f"Formato de e-mail inválido: '{email_raw}'."
            ))
            continue

        parsed_members.append(AssociadoCreate(
            nome=nome,
            cpf=formatted_cpf,
            whatsapp=norm_phone,
            email=email_raw,
            foto_url=foto if foto else None,
            observacoes=obs if obs else None,
        ))

    return parsed_members, errors
