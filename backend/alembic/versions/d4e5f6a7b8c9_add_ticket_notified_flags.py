"""add kam_notified/cs_notified to tickets

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfilled true for existing rows — preserves current dashboard
    # visibility for tickets created before this flag existed; only new
    # tickets get the refined "were they actually notified" gating (see
    # ticket_service.create_ticket). scripts/backfill_ticket_notified.py
    # recomputes these for real from current data if you want existing
    # tickets to reflect the new logic too.
    op.add_column('tickets', sa.Column('kam_notified', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('tickets', sa.Column('cs_notified', sa.Boolean(), nullable=False, server_default='true'))
    op.alter_column('tickets', 'kam_notified', server_default=None)
    op.alter_column('tickets', 'cs_notified', server_default=None)


def downgrade() -> None:
    op.drop_column('tickets', 'cs_notified')
    op.drop_column('tickets', 'kam_notified')
