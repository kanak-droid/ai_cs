"""add call outcome summary

Revision ID: d4e98b2291ad
Revises: c53bf63b17ee
Create Date: 2026-09-03 20:45:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "d4e98b2291ad"
down_revision: Union[str, None] = "c53bf63b17ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds nullable dashboard outcome fields without changing old calls."""
    op.add_column("calls", sa.Column("support_summary", sa.Text(), nullable=True))
    op.add_column("calls", sa.Column("resolution_status", sa.String(length=40), nullable=True))
    op.add_column("calls", sa.Column("suggested_solution", sa.Text(), nullable=True))
    op.add_column("calls", sa.Column("next_action", sa.Text(), nullable=True))
    op.add_column("calls", sa.Column("actions_taken", sa.JSON(), nullable=True))
    op.add_column("calls", sa.Column("summary_generated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Removes generated outcome fields; existing call rows remain intact."""
    op.drop_column("calls", "summary_generated_at")
    op.drop_column("calls", "actions_taken")
    op.drop_column("calls", "next_action")
    op.drop_column("calls", "suggested_solution")
    op.drop_column("calls", "resolution_status")
    op.drop_column("calls", "support_summary")
