import asyncio
import secrets
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.core.rate_limit import login_rate_limiter
from app.core.security import criar_access_token, hash_senha, verificar_senha
from app.models.usuario_admin import UsuarioAdmin

router = APIRouter()

# Hash fictício pré-computado para mitigar enumeração de contas por tempo (timing attacks)
_DUMMY_HASH = hash_senha(secrets.token_hex(32))


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    senha: str = Field(..., max_length=128)


class UsuarioResponse(BaseModel):
    id: str
    nome: str
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Autenticação do administrador com e-mail e senha.
    Aplica rate limiting de 5 falhas a cada 60 segundos por IP + e-mail.
    """
    client_ip = request.client.host if request.client else "unknown"
    email_normalizado = payload.email.strip().lower()
    chave_rate_limit = f"{client_ip}|{email_normalizado}"

    if login_rate_limiter.bloqueado(chave_rate_limit):
        segundos = login_rate_limiter.segundos_para_liberar(chave_rate_limit)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login incorretas. Aguarde antes de tentar novamente.",
            headers={"Retry-After": str(segundos)},
        )

    query = select(UsuarioAdmin).where(UsuarioAdmin.email == email_normalizado)
    resultado = await db.execute(query)
    usuario = resultado.scalar_one_or_none()

    # Sempre executa a verificação criptográfica via thread pool para mitigar timing attack e não travar o loop
    senha_hash_para_verificar = usuario.senha_hash if usuario else _DUMMY_HASH
    senha_valida = await asyncio.to_thread(
        verificar_senha, payload.senha, senha_hash_para_verificar
    )

    if usuario is None or not senha_valida or not usuario.ativo:
        login_rate_limiter.registrar_falha(chave_rate_limit)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_rate_limiter.limpar(chave_rate_limit)
    token = criar_access_token(str(usuario.id))

    return {
        "access_token": token,
        "token_type": "bearer",
        "usuario": {
            "id": str(usuario.id),
            "nome": usuario.nome,
            "email": usuario.email,
        },
    }


@router.get("/me", response_model=UsuarioResponse)
async def me(
    admin: UsuarioAdmin = Depends(get_current_admin),
) -> Dict[str, Any]:
    """
    Retorna os dados do administrador atualmente autenticado.
    """
    return {
        "id": str(admin.id),
        "nome": admin.nome,
        "email": admin.email,
    }
