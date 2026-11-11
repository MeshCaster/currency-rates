from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('alert_rules',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('sync_configuration_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('window_minutes', sa.Integer(), nullable=False),
    sa.Column('direction', sa.Enum('up', 'down', 'both', name='pricedirection', native_enum=False, length=16), nullable=False),
    sa.Column('tiers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('window_minutes >= 1', name=op.f('ck_alert_rules_window_positive')),
    sa.ForeignKeyConstraint(['sync_configuration_id'], ['sync_configurations.id'], name=op.f('fk_alert_rules_sync_configuration_id_sync_configurations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_alert_rules'))
    )
    op.create_index('ix_alert_rules_sync_configuration_id', 'alert_rules', ['sync_configuration_id'], unique=False)
    op.create_table('price_samples',
    sa.Column('sync_configuration_id', sa.Uuid(), nullable=False),
    sa.Column('sampled_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('value', sa.Numeric(precision=38, scale=18), nullable=False),
    sa.ForeignKeyConstraint(['sync_configuration_id'], ['sync_configurations.id'], name=op.f('fk_price_samples_sync_configuration_id_sync_configurations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('sync_configuration_id', 'sampled_at', name=op.f('pk_price_samples'))
    )
    op.create_index('ix_price_samples_sampled_at', 'price_samples', ['sampled_at'], unique=False)
    op.create_table('alerts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('rule_id', sa.Uuid(), nullable=False),
    sa.Column('severity', sa.Enum('info', 'warning', 'critical', name='alertseverity', native_enum=False, length=16), nullable=False),
    sa.Column('status', sa.Enum('open', 'acknowledged', 'resolved', name='alertstatus', native_enum=False, length=16), nullable=False),
    sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('change_percent', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('peak_change_percent', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('reference_price', sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column('current_price', sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('acknowledged_by', sa.String(length=200), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'], name=op.f('fk_alerts_rule_id_alert_rules'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_alerts'))
    )
    op.create_index('ix_alerts_status_opened_at', 'alerts', ['status', 'opened_at'], unique=False)
    op.create_index('uq_alerts_rule_id_unresolved', 'alerts', ['rule_id'], unique=True, postgresql_where=sa.text("status <> 'resolved'"), sqlite_where=sa.text("status <> 'resolved'"))


def downgrade() -> None:
    op.drop_index('uq_alerts_rule_id_unresolved', table_name='alerts', postgresql_where=sa.text("status <> 'resolved'"), sqlite_where=sa.text("status <> 'resolved'"))
    op.drop_index('ix_alerts_status_opened_at', table_name='alerts')
    op.drop_table('alerts')
    op.drop_index('ix_price_samples_sampled_at', table_name='price_samples')
    op.drop_table('price_samples')
    op.drop_index('ix_alert_rules_sync_configuration_id', table_name='alert_rules')
    op.drop_table('alert_rules')
