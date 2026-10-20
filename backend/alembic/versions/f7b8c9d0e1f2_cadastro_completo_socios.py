"""cadastro_completo_socios

Cadastro de Sócios:
- Tabela `planos` (categorias de mensalidade) e vínculo opcional `associados.plano_id`.
- Ficha completa do associado: dados pessoais, endereço e dados de inativação.
- Tabela `membros_familia` (dependentes do titular).
- Novo status INATIVO em `status_associado_enum` (inativação substitui a exclusão).

Idempotente: a API cria as tabelas novas sozinha no startup (Base.metadata.create_all), então
cada passo só age se o objeto ainda não existir.

Revision ID: f7b8c9d0e1f2
Revises: e5a1b2c3d4e5
Create Date: 2026-10-20 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b8c9d0e1f2'
down_revision: Union[str, None] = 'e5a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FK_PLANO = "fk_associados_plano_id"


def _colunas_associado() -> list:
    return [
        sa.Column('data_nascimento', sa.Date(), nullable=True),
        sa.Column('rg', sa.String(length=20), nullable=True),
        sa.Column('sexo', sa.String(length=20), nullable=True),
        sa.Column('profissao', sa.String(length=100), nullable=True),
        sa.Column('cep', sa.String(length=9), nullable=True),
        sa.Column('logradouro', sa.String(length=150), nullable=True),
        sa.Column('numero', sa.String(length=10), nullable=True),
        sa.Column('complemento', sa.String(length=80), nullable=True),
        sa.Column('bairro', sa.String(length=80), nullable=True),
        sa.Column('cidade', sa.String(length=80), nullable=True),
        sa.Column('uf', sa.String(length=2), nullable=True),
        sa.Column('plano_id', sa.UUID(), nullable=True),
        sa.Column('data_inativacao', sa.Date(), nullable=True),
        sa.Column('motivo_inativacao', sa.String(length=255), nullable=True),
    ]


def _timestamps() -> list:
    return [
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tabelas = set(inspector.get_table_names())

    if bind.dialect.name == 'postgresql':
        # ADD VALUE não pode rodar dentro de um bloco de transação que depois use o valor novo
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE status_associado_enum ADD VALUE IF NOT EXISTS 'INATIVO'")

    if 'planos' not in tabelas:
        op.create_table(
            'planos',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('nome', sa.String(length=80), nullable=False),
            sa.Column('descricao', sa.Text(), nullable=True),
            sa.Column('valor_mensalidade', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('ativo', sa.Boolean(), server_default=sa.true(), nullable=False),
            *_timestamps(),
            sa.CheckConstraint('valor_mensalidade >= 0', name='ck_planos_valor_mensalidade'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('nome'),
        )
        op.create_index(op.f('ix_planos_id'), 'planos', ['id'], unique=False)

    colunas_existentes = {c['name'] for c in inspector.get_columns('associados')}
    for coluna in _colunas_associado():
        if coluna.name not in colunas_existentes:
            op.add_column('associados', coluna)

    indices = {i['name'] for i in inspector.get_indexes('associados')}
    if 'ix_associados_plano_id' not in indices:
        op.create_index(op.f('ix_associados_plano_id'), 'associados', ['plano_id'], unique=False)

    fks = {fk['name'] for fk in inspector.get_foreign_keys('associados')}
    if FK_PLANO not in fks and bind.dialect.name == 'postgresql':
        op.create_foreign_key(FK_PLANO, 'associados', 'planos', ['plano_id'], ['id'], ondelete='RESTRICT')

    if 'membros_familia' not in tabelas:
        op.create_table(
            'membros_familia',
            sa.Column('id', sa.UUID(), nullable=False),
            sa.Column('associado_id', sa.UUID(), nullable=False),
            sa.Column('nome', sa.String(length=150), nullable=False),
            sa.Column('parentesco', sa.String(length=20), nullable=False),
            sa.Column('cpf', sa.String(length=14), nullable=True),
            sa.Column('data_nascimento', sa.Date(), nullable=True),
            sa.Column('ativo', sa.Boolean(), server_default=sa.true(), nullable=False),
            *_timestamps(),
            sa.ForeignKeyConstraint(['associado_id'], ['associados.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('associado_id', 'cpf', name='uq_membros_familia_associado_cpf'),
        )
        op.create_index(op.f('ix_membros_familia_id'), 'membros_familia', ['id'], unique=False)
        op.create_index(op.f('ix_membros_familia_associado_id'), 'membros_familia', ['associado_id'], unique=False)


def downgrade() -> None:
    # O valor INATIVO do enum não é removido (PostgreSQL não suporta DROP VALUE); sócios inativos
    # precisam ser reativados manualmente antes de um downgrade.
    op.drop_index(op.f('ix_membros_familia_associado_id'), table_name='membros_familia')
    op.drop_index(op.f('ix_membros_familia_id'), table_name='membros_familia')
    op.drop_table('membros_familia')

    op.drop_constraint(FK_PLANO, 'associados', type_='foreignkey')
    op.drop_index(op.f('ix_associados_plano_id'), table_name='associados')
    for coluna in reversed(_colunas_associado()):
        op.drop_column('associados', coluna.name)

    op.drop_index(op.f('ix_planos_id'), table_name='planos')
    op.drop_table('planos')
