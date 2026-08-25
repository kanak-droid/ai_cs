"""add feedback_reasons to chat_sessions

Revision ID: e7f8a9b1c2d3
Revises: d6e7f8a9b1c2
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b1c2d3'
down_revision: Union[str, None] = 'd6e7f8a9b1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chat_sessions', sa.Column('feedback_reasons', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('chat_sessions', 'feedback_reasons')
