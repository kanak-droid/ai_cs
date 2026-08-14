from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.admin import Admin


class Astrologer(Base):
    __tablename__ = "astrologers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    language: Mapped[str] = mapped_column(String(40), default="English")
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    assigned_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey("admins.id"), nullable=True
    )

    # Join key into the ops team's Google Sheets (roster/KYC/payout/performance)
    # — see app/services/sheets_sync_service.py. Nullable: most seeded test
    # astrologers have no real counterpart in those sheets.
    expert_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)

    # The real AstroLokal platform's user id — confirmed 2026-08-14 as what
    # the astrologer's real JWT is actually keyed by when the main app hands
    # off to this chat webview (not expert_id, and not our own `id` above —
    # both of those are internal to us). Backfilled from the priority-ranking
    # sync (see sheets_sync_service._sync_astrologer_profiles), which now
    # also carries user_id per expert_id. Not yet used to resolve a real
    # token's identity — decode_astrologer_token still only knows our own
    # `id`, via the local-dev scripts/mint_dev_token.py convention — but this
    # is the column to match against once the real token's exact claim shape
    # is confirmed.
    user_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)

    # Mocked payout/KYC/salary fields — for now these merely seed the mocked
    # integration clients with per-astrologer values; a real integration would
    # drop these columns entirely and fetch live from the source system instead.
    kyc_status: Mapped[str] = mapped_column(String(20), default="pending")
    payout_status: Mapped[str] = mapped_column(String(20), default="scheduled")
    monthly_salary_inr: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    assigned_admin: Mapped["Admin | None"] = relationship(back_populates="astrologers")
