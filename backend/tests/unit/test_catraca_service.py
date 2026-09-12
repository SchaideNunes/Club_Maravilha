"""
Testes unitários para o serviço de Catraca Facial e Whitelist Offline.
"""
import pytest
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.services.catraca_service import CatracaService


@pytest.mark.asyncio
async def test_catraca_whitelist_filtering(db_session: AsyncSession):
    service = CatracaService(db_session)
    hoje = date(2026, 9, 12)

    # 1. Sócio Ativo e Adimplente (Deve estar na Whitelist)
    socio_ok = Associado(
        nome="Sócio Liberado Catraca",
        cpf="111.222.333-44",
        whatsapp="+5511911112222",
        email="socio_ok@clube.com",
        facial_id="FACE_ID_001",
        status=StatusAssociado.ATIVO
    )
    # 2. Sócio com Status Inadimplente (NÃO deve estar na Whitelist)
    socio_inad = Associado(
        nome="Sócio Status Inadimplente",
        cpf="222.333.444-55",
        whatsapp="+5511922223333",
        email="socio_inad@clube.com",
        facial_id="FACE_ID_002",
        status=StatusAssociado.INADIMPLENTE
    )
    # 3. Sócio com Status Ativo mas com Fatura Vencida (NÃO deve estar na Whitelist)
    socio_vencido = Associado(
        nome="Sócio Ativo com Boleto Vencido",
        cpf="333.444.555-66",
        whatsapp="+5511933334444",
        email="socio_vencido@clube.com",
        facial_id="FACE_ID_003",
        status=StatusAssociado.ATIVO
    )
    db_session.add_all([socio_ok, socio_inad, socio_vencido])
    await db_session.commit()

    fatura_vencida = Fatura(
        associado_id=socio_vencido.id,
        referencia_mes="2026-08",
        valor_base=150.0,
        valor_total=150.0,
        data_vencimento=hoje - timedelta(days=5),
        status=StatusFatura.VENCIDO
    )
    db_session.add(fatura_vencida)

    # 4. Convidado de hoje (Deve estar na Whitelist)
    conv_hoje = Convidado(
        associado_titular_id=socio_ok.id,
        nome="Convidado Hoje",
        data_visita=hoje,
        status=StatusConvidado.EMITIDO
    )
    # 5. Convidado de amanhã (NÃO deve estar na Whitelist de hoje)
    conv_amanha = Convidado(
        associado_titular_id=socio_ok.id,
        nome="Convidado Amanhã",
        data_visita=hoje + timedelta(days=1),
        status=StatusConvidado.EMITIDO
    )
    db_session.add_all([conv_hoje, conv_amanha])
    await db_session.commit()

    # Consulta a Whitelist
    whitelist = await service.get_whitelist(data_consulta=hoje)

    # Membros liberados
    member_ids = [m["facial_id"] for m in whitelist["members"]]
    assert "FACE_ID_001" in member_ids
    assert "FACE_ID_002" not in member_ids
    assert "FACE_ID_003" not in member_ids

    # Visitantes liberados
    guest_tokens = [g["qr_token"] for g in whitelist["guests"]]
    assert conv_hoje.qr_code_token in guest_tokens
    assert conv_amanha.qr_code_token not in guest_tokens


@pytest.mark.asyncio
async def test_catraca_process_guest_turnstile_event(db_session: AsyncSession):
    service = CatracaService(db_session)
    socio = Associado(
        nome="Sócio Titular Catraca",
        cpf="444.555.666-77",
        whatsapp="+5511944445555",
        email="socio_tit_cat@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    conv = Convidado(
        associado_titular_id=socio.id,
        nome="Visitante Catraca",
        data_visita=date.today(),
        status=StatusConvidado.EMITIDO
    )
    db_session.add(conv)
    await db_session.commit()

    # Evento de passagem física com QR Code de visitante
    event_payload = {
        "event_type": "ENTRY",
        "credential_type": "QR_CODE",
        "token": conv.qr_code_token,
        "turnstile_id": "CATRACA_PORTARIA_1"
    }

    result = await service.process_turnstile_event(event_payload)
    assert result["authorized"] is True

    await db_session.refresh(conv)
    assert conv.status == StatusConvidado.UTILIZADO
    assert conv.check_in_at is not None
