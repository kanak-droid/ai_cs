"""add ticket and secure relay fields to calls

Revision ID: c53bf63b17ee
Revises: c42af52a06dd
Create Date: 2026-09-03 20:10:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

revision: str = "c53bf63b17ee"
down_revision: Union[str, None] = "c42af52a06dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Adds ticket correlation and opaque callback tokens without data loss."""
    op.add_column("calls", sa.Column("ticket_id", sa.Integer(), nullable=True))
    op.add_column(
        "calls",
        sa.Column(
            "triggered_by", sa.String(length=80), server_default="user_request", nullable=False
        ),
    )
    op.add_column("calls", sa.Column("relay_token", sa.String(length=128), nullable=True))
    op.create_foreign_key("fk_calls_ticket_id", "calls", "tickets", ["ticket_id"], ["id"])
    op.create_index("ix_calls_ticket_id", "calls", ["ticket_id"])
    op.create_index("ix_calls_relay_token", "calls", ["relay_token"], unique=True)


def downgrade() -> None:
    """Removes the additive ticket/relay fields while retaining existing calls."""
    op.drop_index("ix_calls_relay_token", table_name="calls")
    op.drop_index("ix_calls_ticket_id", table_name="calls")
    op.drop_constraint("fk_calls_ticket_id", "calls", type_="foreignkey")
    op.drop_column("calls", "relay_token")
    op.drop_column("calls", "triggered_by")
    op.drop_column("calls", "ticket_id")
