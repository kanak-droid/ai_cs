"""Tables populated by app/services/sheets_sync_service.py — one row per
expert_id per table, always overwritten with the latest sync (no history).

Deliberately excludes PAN, UPI id, bank account number, Aadhaar, email, and
address — those columns exist in the source sheets but are never read into
any of these models, so they can't leak into anything the chatbot says.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class SheetAstrologerRoster(Base):
    __tablename__ = "sheet_astrologer_roster"

    expert_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class SheetKycRecord(Base):
    __tablename__ = "sheet_kyc_records"

    expert_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expert_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    kyc_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entry_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class SheetPayoutStatus(Base):
    __tablename__ = "sheet_payout_status"

    expert_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    wallet_balance: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payout: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    incentive: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    penalty_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # This cycle's KYC status and TDS deduction — "YES"/"NO" and a percent
    # string like "1%" or "20%" straight from the payout sheet's own columns
    # (not the separate KYC sheet), so "why is my payout low" can point at
    # the exact TDS rate actually applied that cycle. See payout_client.py.
    kyc_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tds_deducted_percent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tds_amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_after_tax: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    processed_at: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cycle_tab: Mapped[str | None] = mapped_column(String(60), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class SheetQueuePerformance(Base):
    __tablename__ = "sheet_queue_performance"

    expert_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expert_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    languages: Mapped[str | None] = mapped_column(String(120), nullable=True)
    users_connected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queues_connected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_talktime_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sheet_updated_at: Mapped[str | None] = mapped_column(String(60), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
