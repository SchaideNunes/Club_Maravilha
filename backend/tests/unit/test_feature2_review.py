"""
Testes unitários para as correções e regras refinadas da Feature 2 (Code Review):
1. Trava pessimista (for_update=True) nos fluxos de emissão de convidados
2. Validação matemática de CPF (módulo 11) nos schemas de convidado
3. Proteção de dia_vencimento no upsert da importação de planilhas
4. Limites de upload (read_only, max_linhas, captura de csv.Error, mensagem genérica de erro)
5. Validação unificada de elegibilidade (bloqueado, inadimplente, faturas atrasadas)
6. Fuso horário oficial do clube (app/core/clock.py::hoje_clube)
7. Busca de associados com escape de wildcards e validação estrita de dígitos de CPF
"""
import csv
import io
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import openpyxl
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import agora_clube, get_clube_tz, hoje_clube
from app.core.config import settings
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.schemas.associado import AssociadoCreate, AssociadoUpdate
from app.schemas.convidado import (
    ConvidadoAssociadoCreate,
    ConvidadoCreate,
)
from app.services.convidado_service import ConvidadoService
from app.services.excel_import_service import parse_excel_or_csv_bytes


# ---------------------------------------------------------------------------
# 1. Concorrência: for_update=True no get_by_id do titular antes da emissão
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emitir_convite_usa_for_update_true():
    """Garante que emitir_convite invoca get_by_id com for_update=True para serialização pessimista."""
    mock_session = AsyncMock(spec=AsyncSession)
    service = ConvidadoService(mock_session)

    socio_id = uuid.uuid4()
    socio_mock = Associado(
        id=socio_id,
        nome="Sócio Trava",
        cpf="529.982.247-25",
        whatsapp="5575999990000",
        email="trava@clube.com",
        status=StatusAssociado.ATIVO,
    )

    service.associado_repo.get_by_id = AsyncMock(return_value=socio_mock)
    service._validar_elegibilidade = AsyncMock()
    service._calcular_cobranca = AsyncMock(return_value=(True, "GRATUITO", Decimal("0.00"), 0, 1, 8, Decimal("35.00"), None))
    service.convidado_repo.create = AsyncMock(return_value=Convidado(id=uuid.uuid4(), associado_titular_id=socio_id, nome="Visitante", data_visita=date.today()))

    data = ConvidadoCreate(
        associado_titular_id=socio_id,
        nome="Visitante Trava",
        data_visita=date.today(),
    )
    await service.emitir_convite(data)

    service.associado_repo.get_by_id.assert_awaited_once_with(socio_id, for_update=True)


