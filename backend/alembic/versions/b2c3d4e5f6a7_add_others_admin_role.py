"""add OTHERS admin role (widen role column)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Column was sized to the longest member at the time ('KAM' -> varchar(3));
    # 'OTHERS' needs more room. native_enum=False means this is a plain
    # varchar, not a DB-level enum, so widening is just a length change.
    op.alter_column('admins', 'role', type_=sa.String(20))


def downgrade() -> None:
    op.alter_column('admins', 'role', type_=sa.String(3))
