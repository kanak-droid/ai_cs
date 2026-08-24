"""add ticket resolution rating columns

Revision ID: b4c5d6e7f8a9
Revises: a1b2c3d4e5f7
Create Date: 2026-08-20 00:00:00.000001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('rating', sa.Integer(), nullable=True))
    op.add_column('tickets', sa.Column('rating_reasons', sa.JSON(), nullable=True))
    op.add_column('tickets', sa.Column('rating_comment', sa.Text(), nullable=True))
    op.add_column('tickets', sa.Column('rated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('tickets', 'rated_at')
    op.drop_column('tickets', 'rating_comment')
    op.drop_column('tickets', 'rating_reasons')
    op.drop_column('tickets', 'rating')
