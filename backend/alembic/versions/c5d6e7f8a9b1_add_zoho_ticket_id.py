"""add zoho_ticket_id to tickets

Revision ID: c5d6e7f8a9b1
Revises: b4c5d6e7f8a9
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b1'
down_revision: Union[str, None] = 'b4c5d6e7f8a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('zoho_ticket_id', sa.String(length=64), nullable=True))
    op.create_index('ix_tickets_zoho_ticket_id', 'tickets', ['zoho_ticket_id'])


def downgrade() -> None:
    op.drop_index('ix_tickets_zoho_ticket_id', table_name='tickets')
    op.drop_column('tickets', 'zoho_ticket_id')
