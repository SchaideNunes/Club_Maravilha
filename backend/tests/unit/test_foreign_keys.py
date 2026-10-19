"""
Testes de integridade referencial. O conftest liga PRAGMA foreign_keys no SQLite dos testes,
então FK, ON DELETE SET NULL e CASCADE se comportam como no PostgreSQL de produção.
"""
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.associado import Associado
from app.models.convidado import Convidado
from app.models.fatura import Fatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio


def _associado(sufixo: str) -> Associado:
    return Associado(
        nome=f"Associado FK {sufixo}",
        cpf=f"111.000.000-{sufixo}",
        whatsapp="5575999999999",
        email=f"fk{sufixo}@maravilha.com",
    )


async def test_sqlite_dos_testes_aplica_foreign_keys(db_session):
    assert (await db_session.execute(text("PRAGMA foreign_keys"))).scalar_one() == 1


async def test_fk_inexistente_e_rejeitada(db_session):
    db_session.add(Convidado(associado_titular_id=uuid.uuid4(), nome="Sem titular", data_visita=date(2026, 10, 1)))

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_log_mensagem_com_fk_inexistente_e_rejeitado(db_session):
    db_session.add(LogMensagem(
        associado_id=uuid.uuid4(),
        destinatario="5575999999999",
        etapa=EtapaRegua.AVULSO,
        mensagem="Mensagem",
        status=StatusEnvio.SUCESSO,
    ))

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_excluir_associado_preserva_o_historico_de_logs_com_fks_nulas(db_session):
    """ON DELETE SET NULL: o log permanece (auditoria) mesmo sem o sócio e a fatura de origem."""
    associado = _associado("01")
    db_session.add(associado)
    await db_session.flush()
    fatura = Fatura(
        associado_id=associado.id,
        referencia_mes="2026-10",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 10, 10),
    )
    db_session.add(fatura)
    await db_session.flush()
    db_session.add(LogMensagem(
        associado_id=associado.id,
        fatura_id=fatura.id,
        destinatario="5575999999999",
        etapa=EtapaRegua.D0,
        mensagem="Vence hoje",
        status=StatusEnvio.SUCESSO,
    ))
    await db_session.commit()

    await db_session.delete(associado)  # cascata remove as faturas; os logs apenas perdem o vínculo
    await db_session.commit()
    db_session.expunge_all()

    log = (await db_session.execute(select(LogMensagem))).scalar_one()
    assert log.mensagem == "Vence hoje"
    assert log.associado_id is None
    assert log.fatura_id is None
