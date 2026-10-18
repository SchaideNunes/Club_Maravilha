"""initial_schema_all_models

Revision ID: ffc02257a2fe
Revises:
Create Date: 2026-09-12 19:49:49.602911

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffc02257a2fe'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotente (if_not_exists): bancos criados por `Base.metadata.create_all` com os modelos
    # atuais já possuem estas colunas e não podem falhar ao percorrer o histórico desde a base.
    op.add_column('faturas', sa.Column('notificado_d_minus_3_em', sa.DateTime(timezone=True), nullable=True, comment='Data/hora do envio do aviso amigável D-3'), if_not_exists=True)
    op.add_column('faturas', sa.Column('notificado_d_zero_em', sa.DateTime(timezone=True), nullable=True, comment='Data/hora do envio matinal do Pix Copia e Cola no dia do vencimento D-0'), if_not_exists=True)
    op.add_column('faturas', sa.Column('notificado_d_plus_3_em', sa.DateTime(timezone=True), nullable=True, comment='Data/hora da notificação de atraso D+3'), if_not_exists=True)
    op.add_column('faturas', sa.Column('notificado_d_plus_7_em', sa.DateTime(timezone=True), nullable=True, comment='Data/hora do alerta de bloqueio e transição para inadimplente D+7'), if_not_exists=True)
    op.add_column('faturas', sa.Column('notificado_pos_pagamento_em', sa.DateTime(timezone=True), nullable=True, comment='Data/hora do envio de recibo e confirmação de catraca liberada'), if_not_exists=True)


def downgrade() -> None:
    op.drop_column('faturas', 'notificado_pos_pagamento_em')
    op.drop_column('faturas', 'notificado_d_plus_7_em')
    op.drop_column('faturas', 'notificado_d_plus_3_em')
    op.drop_column('faturas', 'notificado_d_zero_em')
    op.drop_column('faturas', 'notificado_d_minus_3_em')
