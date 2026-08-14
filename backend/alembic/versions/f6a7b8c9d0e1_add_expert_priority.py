"""add expert_priority (analytics-query-sourced priority ranking)

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'expert_priority',
        sa.Column('expert_id', sa.Integer(), nullable=False),
        sa.Column('expert_name', sa.String(length=120), nullable=True),
        sa.Column('current_priority_tier', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('expert_id'),
    )


def downgrade() -> None:
    op.drop_table('expert_priority')
