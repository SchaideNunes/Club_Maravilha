"""
Feature 6 - Totais do mês na listagem de faturas (tela de Mensalidades do painel).

Contrato: GET /api/v1/faturas/ passa a devolver, além de items/total/page/page_size/total_pages:
- `resumo`: {
      "total": int,            # faturas NÃO canceladas no escopo
      "pagas": int,            # status PAGO
      "pendentes": int,        # status PENDENTE
      "atrasadas": int,        # status ATRASADA
      "valor_total": Decimal,  # soma de valor_total das faturas não canceladas (string JSON "0.00")
      "valor_recebido": Decimal,  # soma de valor_total das faturas PAGO
  }
  Escopo do resumo: mesmos filtros `referencia_mes` e `associado_id` da listagem, mas IGNORA
  `status`, `q` e a paginação (os cards do mês ficam estáveis enquanto o operador filtra a tabela).
  Faturas CANCELADO não entram em nenhum contador/soma. Sem faturas -> zeros ("0.00").
- Cada item passa a expor também `associado_cpf` (str) para exibição/busca na tabela.
"""
from datetime import date
from decimal import Decimal

from httpx import AsyncClient

from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura

API = "/api/v1/faturas"


def _socio(n: int, nome: str) -> Associado:
    return Associado(
        nome=nome,
        cpf=f"000.000.{n:03d}-00",
        whatsapp=f"55759999900{n:02d}",
        email=f"socio{n}@clube.com",
        status=StatusAssociado.ATIVO,
        dia_vencimento=10,
        data_adesao=date(2025, 1, 1),
    )


async def _cenario(session):
    ana, bia, caio, duda, eva = (
        _socio(1, "Ana"),
        _socio(2, "Bia"),
        _socio(3, "Caio"),
        _socio(4, "Duda"),
        _socio(5, "Eva"),
    )
    session.add_all([ana, bia, caio, duda, eva])
    await session.flush()

    def fat(socio, status, total, ref="2026-11"):
        return Fatura(
            associado_id=socio.id,
            referencia_mes=ref,
            valor_base=Decimal(total),
            valor_total=Decimal(total),
            data_vencimento=date(int(ref[:4]), int(ref[5:]), 10),
            status=status,
        )

    session.add_all([
        fat(ana, StatusFatura.PAGO, "150.00"),
        fat(bia, StatusFatura.PAGO, "185.00"),
        fat(caio, StatusFatura.PENDENTE, "150.00"),
        fat(duda, StatusFatura.ATRASADA, "220.00"),
        fat(eva, StatusFatura.CANCELADO, "150.00"),
        # outro mês: não entra no resumo de 2026-11
        fat(ana, StatusFatura.PENDENTE, "999.00", ref="2026-10"),
    ])
    await session.commit()
    return ana


async def test_listagem_traz_resumo_do_mes(async_client: AsyncClient, db_session):
    await _cenario(db_session)

    res = await async_client.get(f"{API}/", params={"referencia_mes": "2026-11"})

    assert res.status_code == 200
    resumo = res.json()["resumo"]
    assert resumo["total"] == 4
    assert resumo["pagas"] == 2
    assert resumo["pendentes"] == 1
    assert resumo["atrasadas"] == 1
    assert Decimal(resumo["valor_total"]) == Decimal("705.00")
    assert Decimal(resumo["valor_recebido"]) == Decimal("335.00")


async def test_resumo_ignora_status_busca_e_paginacao(async_client: AsyncClient, db_session):
    await _cenario(db_session)

    res = await async_client.get(
        f"{API}/",
        params={"referencia_mes": "2026-11", "status": "PENDENTE", "q": "Caio", "page": 1, "page_size": 1},
    )

    assert res.status_code == 200
    corpo = res.json()
    assert [i["associado_nome"] for i in corpo["items"]] == ["Caio"]
    assert corpo["resumo"]["total"] == 4
    assert corpo["resumo"]["pagas"] == 2
    assert Decimal(corpo["resumo"]["valor_recebido"]) == Decimal("335.00")


async def test_resumo_respeita_associado_id(async_client: AsyncClient, db_session):
    ana = await _cenario(db_session)

    res = await async_client.get(f"{API}/", params={"associado_id": str(ana.id)})

    resumo = res.json()["resumo"]
    assert resumo["total"] == 2
    assert resumo["pagas"] == 1
    assert resumo["pendentes"] == 1
    assert Decimal(resumo["valor_total"]) == Decimal("1149.00")
    assert Decimal(resumo["valor_recebido"]) == Decimal("150.00")


async def test_resumo_sem_faturas_retorna_zeros(async_client: AsyncClient):
    res = await async_client.get(f"{API}/", params={"referencia_mes": "2030-01"})

    assert res.status_code == 200
    resumo = res.json()["resumo"]
    assert (resumo["total"], resumo["pagas"], resumo["pendentes"], resumo["atrasadas"]) == (0, 0, 0, 0)
    assert Decimal(resumo["valor_total"]) == Decimal("0")
    assert Decimal(resumo["valor_recebido"]) == Decimal("0")


async def test_itens_expoem_cpf_do_associado(async_client: AsyncClient, db_session):
    await _cenario(db_session)

    res = await async_client.get(f"{API}/", params={"referencia_mes": "2026-11", "q": "Ana"})

    [item] = res.json()["items"]
    assert item["associado_cpf"] == "000.000.001-00"
