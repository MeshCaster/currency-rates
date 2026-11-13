from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('provider_pairs',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider_id', sa.Uuid(), nullable=False),
    sa.Column('base', sa.String(length=10), nullable=False),
    sa.Column('quote', sa.String(length=10), nullable=False),
    sa.Column('symbol', sa.String(length=40), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('base <> quote', name=op.f('ck_provider_pairs_base_differs_from_quote')),
    sa.ForeignKeyConstraint(['base'], ['currencies.code'], name=op.f('fk_provider_pairs_base_currencies'), onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name=op.f('fk_provider_pairs_provider_id_providers'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['quote'], ['currencies.code'], name=op.f('fk_provider_pairs_quote_currencies'), onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_pairs')),
    sa.UniqueConstraint('provider_id', 'base', 'quote', name='uq_provider_pairs_provider_pair')
    )
    op.execute("""
        INSERT INTO provider_pairs (id, provider_id, base, quote)
        SELECT gen_random_uuid(), provider_id, base, quote
        FROM (SELECT DISTINCT provider_id, base, quote FROM sync_configurations) used
    """)

    op.drop_constraint(op.f('fk_sync_configurations_base_provider_currencies'), 'sync_configurations', type_='foreignkey')
    op.drop_constraint(op.f('fk_sync_configurations_quote_provider_currencies'), 'sync_configurations', type_='foreignkey')
    op.create_foreign_key('fk_sync_configurations_pair_provider_pairs', 'sync_configurations', 'provider_pairs', ['provider_id', 'base', 'quote'], ['provider_id', 'base', 'quote'])

    op.add_column('subscriptions', sa.Column('provider_pair_id', sa.Uuid(), nullable=True))
    op.execute("""
        UPDATE subscriptions s SET provider_pair_id = p.id
        FROM sync_configurations c
        JOIN provider_pairs p
          ON p.provider_id = c.provider_id AND p.base = c.base AND p.quote = c.quote
        WHERE c.id = s.sync_configuration_id
    """)
    op.execute("""
        DELETE FROM subscriptions s USING subscriptions older
        WHERE s.user_id = older.user_id AND s.provider_pair_id = older.provider_pair_id
          AND (older.created_at, older.id) < (s.created_at, s.id)
    """)
    op.alter_column('subscriptions', 'provider_pair_id', nullable=False)
    op.drop_index(op.f('ix_subscriptions_sync_configuration_id'), table_name='subscriptions')
    op.drop_constraint(op.f('uq_subscriptions_user_configuration'), 'subscriptions', type_='unique')
    op.drop_constraint(op.f('fk_subscriptions_sync_configuration_id_sync_configurations'), 'subscriptions', type_='foreignkey')
    op.drop_column('subscriptions', 'sync_configuration_id')
    op.create_index('ix_subscriptions_provider_pair_id', 'subscriptions', ['provider_pair_id'], unique=False)
    op.create_unique_constraint('uq_subscriptions_user_pair', 'subscriptions', ['user_id', 'provider_pair_id'])
    op.create_foreign_key(op.f('fk_subscriptions_provider_pair_id_provider_pairs'), 'subscriptions', 'provider_pairs', ['provider_pair_id'], ['id'])

    op.drop_table('provider_currencies')


def downgrade() -> None:
    op.create_table('provider_currencies',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('provider_id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('currency_code', sa.VARCHAR(length=10), autoincrement=False, nullable=False),
    sa.Column('provider_code', sa.VARCHAR(length=40), autoincrement=False, nullable=True),
    sa.Column('available_from', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['currency_code'], ['currencies.code'], name=op.f('fk_provider_currencies_currency_code_currencies'), onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name=op.f('fk_provider_currencies_provider_id_providers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_currencies')),
    sa.UniqueConstraint('provider_id', 'currency_code', name=op.f('uq_provider_currencies_provider_id'))
    )
    op.execute("""
        INSERT INTO provider_currencies (id, provider_id, currency_code)
        SELECT gen_random_uuid(), provider_id, code
        FROM (SELECT provider_id, base AS code FROM provider_pairs
              UNION SELECT provider_id, quote FROM provider_pairs) legs
    """)

    op.add_column('subscriptions', sa.Column('sync_configuration_id', sa.UUID(), autoincrement=False, nullable=True))
    op.execute("""
        UPDATE subscriptions s SET sync_configuration_id = (
            SELECT c.id FROM sync_configurations c JOIN provider_pairs p
              ON p.provider_id = c.provider_id AND p.base = c.base AND p.quote = c.quote
            WHERE p.id = s.provider_pair_id
            ORDER BY (c.interval = 'daily') DESC, c.is_active DESC, c.created_at
            LIMIT 1)
    """)
    op.execute("DELETE FROM subscriptions WHERE sync_configuration_id IS NULL")
    op.alter_column('subscriptions', 'sync_configuration_id', nullable=False)
    op.drop_constraint(op.f('fk_subscriptions_provider_pair_id_provider_pairs'), 'subscriptions', type_='foreignkey')
    op.drop_constraint('uq_subscriptions_user_pair', 'subscriptions', type_='unique')
    op.drop_index('ix_subscriptions_provider_pair_id', table_name='subscriptions')
    op.drop_column('subscriptions', 'provider_pair_id')
    op.create_foreign_key(op.f('fk_subscriptions_sync_configuration_id_sync_configurations'), 'subscriptions', 'sync_configurations', ['sync_configuration_id'], ['id'], ondelete='CASCADE')
    op.create_unique_constraint(op.f('uq_subscriptions_user_configuration'), 'subscriptions', ['user_id', 'sync_configuration_id'])
    op.create_index(op.f('ix_subscriptions_sync_configuration_id'), 'subscriptions', ['sync_configuration_id'], unique=False)

    op.drop_constraint('fk_sync_configurations_pair_provider_pairs', 'sync_configurations', type_='foreignkey')
    op.create_foreign_key(op.f('fk_sync_configurations_quote_provider_currencies'), 'sync_configurations', 'provider_currencies', ['provider_id', 'quote'], ['provider_id', 'currency_code'])
    op.create_foreign_key(op.f('fk_sync_configurations_base_provider_currencies'), 'sync_configurations', 'provider_currencies', ['provider_id', 'base'], ['provider_id', 'currency_code'])
    op.drop_table('provider_pairs')
