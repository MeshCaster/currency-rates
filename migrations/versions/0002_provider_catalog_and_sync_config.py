import uuid
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDERS = [
    ("frankfurter", "Frankfurter", "fx", False),
    ("nbg", "National Bank of Georgia", "fx", False),
    ("exchangerate-api", "ExchangeRate-API", "fx", True),
    ("binance", "Binance", "crypto", False),
    ("coinbase", "Coinbase", "crypto", False),
    ("kraken", "Kraken", "crypto", False),
    ("coingecko", "CoinGecko", "crypto", False),
]

INTERVALS = [
    ("frankfurter", "daily", True, date(1999, 1, 4), None, None),
    ("frankfurter", "monthly", True, date(1999, 1, 4), None, None),
    ("nbg", "daily", True, date(1996, 1, 6), None, 1),
    ("nbg", "monthly", False, date(1996, 1, 6), None, 1),
    ("binance", "daily", True, None, None, 1000),
    ("binance", "monthly", True, None, None, 1000),
    ("coinbase", "daily", True, date(2023, 10, 1), None, 1),
    ("coinbase", "monthly", False, date(2023, 10, 1), None, 1),
    ("kraken", "daily", True, None, 720, 720),
    ("kraken", "monthly", False, None, 720, 720),
    ("coingecko", "daily", True, None, 365, None),
    ("coingecko", "monthly", False, None, 365, None),
]


def upgrade() -> None:
    op.create_table('currencies',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('code', sa.String(length=10), nullable=False),
    sa.Column('name', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.Enum('fiat', 'crypto', 'stablecoin', name='currencykind', native_enum=False, length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_currencies')),
    sa.UniqueConstraint('code', name=op.f('uq_currencies_code'))
    )
    op.create_table('providers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('key', sa.String(length=40), nullable=False),
    sa.Column('display_name', sa.String(length=64), nullable=False),
    sa.Column('kind', sa.Enum('fx', 'crypto', name='providerkind', native_enum=False, length=16), nullable=False),
    sa.Column('requires_api_key', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_providers')),
    sa.UniqueConstraint('key', name=op.f('uq_providers_key'))
    )
    op.create_table('provider_currencies',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider_id', sa.Uuid(), nullable=False),
    sa.Column('currency_code', sa.String(length=10), nullable=False),
    sa.Column('provider_code', sa.String(length=40), nullable=True),
    sa.Column('available_from', sa.Date(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['currency_code'], ['currencies.code'], name=op.f('fk_provider_currencies_currency_code_currencies'), onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name=op.f('fk_provider_currencies_provider_id_providers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_currencies')),
    sa.UniqueConstraint('provider_id', 'currency_code', name=op.f('uq_provider_currencies_provider_id'))
    )
    op.create_table('provider_intervals',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider_id', sa.Uuid(), nullable=False),
    sa.Column('interval', sa.Enum('daily', 'monthly', name='intervalkind', native_enum=False, length=16), nullable=False),
    sa.Column('is_native', sa.Boolean(), nullable=False),
    sa.Column('history_start', sa.Date(), nullable=True),
    sa.Column('history_window_days', sa.Integer(), nullable=True),
    sa.Column('max_points_per_request', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name=op.f('fk_provider_intervals_provider_id_providers'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_intervals')),
    sa.UniqueConstraint('provider_id', 'interval', name=op.f('uq_provider_intervals_provider_id'))
    )
    op.create_table('sync_configurations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('provider_id', sa.Uuid(), nullable=False),
    sa.Column('base', sa.String(length=10), nullable=False),
    sa.Column('quote', sa.String(length=10), nullable=False),
    sa.Column('interval', sa.Enum('daily', 'monthly', name='intervalkind', native_enum=False, length=16), nullable=False),
    sa.Column('date_from', sa.Date(), nullable=False),
    sa.Column('date_to', sa.Date(), nullable=True),
    sa.Column('synced_until', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_status', sa.Enum('succeeded', 'failed', name='syncstatus', native_enum=False, length=16), nullable=True),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('base <> quote', name=op.f('ck_sync_configurations_base_differs_from_quote')),
    sa.CheckConstraint('date_to IS NULL OR date_from <= date_to', name=op.f('ck_sync_configurations_date_range')),
    sa.ForeignKeyConstraint(['provider_id', 'base'], ['provider_currencies.provider_id', 'provider_currencies.currency_code'], name='fk_sync_configurations_base_provider_currencies'),
    sa.ForeignKeyConstraint(['provider_id', 'interval'], ['provider_intervals.provider_id', 'provider_intervals.interval'], name='fk_sync_configurations_interval_provider_intervals'),
    sa.ForeignKeyConstraint(['provider_id', 'quote'], ['provider_currencies.provider_id', 'provider_currencies.currency_code'], name='fk_sync_configurations_quote_provider_currencies'),
    sa.ForeignKeyConstraint(['provider_id'], ['providers.id'], name=op.f('fk_sync_configurations_provider_id_providers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sync_configurations')),
    sa.UniqueConstraint('provider_id', 'base', 'quote', 'interval', name='uq_sync_configurations_provider_pair_interval')
    )
    op.create_index('ix_sync_configurations_active', 'sync_configurations', ['synced_until'], unique=False, postgresql_where=sa.text('is_active'), sqlite_where=sa.text('is_active'))
    op.add_column('rates', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('rates', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))

    op.execute("UPDATE rates SET created_at = fetched_at, updated_at = fetched_at")
    _seed_providers()


def _seed_providers() -> None:
    providers = sa.table("providers", sa.column("id", sa.Uuid()), sa.column("key"),
                         sa.column("display_name"), sa.column("kind"),
                         sa.column("requires_api_key", sa.Boolean()))
    intervals = sa.table("provider_intervals", sa.column("id", sa.Uuid()),
                         sa.column("provider_id", sa.Uuid()), sa.column("interval"),
                         sa.column("is_native", sa.Boolean()), sa.column("history_start", sa.Date()),
                         sa.column("history_window_days", sa.Integer()),
                         sa.column("max_points_per_request", sa.Integer()))
    ids = {key: uuid.uuid7() for key, *_ in PROVIDERS}
    op.bulk_insert(providers, [
        {"id": ids[key], "key": key, "display_name": name, "kind": kind, "requires_api_key": api_key}
        for key, name, kind, api_key in PROVIDERS])
    op.bulk_insert(intervals, [
        {"id": uuid.uuid7(), "provider_id": ids[key], "interval": interval, "is_native": native,
         "history_start": start, "history_window_days": window, "max_points_per_request": page}
        for key, interval, native, start, window, page in INTERVALS])


def downgrade() -> None:
    op.drop_column('rates', 'updated_at')
    op.drop_column('rates', 'created_at')
    op.drop_index('ix_sync_configurations_active', table_name='sync_configurations', postgresql_where=sa.text('is_active'), sqlite_where=sa.text('is_active'))
    op.drop_table('sync_configurations')
    op.drop_table('provider_intervals')
    op.drop_table('provider_currencies')
    op.drop_table('providers')
    op.drop_table('currencies')
