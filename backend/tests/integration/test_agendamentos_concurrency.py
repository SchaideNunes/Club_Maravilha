"""
Testes de integração e concorrência para Agendamento de Quadras.
"""
import pytest
import asyncio
from datetime import date, datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.agendamento import TipoQuadra


@pytest.mark.asyncio
async def test_full_court_booking_api_flow(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Cria associado ativo
    socio = Associado(
        nome="Sócio API Agendamento",
        cpf="707.707.707-70",
        whatsapp="+5511970707070",
        email="api_agendamento@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add(socio)
    await db_session.commit()

    inicio = datetime.now(timezone.utc) + timedelta(days=2, hours=14)
    fim = inicio + timedelta(hours=1)

    # 2. POST /api/v1/agendamentos/ -> Criação de reserva
    payload = {
        "associado_id": str(socio.id),
        "quadra": TipoQuadra.BEACH_TENNIS_1.value,
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "observacoes": "Partida teste API"
    }
    res = await async_client.post("/api/v1/agendamentos/", json=payload)
    assert res.status_code == 201
    data = res.json()
    agendamento_id = data["id"]
    assert data["status"] == "CONFIRMADO"

    # 3. GET /api/v1/agendamentos/{id} -> Detalhes
    res_get = await async_client.get(f"/api/v1/agendamentos/{agendamento_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == agendamento_id

    # 4. GET /api/v1/agendamentos/disponibilidade -> Checar grade
    dia_consulta = inicio.date().isoformat()
    res_disp = await async_client.get(
        "/api/v1/agendamentos/disponibilidade",
        params={"quadra": TipoQuadra.BEACH_TENNIS_1.value, "data": dia_consulta}
    )
    assert res_disp.status_code == 200
    grade = res_disp.json()
    assert len(grade["slots"]) > 0
    # O slot do horário reservado deve constar como disponivel=False
    slot_ocupado = next((s for s in grade["slots"] if s["agendamento_id"] == agendamento_id), None)
    assert slot_ocupado is not None
    assert slot_ocupado["disponivel"] is False

    # 5. POST /api/v1/agendamentos/{id}/cancelar -> Cancelamento com mais de 2h de antecedência
    res_cancel = await async_client.post(f"/api/v1/agendamentos/{agendamento_id}/cancelar")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELADO"


@pytest.mark.asyncio
async def test_concurrent_booking_double_booking_prevention(async_client: AsyncClient, db_session: AsyncSession):
    """
    Simula 2 requisições paralelas concorrentes tentando agendar a mesma quadra e horário exato.
    Garante que exatamente 1 agendamento é aprovado (201) e o outro é rejeitado com 409 Conflict.
    """
    socio_a = Associado(
        nome="Jogador Concorrente A",
        cpf="801.801.801-80",
        whatsapp="+5511980108010",
        email="concorrente_a@clube.com",
        status=StatusAssociado.ATIVO
    )
    socio_b = Associado(
        nome="Jogador Concorrente B",
        cpf="802.802.802-80",
        whatsapp="+5511980208020",
        email="concorrente_b@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add_all([socio_a, socio_b])
    await db_session.commit()

    inicio = datetime.now(timezone.utc) + timedelta(days=3, hours=18)
    fim = inicio + timedelta(hours=1)

    payload_a = {
        "associado_id": str(socio_a.id),
        "quadra": TipoQuadra.TENIS_1.value,
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat()
    }
    payload_b = {
        "associado_id": str(socio_b.id),
        "quadra": TipoQuadra.TENIS_1.value,
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat()
    }

    # Dispara ambas as requisições em paralelo
    responses = await asyncio.gather(
        async_client.post("/api/v1/agendamentos/", json=payload_a),
        async_client.post("/api/v1/agendamentos/", json=payload_b)
    )

    status_codes = [r.status_code for r in responses]
    # Exatamente um deve ser 201 Created e o outro 409 Conflict
    assert 201 in status_codes
    assert 409 in status_codes
