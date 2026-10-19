"""
Feature 2 (MVP) - Consultas agregadas do AssociadoRepository para a listagem do painel.

Contratos definidos aqui (a implementar):
- AssociadoRepository.contar_convidados_mes(associado_ids: Sequence[UUID], ano: int, mes: int) -> Dict[UUID, int]
  UMA única query agregada (COUNT ... GROUP BY associado_titular_id) restrita ao mês de `data_visita`,
  ignorando convites CANCELADO. Ids sem convites podem ficar ausentes do dict (equivale a 0).
- AssociadoRepository.situacoes_financeiras(associado_ids: Sequence[UUID], referencia_mes: str) -> Dict[UUID, SituacaoFinanceira]
  UMA única query agregada sobre faturas em aberto (PENDENTE/ATRASADA) com referencia_mes <= referencia_mes
  informado (faturas de meses futuros são ignoradas). ATRASADA em qualquer mês anterior em aberto => ATRASADO
  (atraso persiste até a baixa); senão PENDENTE; ids ausentes do dict equivalem a EM_DIA.
- AssociadoRepository.list_paginated(..., situacao: Optional[SituacaoFinanceira] = None, referencia_mes: Optional[str] = None)
  continua retornando (itens, total) e NÃO carrega a relação `convidados` (sem histórico inteiro).
"""
from datetime import date
from decimal import Decimal
from typing import List

import pytest
from sqlalchemy import event

from app.models.associado import Associado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import Fatura, StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.schemas.associado import SituacaoFinanceira

REF = "2026-10"


def _associado(n: int) -> Associado:
    return Associado(
        nome=f"Associado {n:02d}",
        cpf=f"000.000.000-{n:02d}",
        whatsapp=f"55759999900{n:02d}",
        email=f"assoc{n}@club.com",
    )


def _fatura(associado: Associado, referencia_mes: str, status: StatusFatura) -> Fatura:
    ano, mes = (int(p) for p in referencia_mes.split("-"))
    return Fatura(
        associado_id=associado.id,
        referencia_mes=referencia_mes,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(ano, mes, 10),
        status=status,
    )


class _ContadorSQL:
    def __init__(self, sync_engine) -> None:
        self.engine = sync_engine
        self.statements: List[str] = []

    def _on_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.statements.append(statement)

    def __enter__(self) -> "_ContadorSQL":
        event.listen(self.engine, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *exc) -> None:
        event.remove(self.engine, "before_cursor_execute", self._on_execute)


@pytest.fixture
async def associados(db_session) -> List[Associado]:
    itens = [_associado(n) for n in range(1, 5)]
    db_session.add_all(itens)
    await db_session.commit()
    return itens


async def test_contar_convidados_mes_agrega_por_associado_em_uma_query(db_session, associados):
    a1, a2, a3, _a4 = associados
    db_session.add_all([
        Convidado(associado_titular_id=a1.id, nome="C1", data_visita=date(2026, 10, 1)),
        Convidado(associado_titular_id=a1.id, nome="C2", data_visita=date(2026, 10, 31)),
        Convidado(associado_titular_id=a1.id, nome="Cancelado", data_visita=date(2026, 10, 5),
                  status=StatusConvidado.CANCELADO),
        Convidado(associado_titular_id=a1.id, nome="Mes anterior", data_visita=date(2026, 9, 30)),
        Convidado(associado_titular_id=a1.id, nome="Ano anterior", data_visita=date(2025, 10, 15)),
        Convidado(associado_titular_id=a2.id, nome="Utilizado", data_visita=date(2026, 10, 2),
                  status=StatusConvidado.UTILIZADO),
        Convidado(associado_titular_id=a3.id, nome="Proximo mes", data_visita=date(2026, 11, 1)),
    ])
    await db_session.commit()

    repo = AssociadoRepository(db_session)
    with _ContadorSQL(db_session.bind.sync_engine) as sql:
        contagens = await repo.contar_convidados_mes([a.id for a in associados], ano=2026, mes=10)

    assert len(sql.statements) == 1, sql.statements
    assert "count" in sql.statements[0].lower()
    assert contagens.get(a1.id, 0) == 2
    assert contagens.get(a2.id, 0) == 1
    assert contagens.get(a3.id, 0) == 0
    assert contagens.get(associados[3].id, 0) == 0


