"""mvp_configuracoes_logs_mensagens_dia_vencimento

Feature 1 do MVP (motor de WhatsApp Baileys + painel administrativo), para PostgreSQL:

- cria `configuracoes` (singleton, id = 1) e `logs_mensagens` (auditoria dos disparos);
- adiciona `associados.dia_vencimento` (1-31; os sócios existentes recebem o dia 10);
- `status_fatura_enum`: VENCIDO -> ATRASADA (RENAME VALUE preserva as faturas existentes);
- `forma_pagamento_enum`: CARTAO_CREDITO -> CARTAO (RENAME VALUE preserva os dados) e BOLETO
  deixa de existir no modelo: faturas BOLETO viram PIX. O rótulo BOLETO permanece, inerte,
  no tipo do Postgres, que não permite remover valores de um enum.

A migração é idempotente (IF NOT EXISTS e checagens no catálogo): o `create_all` do startup
da API pode ter criado as tabelas novas antes de ela rodar em ambientes de desenvolvimento.

Revision ID: c2749453ba07
Revises: ffc02257a2fe
Create Date: 2026-10-18 19:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c2749453ba07'
down_revision: Union[str, None] = 'ffc02257a2fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DIA_VENCIMENTO_EXISTENTES = 10
CHECK_DIA_VENCIMENTO = "ck_associados_dia_vencimento"

ETAPAS_REGUA = ("D_MENOS_3", "D0", "RECIBO", "D_MAIS_3", "D_MAIS_7", "AVULSO", "TESTE")
STATUS_ENVIO = ("SUCESSO", "ERRO")


def _criar_enum(nome: str, valores: Sequence[str]) -> None:
    """Cria o tipo ENUM do Postgres caso ainda não exista."""
    rotulos = ", ".join(f"'{valor}'" for valor in valores)
    op.execute(
        "DO $$ BEGIN "
        f"CREATE TYPE {nome} AS ENUM ({rotulos}); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )


def _renomear_valor_enum(tipo: str, de: str, para: str) -> None:
    """
    Renomeia um rótulo de ENUM no lugar (as linhas existentes acompanham a troca).
    Só age se `de` existir e `para` ainda não existir, o que torna o passo idempotente.
    """
    rotulo_existe = (
        "SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
        "WHERE t.typname = '{tipo}' AND e.enumlabel = '{rotulo}'"
    )
    op.execute(
        "DO $$ BEGIN "
        f"IF EXISTS ({rotulo_existe.format(tipo=tipo, rotulo=de)}) "
        f"AND NOT EXISTS ({rotulo_existe.format(tipo=tipo, rotulo=para)}) THEN "
        f"ALTER TYPE {tipo} RENAME VALUE '{de}' TO '{para}'; "
        "END IF; END $$;"
    )


def upgrade() -> None:
    # 1. Associados: dia de vencimento da mensalidade. O DEFAULT existe só para preencher
    #    os sócios atuais; depois é removido, pois o valor padrão vem da aplicação.
    op.add_column(
        'associados',
        sa.Column(
            'dia_vencimento',
            sa.Integer(),
            nullable=False,
            server_default=sa.text(str(DIA_VENCIMENTO_EXISTENTES)),
            comment='Dia do mês (1-31) em que a mensalidade do sócio vence',
        ),
        if_not_exists=True,
    )
    op.execute(f"ALTER TABLE associados DROP CONSTRAINT IF EXISTS {CHECK_DIA_VENCIMENTO}")
    op.create_check_constraint(
        CHECK_DIA_VENCIMENTO, 'associados', 'dia_vencimento >= 1 AND dia_vencimento <= 31'
    )
    op.alter_column('associados', 'dia_vencimento', server_default=None)

    # 2. Configurações do clube (singleton: id = 1)
    op.create_table(
        'configuracoes',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('valor_mensalidade', sa.Numeric(precision=10, scale=2), nullable=False, comment='Valor padrão da mensalidade'),
        sa.Column('franquia_convidados', sa.Integer(), nullable=False, comment='Quantidade de convites gratuitos por sócio a cada mês'),
        sa.Column('valor_convidado_extra', sa.Numeric(precision=10, scale=2), nullable=False, comment='Valor cobrado por convite que exceder a franquia mensal'),
        sa.Column('chave_pix', sa.String(length=150), nullable=True, comment='Chave Pix do clube informada nas mensagens de cobrança'),
        sa.Column('horario_disparo', sa.String(length=5), nullable=False, comment='Horário (HH:MM) do disparo diário da régua de cobrança'),
        sa.Column('automacao_ativa', sa.Boolean(), nullable=False, comment='Liga/desliga o disparo automático da régua de cobrança'),
        sa.Column('template_d_menos_3', sa.Text(), nullable=False),
        sa.Column('template_d0', sa.Text(), nullable=False),
        sa.Column('template_recibo', sa.Text(), nullable=False),
        sa.Column('template_d_mais_3', sa.Text(), nullable=False),
        sa.Column('template_d_mais_7', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('id = 1', name='ck_configuracoes_singleton'),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )

    # 3. Logs de mensagens de WhatsApp (auditoria e idempotência da régua)
    _criar_enum('etapa_regua_enum', ETAPAS_REGUA)
    _criar_enum('status_envio_enum', STATUS_ENVIO)
    op.create_table(
        'logs_mensagens',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('associado_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('fatura_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('destinatario', sa.String(length=20), nullable=False, comment='Número de destino no padrão Baileys (somente dígitos com DDI 55)'),
        sa.Column('etapa', postgresql.ENUM(*ETAPAS_REGUA, name='etapa_regua_enum', create_type=False), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False, comment='Texto final enviado, com as variáveis do template já substituídas'),
        sa.Column('status', postgresql.ENUM(*STATUS_ENVIO, name='status_envio_enum', create_type=False), nullable=False),
        sa.Column('erro', sa.Text(), nullable=True, comment='Detalhe da falha quando o status é ERRO'),
        sa.Column('enviado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['associado_id'], ['associados.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['fatura_id'], ['faturas.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        if_not_exists=True,
    )
    op.create_index(op.f('ix_logs_mensagens_id'), 'logs_mensagens', ['id'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_logs_mensagens_associado_id'), 'logs_mensagens', ['associado_id'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_logs_mensagens_enviado_em'), 'logs_mensagens', ['enviado_em'], unique=False, if_not_exists=True)
    op.create_index('idx_log_fatura_etapa', 'logs_mensagens', ['fatura_id', 'etapa'], unique=False, if_not_exists=True)

    # 4. Status da fatura: VENCIDO passa a se chamar ATRASADA
    _renomear_valor_enum('status_fatura_enum', 'VENCIDO', 'ATRASADA')

    # 5. Forma de pagamento: CARTAO_CREDITO -> CARTAO; BOLETO descontinuado (vira PIX)
    _renomear_valor_enum('forma_pagamento_enum', 'CARTAO_CREDITO', 'CARTAO')
    op.execute("UPDATE faturas SET forma_pagamento = 'PIX' WHERE CAST(forma_pagamento AS TEXT) = 'BOLETO'")


def downgrade() -> None:
    # 5. e 4. Restaura os rótulos anteriores (faturas BOLETO convertidas em PIX não são recuperáveis)
    _renomear_valor_enum('forma_pagamento_enum', 'CARTAO', 'CARTAO_CREDITO')
    _renomear_valor_enum('status_fatura_enum', 'ATRASADA', 'VENCIDO')

    # 3. Logs de mensagens
    op.drop_table('logs_mensagens', if_exists=True)
    op.execute("DROP TYPE IF EXISTS status_envio_enum")
    op.execute("DROP TYPE IF EXISTS etapa_regua_enum")

    # 2. Configurações do clube
    op.drop_table('configuracoes', if_exists=True)

    # 1. Associados (a coluna leva consigo a constraint CHECK)
    op.execute(f"ALTER TABLE associados DROP CONSTRAINT IF EXISTS {CHECK_DIA_VENCIMENTO}")
    op.drop_column('associados', 'dia_vencimento', if_exists=True)
