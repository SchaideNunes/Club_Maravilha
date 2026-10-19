"""
Serviço de importação e validação de planilhas Excel (.xlsx) e arquivos (.csv).
Validação matemática estrita de CPF, higienização do WhatsApp (padrão Baileys) e extração em lote.
"""
import csv
import io
import logging
import re
import unicodedata
from typing import Any, List, Optional, Set, Tuple
import openpyxl
from pydantic import ValidationError
from app.core.config import settings
from app.core.cpf import validate_and_format_cpf
from app.core.phone import sanitize_whatsapp_number
from app.schemas.associado import AssociadoCreate, ImportErrorDetail

logger = logging.getLogger(__name__)


def _normalize_header(header: str) -> str:
    """Normaliza o nome da coluna removendo acentos, pontuações, espaços e caixa."""
    nfkd = unicodedata.normalize("NFKD", str(header))
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


def _cell_to_str(c: Any) -> str:
    if c is None:
        return ""
    if isinstance(c, float) and c.is_integer():
        return str(int(c))
    return str(c).strip()


class ParsedMembersList(list):
    total_lidos: int = 0


def parse_excel_or_csv_bytes(
    file_bytes: bytes,
    filename: str
) -> Tuple[List[AssociadoCreate], List[ImportErrorDetail]]:
    """
    Lê o conteúdo em bytes de uma planilha .xlsx ou .csv e extrai associados válidos,
    coletando erros linha a linha sem interromper o processo global.
    """
    lower_filename = filename.lower()
    raw_rows: List[Tuple[int, List[str]]] = []

    if lower_filename.endswith(".xlsx") or lower_filename.endswith(".xlsm"):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        except Exception as exc:
            logger.error("Erro ao carregar arquivo Excel: %s", exc, exc_info=True)
            raise ValueError("Arquivo Excel corrompido ou inválido.") from exc

        try:
            sheet = wb.active
            for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
                if row_idx > settings.IMPORT_MAX_LINHAS + 1:
                    raise ValueError(f"Planilha excede o limite máximo permitido de {settings.IMPORT_MAX_LINHAS} linhas.")
                raw_rows.append((row_idx, [_cell_to_str(c) for c in row]))
        finally:
            wb.close()
    elif lower_filename.endswith(".csv"):
        # Tenta decodificar como UTF-8 com BOM, fallback para Latin-1
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        if not text.strip():
            raise ValueError("O arquivo enviado está vazio.")

        sample = text[:2048]
        delimiter = ";" if sample.count(";") >= sample.count(",") else ","
        try:
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            for row_idx, row in enumerate(reader, start=1):
                if row_idx > settings.IMPORT_MAX_LINHAS + 1:
                    raise ValueError(f"Arquivo CSV excede o limite máximo permitido de {settings.IMPORT_MAX_LINHAS} linhas.")
                raw_rows.append((row_idx, [str(c).strip() for c in row]))
        except csv.Error as exc:
            logger.error("Erro ao ler arquivo CSV: %s", exc, exc_info=True)
            raise ValueError("Arquivo CSV malformado ou inválido.") from exc
    else:
        raise ValueError("Formato de arquivo não suportado. Envie um arquivo .xlsx ou .csv.")

    if not raw_rows:
        raise ValueError("O arquivo enviado está vazio.")

    # Localização das colunas no cabeçalho (linha física 1)
    header_row = raw_rows[0][1]
    col_map = {}
    for idx, col in enumerate(header_row):
        norm = _normalize_header(col)
        if norm in ("nome", "nomecompleto", "nomedosocio", "associado", "socio"):
            col_map["nome"] = idx
        elif norm in ("cpf", "documento", "numcpf"):
            col_map["cpf"] = idx
        elif norm in ("whatsapp", "celular", "telefone", "contato", "fone", "tel", "telefonewhatsapp", "celularwhatsapp"):
            col_map["whatsapp"] = idx
        elif norm in ("email", "correioeletronico"):
            col_map["email"] = idx
        elif norm in ("diavencimento", "vencimento", "diadevencimento", "diadovencimento"):
            col_map["dia_vencimento"] = idx
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

    parsed_members = ParsedMembersList()
    errors: List[ImportErrorDetail] = []
    seen_cpfs_in_file: Set[str] = set()
    seen_emails_in_file: Set[str] = set()
    total_lidos = 0

    # Itera sobre as linhas de dados (começando na linha física 2)
    for physical_line_num, row in raw_rows[1:]:
        # Ignora linhas totalmente vazias (não contam como dados lidos)
        if not any(str(cell).strip() for cell in row):
            continue

        total_lidos += 1

        nome = str(row[col_map["nome"]]).strip() if col_map["nome"] < len(row) else ""
        cpf_raw = str(row[col_map["cpf"]]).strip() if col_map["cpf"] < len(row) else ""
        whatsapp_raw = str(row[col_map["whatsapp"]]).strip() if col_map["whatsapp"] < len(row) else ""
        email_raw = str(row[col_map["email"]]).strip() if col_map["email"] < len(row) else ""
        obs = str(row[col_map["observacoes"]]).strip() if "observacoes" in col_map and col_map["observacoes"] < len(row) and str(row[col_map["observacoes"]]).strip() else None
        foto = str(row[col_map["foto_url"]]).strip() if "foto_url" in col_map and col_map["foto_url"] < len(row) and str(row[col_map["foto_url"]]).strip() else None

        # 1. Validação de Nome
        if len(nome) < 3:
            errors.append(ImportErrorDetail(
                linha=physical_line_num,
                campo="nome",
                motivo="Nome deve ter pelo menos 3 caracteres."
            ))
            continue

        # 2. Validação e formatação de CPF
        try:
            formatted_cpf = validate_and_format_cpf(cpf_raw)
        except ValueError as exc:
            errors.append(ImportErrorDetail(
                linha=physical_line_num,
                campo="cpf",
                motivo=str(exc)
            ))
            continue

        # Verifica duplicidade de CPF dentro do próprio arquivo
        if formatted_cpf in seen_cpfs_in_file:
            errors.append(ImportErrorDetail(
                linha=physical_line_num,
                campo="cpf",
                motivo=f"CPF {formatted_cpf} duplicado dentro da própria planilha."
            ))
            continue
        seen_cpfs_in_file.add(formatted_cpf)

        # 3. Higienização do WhatsApp para o padrão Baileys (só dígitos com DDI 55)
        try:
            norm_phone = sanitize_whatsapp_number(whatsapp_raw)
        except ValueError:
            errors.append(ImportErrorDetail(
                linha=physical_line_num,
                campo="whatsapp",
                motivo=f"Número de WhatsApp inválido: '{whatsapp_raw}'."
            ))
            continue

        # 4. Validação e unicidade de E-mail dentro do arquivo
        clean_email = email_raw.lower().strip()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean_email):
            errors.append(ImportErrorDetail(
                linha=physical_line_num,
                campo="email",
                motivo=f"Formato de e-mail inválido: '{email_raw}'."
            ))
            continue

        if clean_email in seen_emails_in_file:
            errors.append(ImportErrorDetail(
                linha=physical_line_num,
                campo="email",
                motivo=f"E-mail {email_raw} duplicado dentro da própria planilha."
            ))
            continue
        seen_emails_in_file.add(clean_email)

        # 5. Validação de dia_vencimento (opcional: padrão settings.DIA_VENCIMENTO_PADRAO se omitido)
        dia_vencimento = None
        if "dia_vencimento" in col_map and col_map["dia_vencimento"] < len(row):
            raw_dia = str(row[col_map["dia_vencimento"]]).strip()
            if raw_dia != "" and raw_dia.lower() != "none":
                try:
                    val_f = float(raw_dia)
                    if not val_f.is_integer():
                        raise ValueError()
                    dia_int = int(val_f)
                    if not (1 <= dia_int <= 31):
                        raise ValueError()
                    dia_vencimento = dia_int
                except Exception:
                    errors.append(ImportErrorDetail(
                        linha=physical_line_num,
                        campo="dia_vencimento",
                        motivo=f"Dia de vencimento inválido: '{raw_dia}'. Deve ser um número inteiro entre 1 e 31."
                    ))
                    continue

        # 6. Criação do schema AssociadoCreate
        try:
            payload = {
                "nome": nome,
                "cpf": formatted_cpf,
                "whatsapp": norm_phone,
                "email": clean_email,
                "foto_url": foto,
                "observacoes": obs,
            }
            if dia_vencimento is not None:
                payload["dia_vencimento"] = dia_vencimento
            member = AssociadoCreate(**payload)
            member._line_num = physical_line_num
            parsed_members.append(member)
        except ValidationError as exc:
            erro = exc.errors()[0]
            errors.append(ImportErrorDetail(
                linha=physical_line_num,
                campo=str(erro["loc"][0]) if erro["loc"] else "linha",
                motivo=str(erro["msg"]).removeprefix("Value error, ")
            ))

    setattr(parsed_members, "total_lidos", total_lidos)
    return parsed_members, errors
