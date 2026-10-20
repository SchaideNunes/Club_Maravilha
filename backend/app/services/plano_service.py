"""
Camada de serviço dos Planos de mensalidade.
"""
from typing import List, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.plano import Plano
from app.repositories.plano_repository import PlanoRepository
from app.schemas.plano import PlanoCreate, PlanoResponse, PlanoUpdate


class PlanoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = PlanoRepository(session)

    async def _get_or_404(self, plano_id: uuid.UUID) -> Plano:
        plano = await self.repository.get_by_id(plano_id)
        if not plano:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado.")
        return plano

    async def _garantir_nome_livre(self, nome: str, plano_id: Optional[uuid.UUID] = None) -> None:
        existente = await self.repository.get_by_nome(nome)
        if existente and existente.id != plano_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Já existe um plano chamado '{existente.nome}'.",
            )

    async def _responder(self, planos: List[Plano]) -> List[PlanoResponse]:
        totais = await self.repository.contar_associados([p.id for p in planos])
        return [
            PlanoResponse.model_validate(plano).model_copy(update={"total_associados": totais.get(plano.id, 0)})
            for plano in planos
        ]

    async def listar(self, ativo: Optional[bool] = None) -> List[PlanoResponse]:
        return await self._responder(await self.repository.list(ativo=ativo))

    async def criar(self, data: PlanoCreate) -> PlanoResponse:
        await self._garantir_nome_livre(data.nome)
        plano = await self.repository.create(**data.model_dump())
        await self.session.commit()
        return (await self._responder([plano]))[0]

    async def atualizar(self, plano_id: uuid.UUID, data: PlanoUpdate) -> PlanoResponse:
        plano = await self._get_or_404(plano_id)
        campos = data.model_dump(exclude_unset=True)
        if "nome" in campos:
            await self._garantir_nome_livre(campos["nome"], plano_id)
        plano = await self.repository.update(plano, campos)
        await self.session.commit()
        return (await self._responder([plano]))[0]

    async def excluir(self, plano_id: uuid.UUID) -> None:
        """Só exclui planos nunca usados; os demais devem ser desativados para preservar o histórico."""
        plano = await self._get_or_404(plano_id)
        if await self.repository.possui_associados(plano_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este plano está vinculado a associados. Desative-o em vez de excluir.",
            )
        await self.repository.delete(plano)
        await self.session.commit()
