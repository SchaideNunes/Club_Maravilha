"""
Seed idempotente do administrador inicial do sistema.
Pode ser executado via CLI (python -m scripts.seed_admin) ou invocado na subida da API.
"""
import asyncio
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_senha
from app.models.usuario_admin import UsuarioAdmin


async def seed_admin(
    session: AsyncSession,
    email: str,
    senha: str,
    nome: str = "Administrador",
) -> Tuple[UsuarioAdmin, bool]:
    """
    Cria ou recupera o administrador inicial de forma idempotente.
    Retorna (usuario, criado).
    """
    if not senha or not senha.strip():
        raise ValueError("Senha não pode ser vazia.")

    email_normalizado = email.strip().lower()
    nome_limpo = nome.strip() if nome else "Administrador"

    query = select(UsuarioAdmin).where(UsuarioAdmin.email == email_normalizado)
    resultado = await session.execute(query)
    existente = resultado.scalar_one_or_none()

    if existente is not None:
        return existente, False

    novo_admin = UsuarioAdmin(
        nome=nome_limpo,
        email=email_normalizado,
        senha_hash=hash_senha(senha),
        ativo=True,
    )
    session.add(novo_admin)
    await session.commit()
    await session.refresh(novo_admin)
    return novo_admin, True


async def seed_admin_from_env(session: AsyncSession) -> Optional[UsuarioAdmin]:
    """
    Executa o seed com as credenciais configuradas nas variáveis de ambiente.
    Retorna None se ADMIN_EMAIL ou ADMIN_PASSWORD não estiverem definidos.
    """
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        return None

    usuario, _ = await seed_admin(
        session=session,
        email=settings.ADMIN_EMAIL,
        senha=settings.ADMIN_PASSWORD,
        nome=settings.ADMIN_NOME,
    )
    return usuario


def main() -> None:
    """Execução via CLI."""
    async def _executar() -> None:
        async with AsyncSessionLocal() as session:
            usuario = await seed_admin_from_env(session)
            if usuario:
                print(f"[seed_admin] Administrador pronto: {usuario.email}")
            else:
                print("[seed_admin] ADMIN_EMAIL ou ADMIN_PASSWORD não configurados; nenhum admin criado.")

    asyncio.run(_executar())


if __name__ == "__main__":
    main()
