"""
Modelo da tabela de Planos (categorias de mensalidade dos sócios).
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, Numeric, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Plano(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Categoria de mensalidade (ex: Individual, Familiar, Remido).
    O valor do plano substitui Configuracao.valor_mensalidade na geração das faturas do sócio;
    valor 0 representa sócio isento. Planos desativados deixam de ser oferecidos em novos
    cadastros, mas continuam valendo para quem já está neles.
    """
    __tablename__ = "planos"
    __table_args__ = (
        CheckConstraint("valor_mensalidade >= 0", name="ck_planos_valor_mensalidade"),
    )

    nome: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    valor_mensalidade: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    def __repr__(self) -> str:
        return f"<Plano(nome='{self.nome}', valor={self.valor_mensalidade}, ativo={self.ativo})>"