@pytest.mark.asyncio
async def test_adicionar_convidado_associado_usa_for_update_true():
    """Garante que adicionar_convidado_associado invoca get_by_id com for_update=True."""
    mock_session = AsyncMock(spec=AsyncSession)
    service = ConvidadoService(mock_session)

    socio_id = uuid.uuid4()
    socio_mock = Associado(
        id=socio_id,
        nome="Sócio Trava Rápido",
        cpf="529.982.247-25",
        whatsapp="5575999990000",
        email="trava_rapido@clube.com",
        status=StatusAssociado.ATIVO,
    )

    service.associado_repo.get_by_id = AsyncMock(return_value=socio_mock)
    service._validar_elegibilidade = AsyncMock()
    service._calcular_cobranca = AsyncMock(return_value=(True, "GRATUITO", Decimal("0.00"), 0, 1, 8, Decimal("35.00"), None))
    service.convidado_repo.create = AsyncMock(return_value=Convidado(
        id=uuid.uuid4(),
        associado_titular_id=socio_id,
        nome="Visitante Rápido",
        data_visita=date.today(),
        status=StatusConvidado.EMITIDO,
        is_gratuito=True,
        valor_cobrado=Decimal("0.00"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        qr_code_token="a" * 64
    ))

    data = ConvidadoAssociadoCreate(nome="Visitante Rápido")
    await service.adicionar_convidado_associado(socio_id, data)

    service.associado_repo.get_by_id.assert_awaited_once_with(socio_id, for_update=True)


# ---------------------------------------------------------------------------
# 2. Validação matemática de CPF em schemas de convidados
# ---------------------------------------------------------------------------

def test_convidado_associado_create_cpf_invalido_rejeita_com_422():
    with pytest.raises(ValidationError) as exc:
        ConvidadoAssociadoCreate(nome="Visitante Inválido", cpf="123")
    assert "CPF deve conter exatamente 11 dígitos" in str(exc.value)


def test_convidado_create_cpf_invalido_rejeita_com_422():
    with pytest.raises(ValidationError) as exc:
        ConvidadoCreate(
            associado_titular_id=uuid.uuid4(),
            nome="Visitante Inválido",
            data_visita=date.today(),
            cpf="123"
        )
    assert "CPF deve conter exatamente 11 dígitos" in str(exc.value)


def test_convidado_schemas_aceitam_cpf_nulo_ou_vazio():
    c1 = ConvidadoAssociadoCreate(nome="Visitante Sem CPF", cpf=None)
    assert c1.cpf is None

    c2 = ConvidadoAssociadoCreate(nome="Visitante Com Vazio", cpf="")
    assert c2.cpf is None

    c3 = ConvidadoAssociadoCreate(nome="Visitante Com Espacos", cpf="   ")
    assert c3.cpf is None

    c4 = ConvidadoAssociadoCreate(nome="Visitante Válido", cpf="52998224725")
    assert c4.cpf == "529.982.247-25"


# ---------------------------------------------------------------------------
# 3. Upsert e dia_vencimento
# ---------------------------------------------------------------------------

def test_parse_planilha_sem_coluna_vencimento_nao_marca_campo_como_informado():
    csv_content = "Nome,CPF,WhatsApp,Email\nAna Maria,529.982.247-25,5575999990001,ana@clube.com\n".encode("utf-8")
    members, errors = parse_excel_or_csv_bytes(csv_content, "membros.csv")

    assert len(members) == 1
    assert len(errors) == 0
    # O valor padrão está presente para novas inserções
    assert members[0].dia_vencimento == settings.DIA_VENCIMENTO_PADRAO
    # Mas não deve estar no conjunto de campos informados pela planilha (model_fields_set)
    assert "dia_vencimento" not in members[0].model_fields_set


def test_parse_planilha_com_coluna_vencimento_marca_campo_como_informado():
    csv_content = "Nome,CPF,WhatsApp,Email,Vencimento\nBruno Dias,529.982.247-25,5575999990001,bruno@clube.com,18\n".encode("utf-8")
    members, errors = parse_excel_or_csv_bytes(csv_content, "membros.csv")

    assert len(members) == 1
    assert len(errors) == 0
    assert members[0].dia_vencimento == 18
    assert "dia_vencimento" in members[0].model_fields_set


@pytest.mark.asyncio
async def test_bulk_import_upsert_preserva_vencimento_se_nao_informado(db_session: AsyncSession):
    repo = AssociadoRepository(db_session)
    # Cria associado original com dia_vencimento = 5
    socio = Associado(
        nome="Original",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="original@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=5,
    )
    db_session.add(socio)
    await db_session.commit()

    # Importa sem passar dia_vencimento (simulando planilha sem coluna de vencimento)
    member = AssociadoCreate(
        nome="Original Atualizado",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="original@clube.com",
    )
    assert "dia_vencimento" not in member.model_fields_set

    imported, updated, ignored, errors = await repo.bulk_import([member], atualizar_existentes=True)
    assert updated == 1
    assert len(errors) == 0

    recarregado = await repo.get_by_cpf("529.982.247-25")
    assert recarregado.nome == "Original Atualizado"
    assert recarregado.dia_vencimento == 5  # Preservou o 5, NÃO sobrescreveu com o default 10!


@pytest.mark.asyncio
async def test_bulk_import_upsert_atualiza_vencimento_quando_informado(db_session: AsyncSession):
    repo = AssociadoRepository(db_session)
    socio = Associado(
        nome="Mudar Vencimento",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="venc@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=5,
    )
    db_session.add(socio)
    await db_session.commit()

    member = AssociadoCreate(
        nome="Mudar Vencimento",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="venc@clube.com",
        dia_vencimento=25,
    )
    assert "dia_vencimento" in member.model_fields_set

    imported, updated, ignored, errors = await repo.bulk_import([member], atualizar_existentes=True)
    assert updated == 1

    recarregado = await repo.get_by_cpf("529.982.247-25")
    assert recarregado.dia_vencimento == 25


# ---------------------------------------------------------------------------
# 4. Upload e limites: max_linhas, read_only, csv.Error, erro seguro
# ---------------------------------------------------------------------------

def test_parse_csv_excede_limite_maximo_linhas():
    # Cria CSV com mais que settings.IMPORT_MAX_LINHAS (5000)
    linhas = ["Nome,CPF,WhatsApp,Email"]
    for i in range(settings.IMPORT_MAX_LINHAS + 2):
        linhas.append(f"Pessoa {i},529.982.247-25,5575999990000,p{i}@clube.com")
    csv_bytes = "\n".join(linhas).encode("utf-8")

    with pytest.raises(ValueError) as exc:
        parse_excel_or_csv_bytes(csv_bytes, "muitas_linhas.csv")
    assert f"excede o limite máximo permitido de {settings.IMPORT_MAX_LINHAS} linhas" in str(exc.value)


def test_parse_excel_excede_limite_maximo_linhas():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Nome", "CPF", "WhatsApp", "Email"])
    for i in range(settings.IMPORT_MAX_LINHAS + 2):
        ws.append([f"Sócio {i}", "529.982.247-25", "5575999990000", f"s{i}@clube.com"])

    bio = io.BytesIO()
    wb.save(bio)
    wb_bytes = bio.getvalue()

    with pytest.raises(ValueError) as exc:
        parse_excel_or_csv_bytes(wb_bytes, "grande.xlsx")
    assert f"excede o limite máximo permitido de {settings.IMPORT_MAX_LINHAS} linhas" in str(exc.value)


def test_parse_csv_malformado_captura_csv_error(monkeypatch):
    """Simula csv.Error durante o streaming de CSV."""
    def fake_reader(*args, **kwargs):
        class MalformedReader:
            def __iter__(self):
                yield ["Nome", "CPF", "WhatsApp", "Email"]
                raise csv.Error("line contains NULL byte")
        return MalformedReader()

    monkeypatch.setattr(csv, "reader", fake_reader)

    with pytest.raises(ValueError) as exc:
        parse_excel_or_csv_bytes(b"Nome,CPF,WhatsApp,Email\n", "dados.csv")
    assert "Arquivo CSV malformado ou inválido." in str(exc.value)


def test_parse_excel_corrompido_retorna_mensagem_generica():
    with pytest.raises(ValueError) as exc:
        parse_excel_or_csv_bytes(b"conteudo binario totalmente invalido que nao e zip nem xlsx", "arquivo.xlsx")
    # Não deve vazar tracebacks de zipfile nem BadZipFile do openpyxl
    assert str(exc.value) == "Arquivo Excel corrompido ou inválido."


# ---------------------------------------------------------------------------
# 5. Validação unificada de elegibilidade
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validar_elegibilidade_bloqueia_status_bloqueado(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio_bloqueado = Associado(
        id=uuid.uuid4(),
        nome="Bloqueado",
        cpf="529.982.247-25",
        whatsapp="5575999990000",
        email="bloq@clube.com",
        status=StatusAssociado.BLOQUEADO,
    )
    with pytest.raises(HTTPException) as exc:
        await service._validar_elegibilidade(socio_bloqueado)
    assert exc.value.status_code == 403
    assert "bloqueado" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_validar_elegibilidade_bloqueia_status_inadimplente(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio_inad = Associado(
        id=uuid.uuid4(),
        nome="Inadimplente",
        cpf="529.982.247-25",
        whatsapp="5575999990000",
        email="inad@clube.com",
        status=StatusAssociado.INADIMPLENTE,
    )
    with pytest.raises(HTTPException) as exc:
        await service._validar_elegibilidade(socio_inad)
    assert exc.value.status_code == 403
    assert "status cadastral" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_validar_elegibilidade_bloqueia_fatura_atrasada(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio = Associado(
        nome="Sócio Com Fatura",
        cpf="529.982.247-25",
        whatsapp="5575999990000",
        email="fatura@clube.com",
        status=StatusAssociado.ATIVO,
    )
    db_session.add(socio)
    await db_session.flush()

    fatura = Fatura(
        associado_id=socio.id,
        status=StatusFatura.ATRASADA,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 9, 10),
        referencia_mes="2026-09",
    )
    db_session.add(fatura)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await service._validar_elegibilidade(socio)
    assert exc.value.status_code == 403
    assert "mensalidade vencida" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# 6. Fuso horário oficial do clube (app/core/clock.py)
# ---------------------------------------------------------------------------

def test_clock_helper_com_fuso_horario_oficial():
    """Garante que hoje_clube respeita o timezone America/Sao_Paulo (UTC-3)."""
    assert str(get_clube_tz()) == "America/Sao_Paulo"

    # Simula 02:30 UTC do dia 01/11/2026 -> em São Paulo ainda são 23:30 do dia 31/10/2026
    dt_utc_madrugada = datetime(2026, 11, 1, 2, 30, 0, tzinfo=timezone.utc)

    with patch("app.core.clock.datetime") as mock_datetime:
        mock_datetime.now.side_effect = lambda tz=None: dt_utc_madrugada.astimezone(tz) if tz else dt_utc_madrugada
        resultado_hoje = hoje_clube()

    assert resultado_hoje == date(2026, 10, 31)

    # Simula 03:01 UTC do dia 01/11/2026 -> em São Paulo já é 00:01 do dia 01/11/2026
    dt_utc_virada = datetime(2026, 11, 1, 3, 1, 0, tzinfo=timezone.utc)
    with patch("app.core.clock.datetime") as mock_datetime:
        mock_datetime.now.side_effect = lambda tz=None: dt_utc_virada.astimezone(tz) if tz else dt_utc_virada
        resultado_virada = hoje_clube()

    assert resultado_virada == date(2026, 11, 1)


# ---------------------------------------------------------------------------
# 7. Busca com escape de wildcards e validação estrita de dígitos de CPF
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_busca_com_wildcard_escapado_nao_injeta_like(db_session: AsyncSession):
    repo = AssociadoRepository(db_session)
    s1 = Associado(
        nome="Lucas 100% Maravilha",
        cpf="529.982.247-25",
        whatsapp="5575999990001",
        email="lucas1@clube.com",
        status=StatusAssociado.ATIVO,
    )
    s2 = Associado(
        nome="Lucas Outro",
        cpf="729.982.247-33",
        whatsapp="5575999990002",
        email="lucas2@clube.com",
        status=StatusAssociado.ATIVO,
    )
    db_session.add_all([s1, s2])
    await db_session.commit()

    # Busca literal por "100%" não deve trazer s2 (que conteria se % fosse curinga)
    itens, total = await repo.list_paginated(q="100%")
    assert total == 1
    assert itens[0].id == s1.id
