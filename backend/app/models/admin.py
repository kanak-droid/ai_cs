from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.db.base import Base
from app.models.enums import AdminAccessLevel, AdminRole

if TYPE_CHECKING:
    from app.models.astrologer import Astrologer


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Nullable only for pre-existing rows from the retired self-service signup
    # flow; every account created via auth_service.grant_access gets one
    # immediately (the shared password for its access_level).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slack_channel: Mapped[str] = mapped_column(String(80), default="#support")
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole, name="admin_role", native_enum=False), default=AdminRole.KAM
    )
    access_level: Mapped[AdminAccessLevel] = mapped_column(
        Enum(AdminAccessLevel, name="admin_access_level", native_enum=False),
        default=AdminAccessLevel.NORMAL,
    )
    # Languages this admin can serve as CS — see cs_assignment_client's
    # per-language round robin. Irrelevant for KAM (round-robin is
    # language-blind for them) but not restricted to CS at the DB level.
    languages: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    astrologers: Mapped[list["Astrologer"]] = relationship(back_populates="assigned_admin")
