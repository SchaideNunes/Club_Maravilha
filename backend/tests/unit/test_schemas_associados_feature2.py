"""
Feature 2 (MVP) - Schemas de Associado e do convite rápido por associado.

Contratos definidos aqui (a implementar):
- AssociadoCreate.cpf: validado matematicamente (módulo 11) NO SCHEMA e normalizado para
  "000.000.000-00" -> CPF inválido vira ValidationError (HTTP 422 na API).
- AssociadoCreate.email: normalizado em minúsculas (unicidade case-insensitive).
- AssociadoResponse: novos campos `franquia_convidados: int` e
  `situacao_financeira: SituacaoFinanceira` (default EM_DIA).
- app.schemas.convidado.ConvidadoAssociadoCreate {nome (3..150), cpf: Optional, data_visita: Optional[date] = None}
- app.schemas.convidado.AdicionarConvidadoResponse {
      convidado: ConvidadoResponse, is_gratuito: bool, tipo: "GRATUITO" | "EXCEDENTE",
      convidados_usados_mes: int, franquia: int, excedentes_mes: int,
      valor_taxa_extra: Decimal, aviso: Optional[str] = None }
- app.schemas.associado.ImportAssociadosResult ganha `total_atualizados: int` (default 0).
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.associado import (
    AssociadoCreate,
    AssociadoResponse,
    ImportAssociadosResult,
    SituacaoFinanceira,
)
from app.schemas.convidado import AdicionarConvidadoResponse, ConvidadoAssociadoCreate

BASE = {
    "nome": "Maria Maravilha",
    "whatsapp": "(75) 99999-9999",
    "email": "maria@maravilha.com",
}


@pytest.mark.parametrize("cpf", ["52998224725", "529.982.247-25", " 529.982.247-25 "])
def test_associado_create_normaliza_cpf_formatado(cpf):
    assert AssociadoCreate(**BASE, cpf=cpf).cpf == "529.982.247-25"


@pytest.mark.parametrize("cpf", ["52998224700", "111.111.111-11", "123", "abcdefghijk"])
def test_associado_create_rejeita_cpf_invalido(cpf):
    with pytest.raises(ValidationError) as exc:
        AssociadoCreate(**BASE, cpf=cpf)
    assert any(err["loc"][-1] == "cpf" for err in exc.value.errors())


def test_associado_create_normaliza_email_minusculo():
    data = AssociadoCreate(**{**BASE, "email": "Maria.Silva@Maravilha.COM"}, cpf="52998224725")
    assert data.email == "maria.silva@maravilha.com"


def _response_payload(**extra) -> dict:
    agora = datetime.now(timezone.utc)
    return {
        "id": uuid.uuid4(),
        "nome": "Maria Maravilha",
        "cpf": "529.982.247-25",
        "whatsapp": "5575999999999",
        "email": "maria@maravilha.com",
        "status": "ATIVO",
        "limite_reservas_ativas": 2,
        "data_adesao": date.today(),
        "dia_vencimento": 10,
        "created_at": agora,
        "updated_at": agora,
        **extra,
    }


def test_associado_response_expoe_franquia_e_situacao():
    resp = AssociadoResponse(
        **_response_payload(convidados_usados_mes=3, franquia_convidados=8, situacao_financeira="ATRASADO")
    )
    assert resp.convidados_usados_mes == 3
    assert resp.franquia_convidados == 8
    assert resp.situacao_financeira is SituacaoFinanceira.ATRASADO


def test_associado_response_situacao_default_em_dia():
    resp = AssociadoResponse(**_response_payload(franquia_convidados=8))
    assert resp.situacao_financeira is SituacaoFinanceira.EM_DIA


def test_convidado_associado_create_data_visita_opcional():
    data = ConvidadoAssociadoCreate(nome="Visitante Rápido")
    assert data.data_visita is None
    assert data.cpf is None


def test_convidado_associado_create_valida_nome():
    with pytest.raises(ValidationError):
        ConvidadoAssociadoCreate(nome="ab")


def _convidado_dict() -> dict:
    agora = datetime.now(timezone.utc)
    return {
        "id": uuid.uuid4(),
        "associado_titular_id": uuid.uuid4(),
        "nome": "Visitante",
        "data_visita": date.today(),
        "qr_code_token": "a" * 64,
        "status": "EMITIDO",
        "is_gratuito": False,
        "valor_cobrado": Decimal("35.00"),
        "created_at": agora,
        "updated_at": agora,
    }


def test_adicionar_convidado_response_campos():
    resp = AdicionarConvidadoResponse(
        convidado=_convidado_dict(),
        is_gratuito=False,
        tipo="EXCEDENTE",
        convidados_usados_mes=9,
        franquia=8,
        excedentes_mes=1,
        valor_taxa_extra=Decimal("35.00"),
        aviso="Franquia excedida",
    )
    dump = resp.model_dump(mode="json")
    assert set(dump) >= {
        "convidado", "is_gratuito", "tipo", "convidados_usados_mes",
        "franquia", "excedentes_mes", "valor_taxa_extra", "aviso",
    }
    assert dump["tipo"] == "EXCEDENTE"
    assert Decimal(dump["valor_taxa_extra"]) == Decimal("35.00")


def test_adicionar_convidado_response_rejeita_tipo_desconhecido():
    with pytest.raises(ValidationError):
        AdicionarConvidadoResponse(
            convidado=_convidado_dict(), is_gratuito=True, tipo="OUTRO", convidados_usados_mes=1,
            franquia=8, excedentes_mes=0, valor_taxa_extra=Decimal("35.00"),
        )


def test_import_result_total_atualizados_default_zero():
    res = ImportAssociadosResult(total_lidos=1, total_importados=1, total_ignorados_duplicados=0, erros=[])
    assert res.total_atualizados == 0
