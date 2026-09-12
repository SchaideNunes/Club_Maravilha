"""
Testes unitários para regras de negócio de Convidados, Cota de 8 e QR Code na Catraca.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.schemas.convidado import ConvidadoCreate
from app.services.convidado_service import ConvidadoService


@pytest.mark.asyncio
async def test_emitir_convite_gratuito_dentro_da_cota(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio = Associado(
        nome="Titular Convidante",
        cpf="112.112.112-11",
        whatsapp="+5511912121212",
        email="titular_conv@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    hoje = date(2026, 9, 15)
    convite = await service.emitir_convite(
        ConvidadoCreate(
            associado_titular_id=socio.id,
            nome="Visitante Amigo 1",
            data_visita=hoje
        )
    )

    assert convite.id is not None
    assert convite.is_gratuito is True
    assert convite.valor_cobrado == Decimal("0.00")
    assert convite.status == StatusConvidado.EMITIDO
    assert len(convite.qr_code_token) == 64


@pytest.mark.asyncio
async def test_emitir_convite_excedente_a_partir_do_nono(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio = Associado(
        nome="Titular Família Grande",
        cpf="223.223.223-22",
        whatsapp="+5511923232323",
        email="familia_grande@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    mes_visita = date(2026, 9, 20)

    # Emite 8 convites gratuitos (esgotando a franquia mensal de 8)
    for i in range(1, 9):
        c = await service.emitir_convite(
            ConvidadoCreate(
                associado_titular_id=socio.id,
                nome=f"Convidado Grátis {i}",
                data_visita=mes_visita
            )
        )
        assert c.is_gratuito is True
        assert c.valor_cobrado == Decimal("0.00")

    # 9º convite deve ser emitido como EXCEDENTE (R$ 35,00)
    convite_excedente = await service.emitir_convite(
        ConvidadoCreate(
            associado_titular_id=socio.id,
            nome="Convidado Excedente 9",
            data_visita=mes_visita
        )
    )

    assert convite_excedente.is_gratuito is False
    assert convite_excedente.valor_cobrado == Decimal("35.00")
    assert convite_excedente.status == StatusConvidado.EMITIDO


@pytest.mark.asyncio
async def test_emitir_convite_bloqueado_inadimplente(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio_inad = Associado(
        nome="Sócio Inadimplente Convite",
        cpf="334.334.334-33",
        whatsapp="+5511934343434",
        email="inad_conv@clube.com",
        status=StatusAssociado.INADIMPLENTE
    )
    db_session.add(socio_inad)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await service.emitir_convite(
            ConvidadoCreate(
                associado_titular_id=socio_inad.id,
                nome="Visitante Barrado",
                data_visita=date(2026, 9, 25)
            )
        )
    assert exc.value.status_code == 403
    assert "inadimplente" in exc.value.detail.lower() or "status" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_consultar_cota_mensal(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio = Associado(
        nome="Sócio Consulta Cota",
        cpf="445.445.445-44",
        whatsapp="+5511945454545",
        email="cota_consulta@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    # Emite 3 convites
    for i in range(3):
        await service.emitir_convite(
            ConvidadoCreate(
                associado_titular_id=socio.id,
                nome=f"Convidado {i}",
                data_visita=date(2026, 9, 10)
            )
        )

    cota = await service.consultar_cota(socio.id, ano=2026, mes=9)
    assert cota.franquia_total == 8
    assert cota.utilizados == 3
    assert cota.restantes == 5
    assert cota.excedentes_emitidos == 0


@pytest.mark.asyncio
async def test_validar_qr_code_na_catraca_data_correta_e_incorreta(db_session: AsyncSession):
    service = ConvidadoService(db_session)
    socio = Associado(
        nome="Sócio Dono Convite",
        cpf="556.556.556-55",
        whatsapp="+5511956565656",
        email="dono_convite@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    dia_autorizado = date(2026, 9, 18)
    convite = await service.emitir_convite(
        ConvidadoCreate(
            associado_titular_id=socio.id,
            nome="Convidado Catraca",
            data_visita=dia_autorizado
        )
    )

    # 1. Leitura em data divergente da autorizada -> Acesso Negado
    dia_errado = date(2026, 9, 17)
    res_errada = await service.validar_qr_catraca(token=convite.qr_code_token, data_leitura=dia_errado)
    assert res_errada.valido is False
    assert "apenas para o dia" in res_errada.mensagem

    # 2. Leitura no dia correto -> Acesso Liberado
    res_correta = await service.validar_qr_catraca(token=convite.qr_code_token, data_leitura=dia_autorizado)
    assert res_correta.valido is True
    assert "liberado" in res_correta.mensagem.lower()
    assert res_correta.convidado is not None
    assert res_correta.convidado.status == StatusConvidado.UTILIZADO
    assert res_correta.convidado.check_in_at is not None

    # 3. Segunda tentativa com o mesmo token já utilizado -> Acesso Negado
    res_reutilizado = await service.validar_qr_catraca(token=convite.qr_code_token, data_leitura=dia_autorizado)
    assert res_reutilizado.valido is False
    assert "já utilizado" in res_reutilizado.mensagem.lower()
