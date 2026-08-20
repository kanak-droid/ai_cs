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
    # Slack's own member id (e.g. "U0123ABC456", from "Copy member ID" on
    # their Slack profile) — not their name or @handle. Needed to build a
    # real `<@U0123ABC456>` mention, which is the only syntax Slack actually
    # renders as a highlighted, notifying mention; plain "@name" text in an
    # incoming webhook message is never converted into one. Nullable because
    # not every admin has this on file yet — ticket_service falls back to
    # plain "@name" text (visible, but silent) when it's unset.
    slack_user_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
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
    # Temporary, reversible "on leave" state — distinct from is_active
    # (permanent deactivation). An on-leave admin keeps is_active=True: they
    # stay visible everywhere is_active already gates (admin lists, the
    # ticket queue's assigned-admin lookup, KAM/CS performance), so their
    # EXISTING tickets keep rendering correctly (unlike permanent
    # deactivation, which excludes them from that lookup and makes assigned
    # tickets render as unassigned — see docs/chatbot-approach.md). Only
    # gates NEW round-robin assignment (admin_mapping_client/
    # cs_assignment_client) — never touches existing ticket assignments.
    is_temporarily_inactive: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    astrologers: Mapped[list["Astrologer"]] = relationship(back_populates="assigned_admin")