async def test_contar_convidados_mes_lista_vazia_nao_consulta_banco(db_session):
    repo = AssociadoRepository(db_session)
    with _ContadorSQL(db_session.bind.sync_engine) as sql:
        assert await repo.contar_convidados_mes([], ano=2026, mes=10) == {}
    assert sql.statements == []


async def test_situacoes_financeiras_deriva_das_faturas_em_aberto(db_session, associados):
    a_em_dia, a_pendente, a_atrasado, a_sem_fatura = associados
    db_session.add_all([
        _fatura(a_em_dia, REF, StatusFatura.PAGO),
        _fatura(a_em_dia, "2026-09", StatusFatura.CANCELADO),
        _fatura(a_em_dia, "2026-11", StatusFatura.PENDENTE),  # mês futuro: ignorada
        _fatura(a_pendente, REF, StatusFatura.PENDENTE),
        _fatura(a_pendente, "2026-09", StatusFatura.PAGO),
        _fatura(a_atrasado, REF, StatusFatura.PENDENTE),
        _fatura(a_atrasado, "2026-09", StatusFatura.ATRASADA),  # atraso anterior persiste
    ])
    await db_session.commit()

    repo = AssociadoRepository(db_session)
    with _ContadorSQL(db_session.bind.sync_engine) as sql:
        situacoes = await repo.situacoes_financeiras([a.id for a in associados], referencia_mes=REF)

    assert len(sql.statements) == 1, sql.statements
    assert situacoes.get(a_em_dia.id, SituacaoFinanceira.EM_DIA) is SituacaoFinanceira.EM_DIA
    assert situacoes.get(a_pendente.id, SituacaoFinanceira.EM_DIA) is SituacaoFinanceira.PENDENTE
    assert situacoes.get(a_atrasado.id, SituacaoFinanceira.EM_DIA) is SituacaoFinanceira.ATRASADO
    assert situacoes.get(a_sem_fatura.id, SituacaoFinanceira.EM_DIA) is SituacaoFinanceira.EM_DIA


async def test_list_paginated_filtra_por_situacao_com_total_correto(db_session, associados):
    a_em_dia, a_pendente, a_atrasado, a_sem_fatura = associados
    db_session.add_all([
        _fatura(a_em_dia, REF, StatusFatura.PAGO),
        _fatura(a_pendente, REF, StatusFatura.PENDENTE),
        _fatura(a_atrasado, REF, StatusFatura.ATRASADA),
    ])
    await db_session.commit()
    repo = AssociadoRepository(db_session)

    itens, total = await repo.list_paginated(situacao=SituacaoFinanceira.EM_DIA, referencia_mes=REF)
    assert total == 2
    assert {i.id for i in itens} == {a_em_dia.id, a_sem_fatura.id}

    itens, total = await repo.list_paginated(situacao=SituacaoFinanceira.PENDENTE, referencia_mes=REF)
    assert (total, [i.id for i in itens]) == (1, [a_pendente.id])

    itens, total = await repo.list_paginated(situacao=SituacaoFinanceira.ATRASADO, referencia_mes=REF)
    assert (total, [i.id for i in itens]) == (1, [a_atrasado.id])


async def test_list_paginated_nao_carrega_historico_de_convidados(db_session, associados):
    db_session.add(Convidado(associado_titular_id=associados[0].id, nome="C1", data_visita=date.today()))
    await db_session.commit()
    db_session.expunge_all()

    repo = AssociadoRepository(db_session)
    with _ContadorSQL(db_session.bind.sync_engine) as sql:
        itens, total = await repo.list_paginated()

    assert total == 4 and len(itens) == 4
    assert not any("convidados.qr_code_token" in s for s in sql.statements), sql.statements
