"""add payout_cycle_info

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'payout_cycle_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('latest_cycle_tab', sa.String(120), nullable=False),
        sa.Column('latest_cycle_date', sa.Date(), nullable=False),
        sa.Column('next_payout_date', sa.Date(), nullable=False),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('payout_cycle_info')
