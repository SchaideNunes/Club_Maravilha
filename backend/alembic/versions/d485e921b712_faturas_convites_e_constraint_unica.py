"""faturas_convites_e_constraint_unica

Feature 3 do MVP:
- Adiciona colunas convites_usados e convites_extras na tabela faturas (int NOT NULL default 0);
- Adiciona UniqueConstraint uq_faturas_associado_referencia_mes em faturas (associado_id, referencia_mes).

Revision ID: d485e921b712
Revises: c2749453ba07
Create Date: 2026-10-19 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd485e921b712'
down_revision: Union[str, None] = 'c2749453ba07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UQ_FATURAS = 'uq_faturas_associado_referencia_mes'


def upgrade() -> None:
    op.add_column(
        'faturas',
        sa.Column(
            'convites_usados',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Quantidade total de convites utilizados no mês anterior',
        ),
    )
    op.add_column(
        'faturas',
        sa.Column(
            'convites_extras',
            sa.Integer(),
            nullable=False,
            server_default=sa.text('0'),
            comment='Quantidade de convites excedentes cobrados nesta fatura',
        ),
    )
    op.create_unique_constraint(
        UQ_FATURAS,
        'faturas',
        ['associado_id', 'referencia_mes'],
    )


def downgrade() -> None:
    op.drop_constraint(UQ_FATURAS, 'faturas', type_='unique')
    op.drop_column('faturas', 'convites_extras')
    op.drop_column('faturas', 'convites_usados')
