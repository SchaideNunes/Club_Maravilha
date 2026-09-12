"""
Testes unitários para as regras de negócio de Agendamento de Quadras.
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agendamento import AgendamentoQuadra, StatusAgendamento, TipoQuadra
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.schemas.agendamento import AgendamentoCreate
from app.services.agendamento_service import AgendamentoService


@pytest.mark.asyncio
async def test_create_agendamento_success(db_session: AsyncSession):
    service = AgendamentoService(db_session)
    socio = Associado(
        nome="Tenista Ativo",
        cpf="101.101.101-10",
        whatsapp="+5511910101010",
        email="tenista@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    inicio = datetime.now(timezone.utc) + timedelta(days=1, hours=2)
    fim = inicio + timedelta(hours=1)

    agendamento = await service.create_agendamento(
        AgendamentoCreate(
            associado_id=socio.id,
            quadra=TipoQuadra.BEACH_TENNIS_1,
            data_inicio=inicio,
            data_fim=fim,
            observacoes="Treino dupla"
        )
    )

    assert agendamento.id is not None
    assert agendamento.status == StatusAgendamento.CONFIRMADO
    assert agendamento.quadra == TipoQuadra.BEACH_TENNIS_1


@pytest.mark.asyncio
async def test_create_agendamento_inadimplente_blocked(db_session: AsyncSession):
    service = AgendamentoService(db_session)
    socio = Associado(
        nome="Sócio Devedor",
        cpf="202.202.202-20",
        whatsapp="+5511920202020",
        email="devedor@clube.com",
        status=StatusAssociado.INADIMPLENTE
    )
    db_session.add(socio)
    await db_session.commit()

    inicio = datetime.now(timezone.utc) + timedelta(days=1)
    fim = inicio + timedelta(hours=1)

    with pytest.raises(HTTPException) as exc:
        await service.create_agendamento(
            AgendamentoCreate(
                associado_id=socio.id,
                quadra=TipoQuadra.BEACH_TENNIS_1,
                data_inicio=inicio,
                data_fim=fim
            )
        )
    assert exc.value.status_code == 403
    assert "inadimplente" in exc.value.detail.lower() or "status" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_agendamento_fatura_vencida_blocked(db_session: AsyncSession):
    service = AgendamentoService(db_session)
    socio = Associado(
        nome="Sócio com Boleto Vencido",
        cpf="303.303.303-30",
        whatsapp="+5511930303030",
        email="fatura_vencida@clube.com",
        status=StatusAssociado.ATIVO  # Status ainda ativo no cadastro, mas com fatura vencida
    )
    db_session.add(socio)
    await db_session.commit()

    fatura_vencida = Fatura(
        associado_id=socio.id,
        referencia_mes="2026-08",
        valor_base=150.0,
        valor_total=150.0,
        data_vencimento=datetime.now(timezone.utc).date() - timedelta(days=5),
        status=StatusFatura.VENCIDO
    )
    db_session.add(fatura_vencida)
    await db_session.commit()

    inicio = datetime.now(timezone.utc) + timedelta(days=2)
    fim = inicio + timedelta(hours=1)

    with pytest.raises(HTTPException) as exc:
        await service.create_agendamento(
            AgendamentoCreate(
                associado_id=socio.id,
                quadra=TipoQuadra.TENIS_1,
                data_inicio=inicio,
                data_fim=fim
            )
        )
    assert exc.value.status_code == 403
    assert "vencida" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_agendamento_exceeds_max_active_reservations(db_session: AsyncSession):
    service = AgendamentoService(db_session)
    socio = Associado(
        nome="Sócio Ativo Fominha",
        cpf="404.404.404-40",
        whatsapp="+5511940404040",
        email="fominha@clube.com",
        status=StatusAssociado.ATIVO,
        limite_reservas_ativas=2
    )
    db_session.add(socio)
    await db_session.commit()

    agora = datetime.now(timezone.utc)
    # Cria duas reservas futuras ativas (atingindo o teto)
    res1 = AgendamentoQuadra(
        associado_id=socio.id,
        quadra=TipoQuadra.TENIS_1,
        data_inicio=agora + timedelta(days=1),
        data_fim=agora + timedelta(days=1, hours=1),
        status=StatusAgendamento.CONFIRMADO
    )
    res2 = AgendamentoQuadra(
        associado_id=socio.id,
        quadra=TipoQuadra.TENIS_2,
        data_inicio=agora + timedelta(days=2),
        data_fim=agora + timedelta(days=2, hours=1),
        status=StatusAgendamento.CONFIRMADO
    )
    db_session.add_all([res1, res2])
    await db_session.commit()

    # Tentativa de criar a 3ª reserva futura deve ser barrada
    with pytest.raises(HTTPException) as exc:
        await service.create_agendamento(
            AgendamentoCreate(
                associado_id=socio.id,
                quadra=TipoQuadra.BEACH_TENNIS_2,
                data_inicio=agora + timedelta(days=3),
                data_fim=agora + timedelta(days=3, hours=1)
            )
        )
    assert exc.value.status_code == 400
    assert "limite" in exc.value.detail.lower() or "teto" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_create_agendamento_conflict_double_booking(db_session: AsyncSession):
    service = AgendamentoService(db_session)
    socio1 = Associado(
        nome="Sócio 1",
        cpf="501.501.501-50",
        whatsapp="+5511950105010",
        email="socio1@clube.com",
        status=StatusAssociado.ATIVO
    )
    socio2 = Associado(
        nome="Sócio 2",
        cpf="502.502.502-50",
        whatsapp="+5511950205020",
        email="socio2@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add_all([socio1, socio2])
    await db_session.commit()

    inicio = datetime.now(timezone.utc) + timedelta(days=1, hours=10)
    fim = inicio + timedelta(hours=1)

    # Reserva inicial do sócio 1
    await service.create_agendamento(
        AgendamentoCreate(
            associado_id=socio1.id,
            quadra=TipoQuadra.FUTEBOL_SOCIETY,
            data_inicio=inicio,
            data_fim=fim
        )
    )

    # Sócio 2 tenta reservar no mesmo horário e quadra
    with pytest.raises(HTTPException) as exc:
        await service.create_agendamento(
            AgendamentoCreate(
                associado_id=socio2.id,
                quadra=TipoQuadra.FUTEBOL_SOCIETY,
                data_inicio=inicio,
                data_fim=fim
            )
        )
    assert exc.value.status_code == 409
    assert "indisponível" in exc.value.detail.lower() or "conflito" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_cancel_agendamento_policy(db_session: AsyncSession):
    service = AgendamentoService(db_session)
    socio = Associado(
        nome="Sócio Cancelamento",
        cpf="606.606.606-60",
        whatsapp="+5511960606060",
        email="cancel@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    agora = datetime.now(timezone.utc)

    # 1. Agendamento com mais de 2 horas de antecedência -> Cancelamento permitido
    ag_valido = AgendamentoQuadra(
        associado_id=socio.id,
        quadra=TipoQuadra.BEACH_TENNIS_1,
        data_inicio=agora + timedelta(hours=5),
        data_fim=agora + timedelta(hours=6),
        status=StatusAgendamento.CONFIRMADO
    )
    db_session.add(ag_valido)
    await db_session.commit()

    cancelado = await service.cancel_agendamento(ag_valido.id)
    assert cancelado.status == StatusAgendamento.CANCELADO

    # 2. Agendamento com menos de 2 horas (ex: daqui a 30 minutos) -> Rejeitado
    ag_em_cima_da_hora = AgendamentoQuadra(
        associado_id=socio.id,
        quadra=TipoQuadra.BEACH_TENNIS_1,
        data_inicio=agora + timedelta(minutes=30),
        data_fim=agora + timedelta(minutes=90),
        status=StatusAgendamento.CONFIRMADO
    )
    db_session.add(ag_em_cima_da_hora)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await service.cancel_agendamento(ag_em_cima_da_hora.id)
    assert exc.value.status_code == 400
    assert "antecedência" in exc.value.detail.lower()
