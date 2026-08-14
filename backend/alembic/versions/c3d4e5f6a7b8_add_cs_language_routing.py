"""add admin languages and ticket assigned_cs_id (CS language routing)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'admins',
        sa.Column(
            'languages',
            postgresql.ARRAY(sa.String(length=40)),
            nullable=False,
            server_default='{}',
        ),
    )
    op.alter_column('admins', 'languages', server_default=None)
    op.add_column('tickets', sa.Column('assigned_cs_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'tickets_assigned_cs_id_fkey', 'tickets', 'admins', ['assigned_cs_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint('tickets_assigned_cs_id_fkey', 'tickets', type_='foreignkey')
    op.drop_column('tickets', 'assigned_cs_id')
    op.drop_column('admins', 'languages')
