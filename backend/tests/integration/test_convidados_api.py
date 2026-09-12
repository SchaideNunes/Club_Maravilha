"""
Testes de integração para Gestão de Convidados e Faturamento Agregado de Excedentes.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.schemas.convidado import ConvidadoCreate
from app.schemas.fatura import FaturaCreate
from app.services.convidado_service import ConvidadoService
from app.services.fatura_service import FaturaService


@pytest.mark.asyncio
async def test_convidados_crud_and_quota_api(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Cria associado ativo
    socio = Associado(
        nome="Sócio Titular Convidados API",
        cpf="991.991.991-99",
        whatsapp="+5511991919191",
        email="titular_api_conv@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    hoje = date.today()

    # 2. POST /api/v1/convidados/ -> Emissão de convite gratuito
    payload = {
        "associado_titular_id": str(socio.id),
        "nome": "Convidado Especial 1",
        "cpf": "123.456.789-00",
        "data_visita": hoje.isoformat()
    }
    res_post = await async_client.post("/api/v1/convidados/", json=payload)
    assert res_post.status_code == 201
    data_conv = res_post.json()
    convite_id = data_conv["id"]
    token = data_conv["qr_code_token"]
    assert data_conv["is_gratuito"] is True
    assert data_conv["valor_cobrado"] == "0.00"

    # 3. GET /api/v1/convidados/cota/{id}
    res_cota = await async_client.get(f"/api/v1/convidados/cota/{socio.id}")
    assert res_cota.status_code == 200
    cota = res_cota.json()
    assert cota["utilizados"] == 1
    assert cota["restantes"] == 7

    # 4. POST /api/v1/convidados/validar-qr -> Bipar na catraca
    res_val = await async_client.post(
        "/api/v1/convidados/validar-qr",
        json={"token": token, "data_leitura": hoje.isoformat()}
    )
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["valido"] is True
    assert val_data["convidado"]["status"] == "UTILIZADO"

    # 5. GET /api/v1/convidados/{id}
    res_det = await async_client.get(f"/api/v1/convidados/{convite_id}")
    assert res_det.status_code == 200
    assert res_det.json()["status"] == "UTILIZADO"


@pytest.mark.asyncio
async def test_fatura_aggregates_excess_guests_automatically(db_session: AsyncSession):
    convidado_service = ConvidadoService(db_session)
    fatura_service = FaturaService(db_session)

    # 1. Cria titular
    socio = Associado(
        nome="Sócio Agregação Fatura",
        cpf="992.992.992-92",
        whatsapp="+5511992929292",
        email="agregacao_fatura@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    mes_visita = date(2026, 10, 5)

    # 2. Emite 8 gratuitos
    for i in range(8):
        await convidado_service.emitir_convite(
            ConvidadoCreate(
                associado_titular_id=socio.id,
                nome=f"Grátis {i}",
                data_visita=mes_visita
            )
        )

    # 3. Emite 2 excedentes (2 * R$ 35,00 = R$ 70,00)
    c_exc1 = await convidado_service.emitir_convite(
        ConvidadoCreate(
            associado_titular_id=socio.id,
            nome="Excedente 1",
            data_visita=mes_visita
        )
    )
    c_exc2 = await convidado_service.emitir_convite(
        ConvidadoCreate(
            associado_titular_id=socio.id,
            nome="Excedente 2",
            data_visita=mes_visita
        )
    )
    assert c_exc1.is_gratuito is False
    assert c_exc2.is_gratuito is False

    # 4. Cria fatura mensal Pix para o sócio
    fatura = await fatura_service.create_fatura(
        FaturaCreate(
            associado_id=socio.id,
            referencia_mes="2026-10",
            valor_base=Decimal("150.00"),
            valor_convidados_excedentes=Decimal("0.00"),
            valor_desconto=Decimal("0.00"),
            valor_total=Decimal("150.00"),
            data_vencimento=date(2026, 10, 10)
        )
    )

    # 5. Verifica se os 2 excedentes foram agregados automaticamente
    assert fatura.valor_convidados_excedentes == Decimal("70.00")
    assert fatura.valor_total == Decimal("220.00")

    # Verifica vínculo dos convites com a fatura
    await db_session.refresh(c_exc1)
    await db_session.refresh(c_exc2)
    assert c_exc1.fatura_agregada_id == fatura.id
    assert c_exc2.fatura_agregada_id == fatura.id
