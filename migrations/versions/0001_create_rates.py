from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('rates',
    sa.Column('base', sa.String(length=10), nullable=False),
    sa.Column('quote', sa.String(length=10), nullable=False),
    sa.Column('source', sa.String(length=40), nullable=False),
    sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('value', sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column('kind', sa.String(length=16), server_default=sa.text("'observation'"), nullable=False),
    sa.PrimaryKeyConstraint('base', 'quote', 'source', 'observed_at', name=op.f('pk_rates'))
    )
    op.create_index('ix_rates_base_quote_kind_observed_at', 'rates', ['base', 'quote', 'kind', 'observed_at'], unique=False)
    op.create_index('ix_rates_base_quote_observed_at', 'rates', ['base', 'quote', 'observed_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_rates_base_quote_observed_at', table_name='rates')
    op.drop_index('ix_rates_base_quote_kind_observed_at', table_name='rates')
    op.drop_table('rates')
