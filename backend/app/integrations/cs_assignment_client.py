# MOCKED — replace with real API call, same shape as admin_mapping_client.
#
# Round-robins a ticket to a CS admin who serves the astrologer's language,
# based on our own `admins.languages` (set via the dashboard/scripts/create_admin.py)
# and the astrologer's `language` (synced from the ops sheet — see
# sheets_sync_service._sync_astrologer_profiles). No persisted cursor: using
# ticket.id (strictly increasing) as the round-robin index means each new
# ticket in a language rotates to the next matching CS deterministically,
# without needing extra state.
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.config import MOCK_MODE
from app.integrations.language_matching import split_languages
from app.models.admin import Admin
from app.models.enums import AdminRole


@dataclass(frozen=True)
class AssignedCs:
    ticket_id: int
    admin_id: int


def get_assigned_cs(db: Session, *, ticket_id: int, astrologer_language: str) -> AssignedCs | None:
    if not MOCK_MODE:
        raise NotImplementedError("Real CS-assignment integration is not wired up yet.")

    # is_temporarily_inactive excluded same as permanent deactivation for NEW
    # assignment purposes — see admin_mapping_client.fetch_active_kams.
    cs_admins = list(
        db.scalars(
            select(Admin).where(
                Admin.is_active,
                Admin.is_temporarily_inactive.is_(False),
                Admin.role == AdminRole.CS,
            )
        ).all()
    )
    if not cs_admins:
        return None

    wanted = set(split_languages(astrologer_language))
    matching = [a for a in cs_admins if wanted & set(a.languages)] if wanted else []
    # No CS covers this astrologer's language(s) — fall back to the full CS
    # pool rather than leaving the ticket without a CS owner at all.
    pool = matching or cs_admins

    admin_id = pool[ticket_id % len(pool)].id
    return AssignedCs(ticket_id=ticket_id, admin_id=admin_id)
