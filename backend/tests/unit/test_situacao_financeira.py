"""
Feature 2 (MVP) - Situação financeira derivada das faturas do associado.

Contratos definidos aqui (a implementar):
- app.schemas.associado.SituacaoFinanceira(str, Enum): EM_DIA | PENDENTE | ATRASADO
- app.services.associado_service.calcular_situacao_financeira(status_faturas: Iterable[StatusFatura])
  -> SituacaoFinanceira, com prioridade ATRASADO > PENDENTE > EM_DIA.
  Faturas PAGO/CANCELADO não contam (não estão em aberto).
"""
import pytest

from app.models.fatura import StatusFatura
from app.schemas.associado import SituacaoFinanceira
from app.services.associado_service import calcular_situacao_financeira


def test_enum_situacao_financeira_valores():
    assert [s.value for s in SituacaoFinanceira] == ["EM_DIA", "PENDENTE", "ATRASADO"]
    assert SituacaoFinanceira("EM_DIA") is SituacaoFinanceira.EM_DIA


@pytest.mark.parametrize(
    "status_faturas,esperado",
    [
        ([], SituacaoFinanceira.EM_DIA),
        ([StatusFatura.PAGO], SituacaoFinanceira.EM_DIA),
        ([StatusFatura.CANCELADO, StatusFatura.PAGO], SituacaoFinanceira.EM_DIA),
        ([StatusFatura.PENDENTE], SituacaoFinanceira.PENDENTE),
        ([StatusFatura.PAGO, StatusFatura.PENDENTE], SituacaoFinanceira.PENDENTE),
        ([StatusFatura.ATRASADA], SituacaoFinanceira.ATRASADO),
        ([StatusFatura.PENDENTE, StatusFatura.ATRASADA], SituacaoFinanceira.ATRASADO),
        ([StatusFatura.ATRASADA, StatusFatura.PAGO, StatusFatura.PENDENTE], SituacaoFinanceira.ATRASADO),
    ],
)
def test_calcular_situacao_financeira_prioridade(status_faturas, esperado):
    assert calcular_situacao_financeira(status_faturas) is esperado


def test_calcular_situacao_financeira_aceita_iteravel_qualquer():
    gerador = (s for s in [StatusFatura.PENDENTE])
    assert calcular_situacao_financeira(gerador) is SituacaoFinanceira.PENDENTE
