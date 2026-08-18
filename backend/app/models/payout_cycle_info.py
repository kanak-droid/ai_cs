"""Singleton row (id always 1) tracking which payout cycle tab is currently
the latest, and when the next one is expected — computed by
sheets_sync_service._sync_payout_status from the payout spreadsheet's own
tab names (see that module for how "July 31", "August 14 - 1" etc. get
parsed), not hand-maintained. Lets payout_client answer "when's my next
payout" with a real forward-looking date instead of the old
"not tracked" placeholder.
"""

from datetime import date, datetime

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class PayoutCycleInfo(Base):
    __tablename__ = "payout_cycle_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    latest_cycle_tab: Mapped[str] = mapped_column(String(120))
    latest_cycle_date: Mapped[date] = mapped_column(Date)
    next_payout_date: Mapped[date] = mapped_column(Date)
    synced_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
