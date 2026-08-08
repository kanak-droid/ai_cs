# MOCKED — replace with real API call.
#
# Real integration: this would call AstroLokal's ops/roster service, e.g.
#   GET {ROSTER_API_URL}/astrologers/{astrologer_id}/assigned-admin
# and wouldn't need a `db` argument at all — drop it from the signature (and its
# one call site in ticket_service / tool_registry) when swapping this in.
#
# For now it's a deterministic round-robin over whichever admins actually exist
# in our own `admins` table, so ticket auto-assignment never points at an admin
# id that doesn't exist (a hardcoded id range would drift the moment admins are
# added, removed, or — as in tests — created with non-sequential ids).
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.config import MOCK_MODE
from app.models.admin import Admin


@dataclass(frozen=True)
class AssignedAdmin:
    astrologer_id: int
    admin_id: int


def get_assigned_admin(db: Session, astrologer_id: int) -> AssignedAdmin:
    if not MOCK_MODE:
        raise NotImplementedError("Real admin-mapping integration is not wired up yet.")

    admin_ids = [row for row in db.scalars(select(Admin.id).order_by(Admin.id)).all()]
    if not admin_ids:
        raise RuntimeError("No admins found — run scripts/seed.py before creating tickets.")

    admin_id = admin_ids[(astrologer_id - 1) % len(admin_ids)]
    return AssignedAdmin(astrologer_id=astrologer_id, admin_id=admin_id)
