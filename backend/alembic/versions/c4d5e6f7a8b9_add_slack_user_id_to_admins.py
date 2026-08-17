"""add slack_user_id to admins

Revision ID: c4d5e6f7a8b9
Revises: a7b8c9d0e1f2
Create Date: 2026-08-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('admins', sa.Column('slack_user_id', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('admins', 'slack_user_id')
