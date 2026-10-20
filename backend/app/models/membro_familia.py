"""
Modelo da tabela de Membros da Família (dependentes do sócio titular).
"""
import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.associado import Associado


class Parentesco(str, enum.Enum):
    CONJUGE = "CONJUGE"
    FILHO = "FILHO"
    ENTEADO = "ENTEADO"
    PAI_MAE = "PAI_MAE"
    IRMAO = "IRMAO"
    OUTRO = "OUTRO"


class MembroFamilia(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Dependente vinculado permanentemente ao titular, com entrada gratuita no clube e sem
    consumir a franquia mensal de convidados. A mesma pessoa pode ser dependente de dois
    titulares (ex: filho de pai e mãe sócios), mas não duas vezes na mesma família.
    """
    __tablename__ = "membros_familia"
    __table_args__ = (
        UniqueConstraint("associado_id", "cpf", name="uq_membros_familia_associado_cpf"),
    )

    associado_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("associados.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    parentesco: Mapped[Parentesco] = mapped_column(
        Enum(Parentesco, native_enum=False, length=20),
        nullable=False,
    )
    cpf: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)
    data_nascimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), nullable=False)

    associado: Mapped["Associado"] = relationship("Associado", back_populates="membros_familia")

    def __repr__(self) -> str:
        return f"<MembroFamilia(nome='{self.nome}', parentesco={self.parentesco.value})>"
