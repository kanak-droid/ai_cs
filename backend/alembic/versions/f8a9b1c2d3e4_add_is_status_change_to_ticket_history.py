"""add is_status_change to ticket_status_history

Revision ID: f8a9b1c2d3e4
Revises: e7f8a9b1c2d3
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a9b1c2d3e4'
down_revision: Union[str, None] = 'e7f8a9b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ticket_status_history',
        sa.Column('is_status_change', sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column('ticket_status_history', 'is_status_change')
