"""
Serviço de Negócio para Gestão de Convidados, Cota Mensal de 8 e Validação de QR Code na Catraca.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.associado import StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.convidado_repository import ConvidadoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.schemas.convidado import (
    ConvidadoCreate,
    ConvidadoResponse,
    ConvidadoValidateQRResponse,
    QuotaConvidadosResponse,
)


class ConvidadoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.convidado_repo = ConvidadoRepository(session)
        self.associado_repo = AssociadoRepository(session)
        self.fatura_repo = FaturaRepository(session)

    async def get_by_id(self, convidado_id: uuid.UUID) -> Convidado:
        convidado = await self.convidado_repo.get_by_id(convidado_id)
        if not convidado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Convite não encontrado."
            )
        return convidado

    async def list_convidados(
        self,
        associado_id: Optional[uuid.UUID] = None,
        data_visita: Optional[date] = None,
        status_filter: Optional[StatusConvidado] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Convidado]:
        return await self.convidado_repo.list_convidados(
            associado_id=associado_id,
            data_visita=data_visita,
            status=status_filter,
            skip=skip,
            limit=limit
        )

    async def emitir_convite(self, data: ConvidadoCreate) -> Convidado:
        """
        Emite um convite para visitante com QR Code temporário e controle da cota mensal:
        - Até 8 convites no mês: GRATUITO (R$ 0,00).
        - A partir do 9º no mês: EXCEDENTE (R$ 35,00 faturados no próximo ciclo).
        """
        # 1. Validação do Sócio Titular
        associado = await self.associado_repo.get_by_id(data.associado_titular_id)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado titular não encontrado."
            )
        if associado.status != StatusAssociado.ATIVO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Associado não pode emitir convites. Status cadastral: {associado.status}."
            )

        # 2. Validação contra Inadimplência
        faturas_vencidas = await self.fatura_repo.list_faturas(
            associado_id=data.associado_titular_id,
            status=StatusFatura.VENCIDO
        )
        if faturas_vencidas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Emissão bloqueada: associado possui mensalidade vencida em aberto."
            )

        # 3. Cálculo da Franquia no Mês da Visita (Reset no dia 1º de cada mês)
        ano = data.data_visita.year
        mes = data.data_visita.month
        emitidos_no_mes = await self.convidado_repo.contar_convites_no_mes(
            associado_id=data.associado_titular_id,
            ano=ano,
            mes=mes
        )

        franquia = settings.FRANQUIA_CONVITES_MENSAL
        if emitidos_no_mes < franquia:
            is_gratuito = True
            valor_cobrado = Decimal("0.00")
        else:
            is_gratuito = False
            valor_cobrado = Decimal(str(settings.VALOR_CONVITE_EXCEDENTE))

        convidado = Convidado(
            associado_titular_id=data.associado_titular_id,
            nome=data.nome,
            cpf=data.cpf,
            data_visita=data.data_visita,
            status=StatusConvidado.EMITIDO,
            is_gratuito=is_gratuito,
            valor_cobrado=valor_cobrado
        )

        created = await self.convidado_repo.create(convidado)
        await self.session.commit()
        await self.session.refresh(created)
        return created

    async def consultar_cota(
        self,
        associado_id: uuid.UUID,
        ano: int,
        mes: int
    ) -> QuotaConvidadosResponse:
        """Retorna o balanço de convites gratuitos e excedentes do sócio no mês informado."""
        emitidos = await self.convidado_repo.contar_convites_no_mes(
            associado_id=associado_id,
            ano=ano,
            mes=mes
        )
        franquia = settings.FRANQUIA_CONVITES_MENSAL
        utilizados = min(emitidos, franquia)
        restantes = max(0, franquia - emitidos)
        excedentes = max(0, emitidos - franquia)

        mes_str = f"{ano:04d}-{mes:02d}"
        return QuotaConvidadosResponse(
            associado_id=associado_id,
            mes_referencia=mes_str,
            franquia_total=franquia,
            utilizados=utilizados,
            restantes=restantes,
            excedentes_emitidos=excedentes,
            valor_unitario_excedente=Decimal(str(settings.VALOR_CONVITE_EXCEDENTE))
        )

    async def validar_qr_catraca(
        self,
        token: str,
        data_leitura: Optional[date] = None
    ) -> ConvidadoValidateQRResponse:
        """
        Valida a leitura ótica do QR Code na catraca de visitantes.
        Regra estrita: O convidado só pode acessar as dependências no dia marcado.
        """
        convidado = await self.convidado_repo.get_by_token(token)
        if not convidado:
            return ConvidadoValidateQRResponse(
                valido=False,
                mensagem="QR Code de visitante inválido ou não encontrado."
            )

        if convidado.status == StatusConvidado.UTILIZADO:
            return ConvidadoValidateQRResponse(
                valido=False,
                mensagem="QR Code já utilizado anteriormente na catraca."
            )

        if convidado.status == StatusConvidado.CANCELADO:
            return ConvidadoValidateQRResponse(
                valido=False,
                mensagem="Este convite foi cancelado pelo sócio titular."
            )

        hoje = data_leitura or date.today()
        if convidado.data_visita != hoje:
            data_str = convidado.data_visita.strftime("%d/%m/%Y")
            return ConvidadoValidateQRResponse(
                valido=False,
                mensagem=f"Acesso não permitido: o convite é válido apenas para o dia {data_str}."
            )

        # Registra o acesso do visitante
        convidado.status = StatusConvidado.UTILIZADO
        convidado.check_in_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(convidado)

        return ConvidadoValidateQRResponse(
            valido=True,
            mensagem="Acesso liberado na catraca! Bem-vindo ao Club Maravilha.",
            convidado=ConvidadoResponse.model_validate(convidado)
        )

    async def cancelar_convite(self, convidado_id: uuid.UUID) -> Convidado:
        """Cancela um convite emitido que ainda não tenha sido bipado na catraca."""
        convidado = await self.get_by_id(convidado_id)
        if convidado.status == StatusConvidado.UTILIZADO:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível cancelar um convite que já foi utilizado na catraca."
            )
        convidado.status = StatusConvidado.CANCELADO
        await self.session.commit()
        await self.session.refresh(convidado)
        return convidado
