"""
Utilitários de segurança, hash de senhas e geração de tokens JWT.
Utiliza o pacote `bcrypt` diretamente para compatibilidade com bcrypt 5.x.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt

from app.core.config import settings


def hash_senha(senha: str) -> str:
    """
    Gera um hash bcrypt seguro com salt aleatório para a senha fornecida.
    """
    senha_bytes = senha.encode("utf-8")
    salt = bcrypt.gensalt()
    hash_bytes = bcrypt.hashpw(senha_bytes, salt)
    return hash_bytes.decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """
    Verifica se a senha em texto confere com o hash bcrypt fornecido.
    Tolerante a hashes vazios ou malformados, retornando False sem lançar exceção.
    """
    if not senha_hash or not isinstance(senha_hash, str):
        return False
    try:
        senha_bytes = senha.encode("utf-8")
        hash_bytes = senha_hash.encode("utf-8")
        return bcrypt.checkpw(senha_bytes, hash_bytes)
    except Exception:
        return False


def criar_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um token JWT HS256 com claims 'sub' e 'exp'.
    """
    agora = datetime.now(timezone.utc)
    if expires_delta is not None:
        expiracao = agora + expires_delta
    else:
        expiracao = agora + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims = {
        "sub": str(subject),
        "exp": expiracao,
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
