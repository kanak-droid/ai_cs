"""Populated by app/services/sheets_sync_service.py's `_sync_expert_priority`
step — one row per expert_id, always overwritten with the latest sync (no
history). Unlike sheet_sync.py's tables, the source here isn't a Google
Sheet: it's a saved analytics query (Redash-style), fetched as CSV over
plain HTTPS with an API key baked into the URL — see
app/integrations/analytics_client.py.
"""

from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class ExpertPriority(Base):
    __tablename__ = "expert_priority"

    expert_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # The real platform user id for this expert — added to the query
    # 2026-08-14, this is the actual identity a real astrologer JWT is keyed
    # by (confirmed by the team), distinct from expert_id (the ops-roster
    # join key this whole table is otherwise keyed by). Used to backfill
    # Astrologer.user_id in _sync_astrologer_profiles.
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expert_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Raw tier from the query: "P1".."P5", "PRE_MATURE", or blank — kept
    # verbatim for transparency/debugging even though the rest of the app
    # only ever consumes `priority` below.
    current_priority_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "P1".."P5" mapped to 1-5. None for PRE_MATURE/blank ("not enough
    # matured users yet to rank") — deliberately not coerced into a fake
    # number, since that would misrepresent an unranked expert as e.g. a
    # real, ordinary P5.
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
