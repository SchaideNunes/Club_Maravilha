"""
Serviço de Negócio para Gestão de Convidados, Cota Mensal e Validação de QR Code na Catraca.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.associado import StatusAssociado
from app.models.convidado import Convidado, StatusConvidado
from app.models.fatura import StatusFatura
from app.repositories.associado_repository import AssociadoRepository
from app.repositories.configuracao_repository import ConfiguracaoRepository
from app.repositories.convidado_repository import ConvidadoRepository
from app.repositories.fatura_repository import FaturaRepository
from app.schemas.convidado import (
    AdicionarConvidadoResponse,
    ConvidadoAssociadoCreate,
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
        self.configuracao_repo = ConfiguracaoRepository(session)

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
        Emite um convite para visitante com QR Code temporário e controle da cota mensal
        lida dinamicamente da Configuracao do clube:
        - Até a franquia no mês: GRATUITO (R$ 0,00).
        - Acima da franquia: EXCEDENTE (valor_convidado_extra).
        """
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

        faturas_vencidas = await self.fatura_repo.list_faturas(
            associado_id=data.associado_titular_id,
            status=StatusFatura.ATRASADA
        )
        if faturas_vencidas:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Emissão bloqueada: associado possui mensalidade vencida em aberto."
            )

        ano = data.data_visita.year
        mes = data.data_visita.month
        emitidos_no_mes = await self.convidado_repo.contar_convites_no_mes(
            associado_id=data.associado_titular_id,
            ano=ano,
            mes=mes
        )

        cfg = await self.configuracao_repo.get_or_create()
        franquia = cfg.franquia_convidados
        valor_extra = cfg.valor_convidado_extra

        if emitidos_no_mes < franquia:
            is_gratuito = True
            valor_cobrado = Decimal("0.00")
        else:
            is_gratuito = False
            valor_cobrado = valor_extra

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

    async def adicionar_convidado_associado(
        self,
        associado_id: uuid.UUID,
        data: ConvidadoAssociadoCreate
    ) -> AdicionarConvidadoResponse:
        """
        Emissão rápida de convite pelo ID do associado titular:
        - data_visita omitida => date.today()
        - Respeita franquia_convidados e valor_convidado_extra da Configuracao
        - Associado inexistente => 404, BLOQUEADO => 403
        """
        associado = await self.associado_repo.get_by_id(associado_id)
        if not associado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associado não encontrado."
            )

        if associado.status == StatusAssociado.BLOQUEADO:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Associado bloqueado não pode emitir convites."
            )

        data_visita = data.data_visita or date.today()
        ano = data_visita.year
        mes = data_visita.month

        emitidos_no_mes = await self.convidado_repo.contar_convites_no_mes(
            associado_id=associado_id,
            ano=ano,
            mes=mes
        )

        cfg = await self.configuracao_repo.get_or_create()
        franquia = cfg.franquia_convidados
        valor_extra = cfg.valor_convidado_extra

        is_gratuito = emitidos_no_mes < franquia
        tipo = "GRATUITO" if is_gratuito else "EXCEDENTE"
        valor_cobrado = Decimal("0.00") if is_gratuito else valor_extra

        if is_gratuito:
            aviso = None
        else:
            valor_fmt = f"R$ {valor_extra:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            aviso = f"Franquia mensal de convidados ({franquia}) atingida. Este convite excedente terá cobrança de {valor_fmt}."

        convidado = Convidado(
            associado_titular_id=associado_id,
            nome=data.nome,
            cpf=data.cpf,
            data_visita=data_visita,
            status=StatusConvidado.EMITIDO,
            is_gratuito=is_gratuito,
            valor_cobrado=valor_cobrado
        )

        created = await self.convidado_repo.create(convidado)
        await self.session.commit()
        await self.session.refresh(created)

        usados = emitidos_no_mes + 1
        excedentes = max(0, usados - franquia)

        return AdicionarConvidadoResponse(
            convidado=ConvidadoResponse.model_validate(created),
            is_gratuito=is_gratuito,
            tipo=tipo,
            convidados_usados_mes=usados,
            franquia=franquia,
            excedentes_mes=excedentes,
            valor_taxa_extra=valor_extra,
            aviso=aviso
        )

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
        cfg = await self.configuracao_repo.get_or_create()
        franquia = cfg.franquia_convidados
        valor_extra = cfg.valor_convidado_extra

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
            valor_unitario_excedente=valor_extra
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
