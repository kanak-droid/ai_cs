"""add access_level to admins

Revision ID: a1b2c3d4e5f6
Revises: f7ea76fd8032
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f7ea76fd8032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'admins',
        sa.Column(
            'access_level',
            sa.Enum('NORMAL', 'ADMIN', name='admin_access_level', native_enum=False),
            nullable=False,
            server_default='NORMAL',
        ),
    )
    op.alter_column('admins', 'access_level', server_default=None)


def downgrade() -> None:
    op.drop_column('admins', 'access_level')
