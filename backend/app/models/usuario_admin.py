"""
Modelo de dados para Usuário Administrador do Painel Admin.
"""
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UsuarioAdmin(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Representa um administrador com acesso ao painel de gestão do clube.
    """
    __tablename__ = "usuarios_admin"

    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<UsuarioAdmin id={self.id} nome='{self.nome}' email='{self.email}' ativo={self.ativo}>"
