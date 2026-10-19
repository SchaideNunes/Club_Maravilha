"""
Serviço de negócio para a gestão de Configurações do clube e pré-visualização de templates.
"""
from decimal import Decimal
from typing import Optional
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.clock import hoje_clube
from app.models.configuracao import Configuracao
from app.models.fatura import Fatura
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.schemas.configuracao import ConfiguracaoUpdate
from app.services.template_service import (
    formatar_data_br,
    formatar_moeda_brl,
    renderizar_template,
    variaveis_da_fatura,
)


class ConfiguracaoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ConfiguracaoRepository(session)

    async def get_configuracao(self) -> Configuracao:
        """Retorna a configuração do clube (singleton), criando-a com os defaults quando inexistente."""
        return await self.repo.get_or_create()

    async def update_configuracao(self, dados: ConfiguracaoUpdate) -> Configuracao:
        """
        Atualiza parcialmente a configuração do clube.
        Quando o horário de disparo é alterado, reagenda a régua de cobrança após persistir.
        """
        config = await self.repo.get_or_create()
        campos = dados.model_dump(exclude_unset=True)

        horario_anterior = config.horario_disparo

        for chave, valor in campos.items():
            setattr(config, chave, valor)

        await self.session.commit()
        await self.session.refresh(config)

        if "horario_disparo" in campos and campos["horario_disparo"] != horario_anterior:
            from app.jobs import billing_scheduler
            billing_scheduler.reagendar_regua(config.horario_disparo)

        return config

    async def preview_template(
        self,
        template: str,
        fatura_id: Optional[uuid.UUID] = None,
    ) -> str:
        """
        Renderiza um template com variáveis reais da fatura ou dados de exemplo coerentes
        com as regras financeiras configuradas.
        """
        config = await self.repo.get_or_create()

        if fatura_id is not None:
            stmt = (
                select(Fatura)
                .options(joinedload(Fatura.associado))
                .where(Fatura.id == fatura_id)
            )
            fatura = (await self.session.execute(stmt)).scalar_one_or_none()
            if not fatura:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fatura {fatura_id} não encontrada.",
                )
            if not fatura.associado:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Associado da fatura não encontrado.",
                )
            variaveis = variaveis_da_fatura(fatura, fatura.associado, config)
        else:
            convites_usados = config.franquia_convidados + 2
            convites_extras = max(0, convites_usados - config.franquia_convidados)
            valor_base = config.valor_mensalidade
            valor_total = valor_base + (Decimal(convites_extras) * config.valor_convidado_extra)
            variaveis = {
                "nome": "Associado Exemplo",
                "valor_base": formatar_moeda_brl(valor_base),
                "convites_usados": str(convites_usados),
                "convites_extras": str(convites_extras),
                "valor_total": formatar_moeda_brl(valor_total),
                "vencimento": formatar_data_br(hoje_clube()),
                "chave_pix": config.chave_pix or "",
            }

        return renderizar_template(template, variaveis)
