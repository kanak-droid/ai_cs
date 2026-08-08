from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
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

    # Mocked payout/KYC/salary fields — for now these merely seed the mocked
    # integration clients with per-astrologer values; a real integration would
    # drop these columns entirely and fetch live from the source system instead.
    kyc_status: Mapped[str] = mapped_column(String(20), default="pending")
    payout_status: Mapped[str] = mapped_column(String(20), default="scheduled")
    monthly_salary_inr: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    assigned_admin: Mapped["Admin | None"] = relationship(back_populates="astrologers")
