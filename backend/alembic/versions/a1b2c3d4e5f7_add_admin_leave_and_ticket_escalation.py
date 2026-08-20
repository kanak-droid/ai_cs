"""add admin on-leave flag and ticket escalation columns

Revision ID: a1b2c3d4e5f7
Revises: f7a8b9c0d1e2
Create Date: 2026-08-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'admins',
        sa.Column('is_temporarily_inactive', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'tickets',
        sa.Column('escalated_to_kam', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('tickets', sa.Column('escalated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('tickets', 'escalated_at')
    op.drop_column('tickets', 'escalated_to_kam')
    op.drop_column('admins', 'is_temporarily_inactive')
