"""
Feature 1 (MVP) - Testes dos schemas Pydantic v2.

Contratos definidos aqui (a implementar):
- AssociadoCreate.dia_vencimento: int = settings.DIA_VENCIMENTO_PADRAO (1..31)
- AssociadoCreate/AssociadoUpdate.whatsapp: higienizado para padrão Baileys (só dígitos, DDI 55)
- AssociadoUpdate.dia_vencimento: Optional[int] (1..31)
- AssociadoResponse.dia_vencimento: int ; AssociadoResponse.convidados_usados_mes: int = 0
- FaturaCreate.valor_total: Optional -> calculado (base + excedentes - desconto) quando omitido;
  se informado e incoerente -> ValidationError; total negativo -> ValidationError
- app.schemas.fatura.FaturaBaixaManual {forma_pagamento: PIX|CARTAO|DINHEIRO, data_pagamento: Optional[datetime]}
- app.schemas.configuracao.ConfiguracaoResponse / ConfiguracaoUpdate
- app.schemas.log_mensagem.LogMensagemResponse
- Todos exportados em app.schemas
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.associado import AssociadoCreate, AssociadoResponse, AssociadoUpdate
from app.schemas.fatura import FaturaCreate


BASE_ASSOCIADO = {
    "nome": "Maria Maravilha",
    "cpf": "529.982.247-25",
    "email": "maria@maravilha.com",
}


# ------------------------------------------------------------------------------
# Associado
# ------------------------------------------------------------------------------
def test_associado_create_dia_vencimento_default_settings():
    data = AssociadoCreate(**BASE_ASSOCIADO, whatsapp="+55 75 99999-9999")
    assert data.dia_vencimento == settings.DIA_VENCIMENTO_PADRAO


@pytest.mark.parametrize("dia", [1, 15, 28, 31])
def test_associado_create_dia_vencimento_valido(dia):
    data = AssociadoCreate(**BASE_ASSOCIADO, whatsapp="5575999999999", dia_vencimento=dia)
    assert data.dia_vencimento == dia


@pytest.mark.parametrize("dia", [0, 32, -1])
def test_associado_create_dia_vencimento_invalido(dia):
    with pytest.raises(ValidationError):
        AssociadoCreate(**BASE_ASSOCIADO, whatsapp="5575999999999", dia_vencimento=dia)


@pytest.mark.parametrize("dia", [0, 32])
def test_associado_update_dia_vencimento_invalido(dia):
    with pytest.raises(ValidationError):
        AssociadoUpdate(dia_vencimento=dia)


def test_associado_update_dia_vencimento_opcional():
    assert AssociadoUpdate().dia_vencimento is None
    assert AssociadoUpdate(dia_vencimento=5).dia_vencimento == 5


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("+55 (75) 99999-9999", "5575999999999"),
        ("5575999999999", "5575999999999"),
        ("(75) 99999-9999", "5575999999999"),
        ("75999999999", "5575999999999"),
        ("(75) 3222-1111", "557532221111"),
        ("+5511988887777", "5511988887777"),
        ("11 98888.7777", "5511988887777"),
    ],
)
def test_associado_create_whatsapp_higienizado_padrao_baileys(entrada, esperado):
    data = AssociadoCreate(**BASE_ASSOCIADO, whatsapp=entrada)
    assert data.whatsapp == esperado


@pytest.mark.parametrize("entrada", ["12345", "abcdefghijk", "123456789012345", "4475999999999"])
def test_associado_create_whatsapp_invalido(entrada):
    with pytest.raises(ValidationError):
        AssociadoCreate(**BASE_ASSOCIADO, whatsapp=entrada)


def test_associado_update_whatsapp_higienizado():
    data = AssociadoUpdate(whatsapp="(75) 99999-9999")
    assert data.whatsapp == "5575999999999"


def _response_payload(**extra):
    agora = datetime.now(timezone.utc)
    return {
        **BASE_ASSOCIADO,
        "whatsapp": "5575999999999",
        "id": uuid.uuid4(),
        "status": "ATIVO",
        "limite_reservas_ativas": 2,
        "data_adesao": date(2026, 1, 1),
        "created_at": agora,
        "updated_at": agora,
        **extra,
    }


def test_associado_response_expoe_dia_vencimento_e_convidados_usados_mes():
    resp = AssociadoResponse(**_response_payload(dia_vencimento=20, convidados_usados_mes=4))
    dumped = resp.model_dump()
    assert dumped["dia_vencimento"] == 20
    assert dumped["convidados_usados_mes"] == 4


def test_associado_response_convidados_usados_mes_default_zero():
    resp = AssociadoResponse(**_response_payload(dia_vencimento=10))
    assert resp.convidados_usados_mes == 0


def test_associado_response_from_model_attributes():
    from app.models.associado import Associado

    agora = datetime.now(timezone.utc)
    associado = Associado(
        id=uuid.uuid4(),
        nome="Maria Maravilha",
        cpf="529.982.247-25",
        whatsapp="5575999999999",
        email="maria@maravilha.com",
        status="ATIVO",
        limite_reservas_ativas=2,
        data_adesao=date(2026, 1, 1),
        dia_vencimento=15,
        created_at=agora,
        updated_at=agora,
    )
    associado.convidados = []
    resp = AssociadoResponse.model_validate(associado)
    assert resp.dia_vencimento == 15
    assert resp.convidados_usados_mes == 0


# ------------------------------------------------------------------------------
# Fatura
# ------------------------------------------------------------------------------
def _fatura_payload(**extra):
    return {
        "associado_id": uuid.uuid4(),
        "referencia_mes": "2026-10",
        "valor_base": Decimal("150.00"),
        "data_vencimento": date(2026, 10, 10),
        **extra,
    }


def test_fatura_create_calcula_valor_total_quando_omitido():
    data = FaturaCreate(
        **_fatura_payload(
            valor_convidados_excedentes=Decimal("70.00"),
            valor_desconto=Decimal("10.00"),
        )
    )
    assert data.valor_total == Decimal("210.00")


def test_fatura_create_aceita_valor_total_coerente():
    data = FaturaCreate(
        **_fatura_payload(valor_convidados_excedentes=Decimal("35.00"), valor_total=Decimal("185.00"))
    )
    assert data.valor_total == Decimal("185.00")


def test_fatura_create_rejeita_valor_total_incoerente():
    with pytest.raises(ValidationError):
        FaturaCreate(
            **_fatura_payload(valor_convidados_excedentes=Decimal("35.00"), valor_total=Decimal("150.00"))
        )


def test_fatura_create_rejeita_total_negativo():
    with pytest.raises(ValidationError):
        FaturaCreate(**_fatura_payload(valor_desconto=Decimal("200.00")))


@pytest.mark.parametrize("forma", ["PIX", "CARTAO", "DINHEIRO"])
def test_fatura_baixa_manual_formas_aceitas(forma):
    from app.schemas.fatura import FaturaBaixaManual

    data = FaturaBaixaManual(forma_pagamento=forma)
    assert data.forma_pagamento.value == forma
    assert data.data_pagamento is None


@pytest.mark.parametrize("forma", ["BOLETO", "CHEQUE", ""])
def test_fatura_baixa_manual_formas_rejeitadas(forma):
    from app.schemas.fatura import FaturaBaixaManual

    with pytest.raises(ValidationError):
        FaturaBaixaManual(forma_pagamento=forma)


def test_fatura_baixa_manual_com_data_pagamento():
    from app.schemas.fatura import FaturaBaixaManual

    quando = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)
    data = FaturaBaixaManual(forma_pagamento="PIX", data_pagamento=quando)
    assert data.data_pagamento == quando


def test_fatura_response_aceita_status_atrasada():
    from app.schemas.fatura import FaturaResponse

    agora = datetime.now(timezone.utc)
    resp = FaturaResponse(
        **_fatura_payload(valor_total=Decimal("150.00")),
        id=uuid.uuid4(),
        status="ATRASADA",
        forma_pagamento="CARTAO",
        created_at=agora,
        updated_at=agora,
    )
    assert resp.status.value == "ATRASADA"
    assert resp.forma_pagamento.value == "CARTAO"


# ------------------------------------------------------------------------------
# Configuracao
# ------------------------------------------------------------------------------
def _config_response_payload(**extra):
    agora = datetime.now(timezone.utc)
    return {
        "id": 1,
        "valor_mensalidade": Decimal("150.00"),
        "franquia_convidados": 8,
        "valor_convidado_extra": Decimal("35.00"),
        "chave_pix": "pix@club.com",
        "horario_disparo": "08:00",
        "automacao_ativa": True,
        "template_d_menos_3": "Olá {nome}, vence em {vencimento}.",
        "template_d0": "Olá {nome}, {valor_total} hoje. Pix {chave_pix}",
        "template_recibo": "Obrigado {nome}!",
        "template_d_mais_3": "Olá {nome}, atraso de {valor_total}.",
        "template_d_mais_7": "Olá {nome}, bloqueio. Pix {chave_pix}",
        "updated_at": agora,
        **extra,
    }


def test_configuracao_response_campos():
    from app.schemas.configuracao import ConfiguracaoResponse

    resp = ConfiguracaoResponse(**_config_response_payload())
    dumped = resp.model_dump()
    for campo in (
        "valor_mensalidade", "franquia_convidados", "valor_convidado_extra", "chave_pix",
        "horario_disparo", "automacao_ativa", "template_d_menos_3", "template_d0",
        "template_recibo", "template_d_mais_3", "template_d_mais_7",
    ):
        assert campo in dumped


async def test_configuracao_response_from_model(db_session):
    from app.models.configuracao import Configuracao
    from app.schemas.configuracao import ConfiguracaoResponse

    cfg = Configuracao()
    db_session.add(cfg)
    await db_session.commit()
    await db_session.refresh(cfg)

    resp = ConfiguracaoResponse.model_validate(cfg)
    assert resp.franquia_convidados == 8
    assert resp.valor_mensalidade == Decimal("150.00")
    assert resp.horario_disparo == "08:00"
    assert "{nome}" in resp.template_recibo


def test_configuracao_update_parcial_tudo_opcional():
    from app.schemas.configuracao import ConfiguracaoUpdate

    data = ConfiguracaoUpdate(automacao_ativa=False)
    assert data.model_dump(exclude_unset=True) == {"automacao_ativa": False}


@pytest.mark.parametrize("horario", ["00:00", "08:00", "23:59", "18:30"])
def test_configuracao_update_horario_valido(horario):
    from app.schemas.configuracao import ConfiguracaoUpdate

    assert ConfiguracaoUpdate(horario_disparo=horario).horario_disparo == horario


@pytest.mark.parametrize("horario", ["8:00", "24:00", "12:60", "0800", "ab:cd", ""])
def test_configuracao_update_horario_invalido(horario):
    from app.schemas.configuracao import ConfiguracaoUpdate

    with pytest.raises(ValidationError):
        ConfiguracaoUpdate(horario_disparo=horario)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("valor_mensalidade", Decimal("-0.01")),
        ("valor_convidado_extra", Decimal("-1")),
        ("franquia_convidados", -1),
    ],
)
def test_configuracao_update_valores_negativos_rejeitados(campo, valor):
    from app.schemas.configuracao import ConfiguracaoUpdate

    with pytest.raises(ValidationError):
        ConfiguracaoUpdate(**{campo: valor})


def test_configuracao_update_aceita_zero():
    from app.schemas.configuracao import ConfiguracaoUpdate

    data = ConfiguracaoUpdate(
        valor_mensalidade=Decimal("0"), valor_convidado_extra=Decimal("0"), franquia_convidados=0
    )
    assert data.franquia_convidados == 0


def test_configuracao_update_template_vazio_rejeitado():
    from app.schemas.configuracao import ConfiguracaoUpdate

    with pytest.raises(ValidationError):
        ConfiguracaoUpdate(template_d0="")


# ------------------------------------------------------------------------------
# LogMensagem
# ------------------------------------------------------------------------------
async def test_log_mensagem_response_from_model(db_session):
    from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
    from app.schemas.log_mensagem import LogMensagemResponse

    log = LogMensagem(
        destinatario="5575999999999",
        etapa=EtapaRegua.RECIBO,
        mensagem="Recibo de pagamento",
        status=StatusEnvio.SUCESSO,
    )
    db_session.add(log)
    await db_session.commit()
    await db_session.refresh(log)

    resp = LogMensagemResponse.model_validate(log)
    dumped = resp.model_dump(mode="json")
    assert dumped["etapa"] == "RECIBO"
    assert dumped["status"] == "SUCESSO"
    assert dumped["destinatario"] == "5575999999999"
    assert dumped["associado_id"] is None
    assert dumped["fatura_id"] is None
    assert dumped["erro"] is None
    assert dumped["enviado_em"] is not None
    assert "id" in dumped and "mensagem" in dumped


def test_app_schemas_exporta_novos_schemas():
    import app.schemas as schemas

    for nome in ("ConfiguracaoResponse", "ConfiguracaoUpdate", "LogMensagemResponse", "FaturaBaixaManual"):
        assert hasattr(schemas, nome), f"app.schemas deve exportar {nome}"
        assert nome in schemas.__all__
