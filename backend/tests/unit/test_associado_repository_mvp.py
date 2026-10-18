"""
Testes do AssociadoRepository para os campos do MVP: persistência do dia de vencimento
e carregamento da relação de convidados (contador de convites do mês).
"""
from datetime import date
from app.models.associado import Associado
from app.models.convidado import Convidado
from app.repositories.associado_repository import AssociadoRepository
from app.schemas.associado import AssociadoCreate, AssociadoUpdate


def _create(**extra) -> AssociadoCreate:
    return AssociadoCreate(
        nome="Maria Maravilha",
        cpf="529.982.247-25",
        whatsapp="(75) 99999-9999",
        email="maria@maravilha.com",
        **extra,
    )


async def _associado_com_convites_no_mes(repo: AssociadoRepository, db_session) -> Associado:
    associado = await repo.create(_create(dia_vencimento=12))
    db_session.add_all([
        Convidado(associado_titular_id=associado.id, nome="Conv 1", data_visita=date.today()),
        Convidado(associado_titular_id=associado.id, nome="Conv 2", data_visita=date.today()),
    ])
    await db_session.commit()
    db_session.expunge_all()
    return associado


async def test_create_persiste_dia_vencimento_e_whatsapp_higienizado(db_session):
    repo = AssociadoRepository(db_session)

    associado = await repo.create(_create(dia_vencimento=12))

    assert associado.dia_vencimento == 12
    assert associado.whatsapp == "5575999999999"


async def test_get_by_id_so_carrega_convidados_quando_solicitado(db_session):
    repo = AssociadoRepository(db_session)
    criado = await _associado_com_convites_no_mes(repo, db_session)

    sem_convidados = await repo.get_by_id(criado.id)
    assert sem_convidados.convidados_usados_mes == 0  # relação não carregada: sem IO implícito

    db_session.expunge_all()
    com_convidados = await repo.get_by_id(criado.id, com_convidados=True)
    assert com_convidados.convidados_usados_mes == 2


async def test_list_paginated_carrega_convidados_da_pagina(db_session):
    repo = AssociadoRepository(db_session)
    await _associado_com_convites_no_mes(repo, db_session)

    itens, total = await repo.list_paginated()

    assert total == 1
    assert itens[0].convidados_usados_mes == 2


async def test_update_mantem_contador_correto_mesmo_sem_carga_previa_dos_convidados(db_session):
    repo = AssociadoRepository(db_session)
    criado = await _associado_com_convites_no_mes(repo, db_session)

    associado = await repo.get_by_id(criado.id)  # sem convidados carregados
    atualizado = await repo.update(associado, AssociadoUpdate(dia_vencimento=7))

    assert atualizado.dia_vencimento == 7
    assert atualizado.convidados_usados_mes == 2
