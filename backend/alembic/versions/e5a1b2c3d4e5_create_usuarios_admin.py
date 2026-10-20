"""create_usuarios_admin

Feature 5 do MVP:
- Criação da tabela usuarios_admin para autenticação do painel admin.

Revision ID: e5a1b2c3d4e5
Revises: d485e921b712
Create Date: 2026-10-19 06:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a1b2c3d4e5'
down_revision: Union[str, None] = 'd485e921b712'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'usuarios_admin' not in inspector.get_table_names():
        op.create_table(
            'usuarios_admin',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('nome', sa.String(length=255), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=False),
            sa.Column('senha_hash', sa.String(length=255), nullable=False),
            sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('email', name='uq_usuarios_admin_email'),
        )
        op.create_index(op.f('ix_usuarios_admin_email'), 'usuarios_admin', ['email'], unique=True)
        op.create_index(op.f('ix_usuarios_admin_id'), 'usuarios_admin', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_usuarios_admin_id'), table_name='usuarios_admin')
    op.drop_index(op.f('ix_usuarios_admin_email'), table_name='usuarios_admin')
    op.drop_table('usuarios_admin')
