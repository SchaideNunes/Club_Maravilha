"""
Testes unitários para o motor da Régua Diária de Cobrança (D-3, D-0, D+3, D+7).
"""
import pytest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura
from app.services.billing_engine_service import BillingEngineService
from app.services.whatsapp_service import MockWhatsAppProvider
from app.services.whatsapp_queue_service import WhatsAppQueueService


@pytest.mark.asyncio
async def test_billing_engine_stages_and_idempotency(db_session: AsyncSession):
    mock_provider = MockWhatsAppProvider()
    queue_service = WhatsAppQueueService(
        provider=mock_provider,
        min_delay_seconds=0.0,
        max_delay_seconds=0.0,
    )
    engine = BillingEngineService(
        session=db_session,
        queue_service=queue_service
    )

    data_hoje = date(2026, 9, 10)

    # 1. Cria Associados
    socio_d3 = Associado(
        nome="Sócio D-3",
        cpf="111.111.111-11",
        whatsapp="+5511911110003",
        email="socio_d3@clube.com",
        status=StatusAssociado.ATIVO
    )
    socio_d0 = Associado(
        nome="Sócio D-0",
        cpf="222.222.222-22",
        whatsapp="+5511922220000",
        email="socio_d0@clube.com",
        status=StatusAssociado.ATIVO
    )
    socio_dp3 = Associado(
        nome="Sócio D+3",
        cpf="333.333.333-33",
        whatsapp="+5511933330003",
        email="socio_dp3@clube.com",
        status=StatusAssociado.ATIVO
    )
    socio_dp7 = Associado(
        nome="Sócio D+7",
        cpf="444.444.444-44",
        whatsapp="+5511944440007",
        email="socio_dp7@clube.com",
        status=StatusAssociado.ATIVO
    )
    db_session.add_all([socio_d3, socio_d0, socio_dp3, socio_dp7])
    await db_session.commit()

    # 2. Cria Faturas correspondentes
    fat_d3 = Fatura(
        associado_id=socio_d3.id,
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=data_hoje + timedelta(days=3),  # D-3
        status=StatusFatura.PENDENTE,
        pix_copia_cola="pix_d3"
    )
    fat_d0 = Fatura(
        associado_id=socio_d0.id,
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=data_hoje,  # D-0
        status=StatusFatura.PENDENTE,
        pix_copia_cola="pix_d0"
    )
    fat_dp3 = Fatura(
        associado_id=socio_dp3.id,
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=data_hoje - timedelta(days=3),  # D+3
        status=StatusFatura.PENDENTE,
        pix_copia_cola="pix_dp3"
    )
    fat_dp7 = Fatura(
        associado_id=socio_dp7.id,
        referencia_mes="2026-09",
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=data_hoje - timedelta(days=7),  # D+7
        status=StatusFatura.PENDENTE,
        pix_copia_cola="pix_dp7"
    )
    db_session.add_all([fat_d3, fat_d0, fat_dp3, fat_dp7])
    await db_session.commit()

    # 3. Executa a régua de cobrança
    report = await engine.processar_regua_diaria(data_referencia=data_hoje)

    assert report.d_minus_3_enviados == 1
    assert report.d_zero_enviados == 1
    assert report.d_plus_3_enviados == 1
    assert report.d_plus_7_enviados == 1
    assert report.inadimplentes_atualizados == 1
    assert report.total_enfileirados == 4

    # Processa mensagens na fila
    import asyncio
    worker_task = asyncio.create_task(queue_service.start_worker())
    await queue_service.join()
    await queue_service.stop_worker(worker_task)

    assert len(mock_provider.sent_messages) == 4

    # Verifica se os timestamps foram gravados nas faturas
    await db_session.refresh(fat_d3)
    await db_session.refresh(fat_d0)
    await db_session.refresh(fat_dp3)
    await db_session.refresh(fat_dp7)
    await db_session.refresh(socio_dp7)

    assert fat_d3.notificado_d_minus_3_em is not None
    assert fat_d0.notificado_d_zero_em is not None
    assert fat_dp3.notificado_d_plus_3_em is not None
    assert fat_dp7.notificado_d_plus_7_em is not None
    assert fat_dp7.status == StatusFatura.VENCIDO
    assert socio_dp7.status == StatusAssociado.INADIMPLENTE

    # 4. Teste de Idempotência: Executar novamente no mesmo dia não deve reenviar nada
    report_repetido = await engine.processar_regua_diaria(data_referencia=data_hoje)
    assert report_repetido.d_minus_3_enviados == 0
    assert report_repetido.d_zero_enviados == 0
    assert report_repetido.d_plus_3_enviados == 0
    assert report_repetido.d_plus_7_enviados == 0
    assert report_repetido.inadimplentes_atualizados == 0
    assert report_repetido.total_enfileirados == 0
