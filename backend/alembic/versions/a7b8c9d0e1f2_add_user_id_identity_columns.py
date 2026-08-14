"""add user_id to astrologers and expert_priority (real token identity)

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('astrologers', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_astrologers_user_id'), 'astrologers', ['user_id'], unique=True)
    op.add_column('expert_priority', sa.Column('user_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('expert_priority', 'user_id')
    op.drop_index(op.f('ix_astrologers_user_id'), table_name='astrologers')
    op.drop_column('astrologers', 'user_id')
