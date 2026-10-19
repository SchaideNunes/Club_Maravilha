"""
Feature 4 - Disparo avulso de cobrança pelo painel ("Cobrar agora no WhatsApp").

Contrato:
- POST /api/v1/faturas/{fatura_id}/cobrar-whatsapp (sem corpo)
  implementado em `BillingEngineService.cobrar_fatura_agora(fatura_id, data_referencia=None)`
  (padrão: hoje_clube()), usando a fila global (`get_global_whatsapp_queue()`).
- Escolha do template pela situação da fatura na data de referência:
    vencimento >= hoje (no prazo)  -> template_d0      ("template": "D0")
    vencimento <  hoje (vencida)   -> template_d_mais_3 ("template": "D_MAIS_3")
  renderizado com variaveis_da_fatura (inclui {chave_pix}).
- Enfileira com LogContext(etapa=EtapaRegua.AVULSO, associado_id, fatura_id); vale mesmo com
  Configuracao.automacao_ativa == False (ação manual) e não é bloqueado por envios anteriores.
- 202 {"fatura_id", "etapa": "AVULSO", "template": "D0" | "D_MAIS_3", "destinatario", "mensagem"}
- 404 fatura inexistente; 409 fatura PAGO/CANCELADO; 422 associado sem WhatsApp. Nada é enfileirado nos erros.
"""
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.core.clock import hoje_clube
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.models.log_mensagem import EtapaRegua, LogMensagem, StatusEnvio
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.services import whatsapp_queue_service


class FilaFalsa:
    def __init__(self) -> None:
        self.itens = []

    async def enqueue(self, phone, message, priority=None, log_context=None) -> None:
        self.itens.append({"phone": phone, "message": message, "priority": priority, "log_context": log_context})


@pytest.fixture
def fila(monkeypatch) -> FilaFalsa:
    falsa = FilaFalsa()
    monkeypatch.setattr(whatsapp_queue_service, "_global_queue", falsa)
    return falsa


async def _cenario(db_session, dias_para_vencer: int, status=StatusFatura.PENDENTE, whatsapp="5575999991234",
                   automacao_ativa=True):
    cfg = await ConfiguracaoRepository(db_session).get_or_create()
    cfg.chave_pix = "pix@clube.com"
    cfg.automacao_ativa = automacao_ativa
    cfg.template_d0 = "NO PRAZO {nome} {valor_total} {vencimento} {chave_pix}"
    cfg.template_d_mais_3 = "VENCIDA {nome} {valor_total} {vencimento} {chave_pix}"
    socio = Associado(
        nome="Helena Avulsa",
        cpf="153.509.460-56",
        whatsapp=whatsapp,
        email="avulsa@clube.com",
        status=StatusAssociado.ATIVO,
    )
    db_session.add(socio)
    await db_session.commit()
    vencimento = hoje_clube() + timedelta(days=dias_para_vencer)
    fatura = Fatura(
        associado_id=socio.id,
        referencia_mes=vencimento.strftime("%Y-%m"),
        valor_base=Decimal("180.00"),
        valor_total=Decimal("180.00"),
        data_vencimento=vencimento,
        status=status,
    )
    db_session.add(fatura)
    await db_session.commit()
    return socio, fatura


def _url(fatura_id) -> str:
    return f"/api/v1/faturas/{fatura_id}/cobrar-whatsapp"


@pytest.mark.parametrize("dias", [0, 5])
async def test_fatura_no_prazo_usa_template_d0(async_client: AsyncClient, db_session, fila, dias):
    socio, fatura = await _cenario(db_session, dias_para_vencer=dias)

    res = await async_client.post(_url(fatura.id))

    assert res.status_code == 202
    venc = fatura.data_vencimento.strftime("%d/%m/%Y")
    esperado = f"NO PRAZO Helena Avulsa R$ 180,00 {venc} pix@clube.com"
    assert res.json() == {
        "fatura_id": str(fatura.id),
        "etapa": "AVULSO",
        "template": "D0",
        "destinatario": "5575999991234",
        "mensagem": esperado,
    }
    assert len(fila.itens) == 1
    item = fila.itens[0]
    assert item["message"] == esperado
    assert item["phone"] == socio.whatsapp
    ctx = item["log_context"]
    assert ctx.etapa == EtapaRegua.AVULSO
    assert ctx.associado_id == socio.id
    assert ctx.fatura_id == fatura.id


@pytest.mark.parametrize("status", [StatusFatura.PENDENTE, StatusFatura.ATRASADA])
async def test_fatura_vencida_usa_template_d_mais_3(async_client: AsyncClient, db_session, fila, status):
    _, fatura = await _cenario(db_session, dias_para_vencer=-2, status=status)

    res = await async_client.post(_url(fatura.id))

    assert res.status_code == 202
    assert res.json()["template"] == "D_MAIS_3"
    assert res.json()["mensagem"].startswith("VENCIDA Helena Avulsa R$ 180,00")
    assert fila.itens[0]["log_context"].etapa == EtapaRegua.AVULSO


async def test_avulso_ignora_automacao_desligada_e_envios_anteriores(async_client: AsyncClient, db_session, fila):
    socio, fatura = await _cenario(db_session, dias_para_vencer=0, automacao_ativa=False)
    db_session.add(LogMensagem(
        associado_id=socio.id, fatura_id=fatura.id, destinatario=socio.whatsapp,
        etapa=EtapaRegua.D0, mensagem="já enviado", status=StatusEnvio.SUCESSO,
    ))
    await db_session.commit()

    res = await async_client.post(_url(fatura.id))

    assert res.status_code == 202
    assert len(fila.itens) == 1


@pytest.mark.parametrize("status", [StatusFatura.PAGO, StatusFatura.CANCELADO])
async def test_fatura_paga_ou_cancelada_409(async_client: AsyncClient, db_session, fila, status):
    _, fatura = await _cenario(db_session, dias_para_vencer=0, status=status)

    res = await async_client.post(_url(fatura.id))

    assert res.status_code == 409
    assert fila.itens == []


async def test_fatura_inexistente_404(async_client: AsyncClient, fila):
    res = await async_client.post(_url(uuid.uuid4()))

    assert res.status_code == 404
    assert fila.itens == []


async def test_associado_sem_whatsapp_422(async_client: AsyncClient, db_session, fila):
    _, fatura = await _cenario(db_session, dias_para_vencer=0, whatsapp="")

    res = await async_client.post(_url(fatura.id))

    assert res.status_code == 422
    assert fila.itens == []
