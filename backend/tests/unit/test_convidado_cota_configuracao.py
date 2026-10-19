"""
Feature 2 (MVP) - Cota de convidados lida da Configuracao (não de settings fixos) e
convite rápido por associado.

Contratos definidos aqui (a implementar em app.services.convidado_service.ConvidadoService):
- emitir_convite / consultar_cota usam Configuracao.franquia_convidados e
  Configuracao.valor_convidado_extra (via ConfiguracaoRepository.get_or_create).
- adicionar_convidado_associado(associado_id: UUID, data: ConvidadoAssociadoCreate) -> AdicionarConvidadoResponse
    * data_visita omitida => date.today()
    * contagem pelo mês de data_visita, ignorando CANCELADO (zera na virada do mês)
    * convite dentro da franquia: is_gratuito=True, tipo="GRATUITO", valor_cobrado=0, aviso=None
    * além da franquia: is_gratuito=False, tipo="EXCEDENTE", valor_cobrado=valor_convidado_extra,
      aviso = texto não vazio mencionando "franquia" e o valor no formato "R$ 35,00"
    * convidados_usados_mes inclui o convite recém-criado; excedentes_mes = max(0, usados - franquia)
    * valor_taxa_extra = Configuracao.valor_convidado_extra (valor unitário)
    * associado inexistente => HTTPException 404; BLOQUEADO => HTTPException 403 (detail cita "bloqueado")
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.associado import Associado, StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.schemas.convidado import ConvidadoAssociadoCreate, ConvidadoCreate
from app.services.convidado_service import ConvidadoService


async def _socio(db_session, status: StatusAssociado = StatusAssociado.ATIVO) -> Associado:
    socio = Associado(
        nome="Titular Cota Config",
        cpf="529.982.247-25",
        whatsapp="5575999990000",
        email="cota.config@club.com",
        status=status,
    )
    db_session.add(socio)
    await db_session.commit()
    return socio


async def _configurar(db_session, franquia: int, valor_extra: str) -> None:
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.franquia_convidados = franquia
    cfg.valor_convidado_extra = Decimal(valor_extra)
    await db_session.commit()


async def test_emitir_convite_respeita_franquia_e_valor_da_configuracao(db_session):
    socio = await _socio(db_session)
    await _configurar(db_session, franquia=2, valor_extra="50.00")
    service = ConvidadoService(db_session)
    visita = date(2026, 10, 20)

    convites = [
        await service.emitir_convite(
            ConvidadoCreate(associado_titular_id=socio.id, nome=f"Convidado {i}", data_visita=visita)
        )
        for i in range(3)
    ]

    assert [c.is_gratuito for c in convites] == [True, True, False]
    assert convites[2].valor_cobrado == Decimal("50.00")


async def test_consultar_cota_usa_configuracao(db_session):
    socio = await _socio(db_session)
    await _configurar(db_session, franquia=3, valor_extra="20.00")
    service = ConvidadoService(db_session)

    cota = await service.consultar_cota(socio.id, ano=2026, mes=10)

    assert cota.franquia_total == 3
    assert cota.restantes == 3
    assert cota.valor_unitario_excedente == Decimal("20.00")


async def test_adicionar_convidado_gratuito_com_data_padrao_hoje(db_session):
    socio = await _socio(db_session)
    service = ConvidadoService(db_session)

    resp = await service.adicionar_convidado_associado(socio.id, ConvidadoAssociadoCreate(nome="Visitante 1"))

    assert resp.is_gratuito is True
    assert resp.tipo == "GRATUITO"
    assert resp.convidados_usados_mes == 1
    assert resp.franquia == 8
    assert resp.excedentes_mes == 0
    assert resp.valor_taxa_extra == Decimal("35.00")
    assert resp.aviso is None
    assert resp.convidado.data_visita == date.today()
    assert resp.convidado.associado_titular_id == socio.id
    assert resp.convidado.valor_cobrado == Decimal("0.00")


async def test_adicionar_convidado_excedente_retorna_aviso(db_session):
    socio = await _socio(db_session)
    await _configurar(db_session, franquia=1, valor_extra="35.00")
    service = ConvidadoService(db_session)

    await service.adicionar_convidado_associado(socio.id, ConvidadoAssociadoCreate(nome="Primeiro"))
    resp = await service.adicionar_convidado_associado(socio.id, ConvidadoAssociadoCreate(nome="Segundo"))

    assert resp.is_gratuito is False
    assert resp.tipo == "EXCEDENTE"
    assert resp.convidados_usados_mes == 2
    assert resp.franquia == 1
    assert resp.excedentes_mes == 1
    assert resp.convidado.valor_cobrado == Decimal("35.00")
    assert resp.aviso and "franquia" in resp.aviso.lower()
    assert "R$ 35,00" in resp.aviso


async def test_adicionar_convidado_zera_na_virada_do_mes_e_ignora_cancelados(db_session):
    socio = await _socio(db_session)
    await _configurar(db_session, franquia=2, valor_extra="35.00")
    hoje = date.today()
    mes_anterior = hoje.replace(day=1) - timedelta(days=1)
    db_session.add_all([
        Convidado(associado_titular_id=socio.id, nome="Antigo 1", data_visita=mes_anterior),
        Convidado(associado_titular_id=socio.id, nome="Antigo 2", data_visita=mes_anterior),
        Convidado(associado_titular_id=socio.id, nome="Antigo 3", data_visita=mes_anterior),
        Convidado(associado_titular_id=socio.id, nome="Cancelado", data_visita=hoje,
                  status=StatusConvidado.CANCELADO),
    ])
    await db_session.commit()
    service = ConvidadoService(db_session)

    resp = await service.adicionar_convidado_associado(socio.id, ConvidadoAssociadoCreate(nome="Novo do Mes"))

    assert resp.is_gratuito is True
    assert resp.convidados_usados_mes == 1
    assert resp.excedentes_mes == 0


async def test_adicionar_convidado_associado_bloqueado_retorna_403(db_session):
    socio = await _socio(db_session, status=StatusAssociado.BLOQUEADO)
    service = ConvidadoService(db_session)

    with pytest.raises(HTTPException) as exc:
        await service.adicionar_convidado_associado(socio.id, ConvidadoAssociadoCreate(nome="Barrado"))

    assert exc.value.status_code == 403
    assert "bloqueado" in str(exc.value.detail).lower()


async def test_adicionar_convidado_associado_inexistente_retorna_404(db_session):
    import uuid

    service = ConvidadoService(db_session)
    with pytest.raises(HTTPException) as exc:
        await service.adicionar_convidado_associado(uuid.uuid4(), ConvidadoAssociadoCreate(nome="Ninguem"))
    assert exc.value.status_code == 404
