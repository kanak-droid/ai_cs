"""switch to real KYC/Payout sheets: add TDS/KYC columns to payout status, drop wallet_balance table

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sheet_payout_status', sa.Column('kyc_status', sa.String(length=20), nullable=True))
    op.add_column(
        'sheet_payout_status', sa.Column('tds_deducted_percent', sa.String(length=20), nullable=True)
    )
    op.add_column('sheet_payout_status', sa.Column('tds_amount', sa.BigInteger(), nullable=True))
    # Fully redundant now that sheet_payout_status.wallet_balance is sourced
    # directly from the (real) payout sheet's own wallet-balance column —
    # see app/integrations/payout_client.py.
    op.drop_table('sheet_wallet_balance')


def downgrade() -> None:
    op.create_table(
        'sheet_wallet_balance',
        sa.Column('expert_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=True),
        sa.Column('balance', sa.BigInteger(), nullable=True),
        sa.Column('eligible', sa.BigInteger(), nullable=True),
        sa.Column('sheet_updated_at', sa.String(length=60), nullable=True),
        sa.Column('synced_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('expert_id'),
    )
    op.drop_column('sheet_payout_status', 'tds_amount')
    op.drop_column('sheet_payout_status', 'tds_deducted_percent')
    op.drop_column('sheet_payout_status', 'kyc_status')
