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
from app.integrations.language_matching import split_languages
from app.models.admin import Admin
from app.models.astrologer import Astrologer
from app.models.enums import AdminRole
from app.services import admin_service


@dataclass(frozen=True)
class AssignedAdmin:
    astrologer_id: int
    admin_id: int


def fetch_active_kams(db: Session) -> list[Admin]:
    # Only KAMs are ever a ticket's "assigned admin" — CS is a separate,
    # language-routed pool (see cs_assignment_client), so CS admins never
    # enter this pool even though they have full dashboard access (see the
    # approach doc §7b). Also excludes anyone on leave (is_temporarily_
    # inactive) — same as permanent deactivation for the purpose of NEW
    # assignment, even though on-leave admins otherwise still count as
    # is_active=True everywhere else (see Admin model's docstring).
    #
    # Fetches the is_temporarily_inactive filter in Python, not SQL: a
    # scheduled leave whose end date has already passed needs its lazy
    # revert (admin_service.maybe_end_scheduled_leave) applied BEFORE that
    # admin can be excluded, and an admin excluded at the SQL level would
    # never get loaded for that check to run on in the first place.
    stmt = select(Admin).where(Admin.is_active, Admin.role == AdminRole.KAM).order_by(Admin.id)
    candidates = list(db.scalars(stmt).all())
    for a in candidates:
        admin_service.maybe_end_scheduled_leave(db, a)
    kams = [a for a in candidates if not a.is_temporarily_inactive]
    if not kams:
        raise RuntimeError("No active KAMs found — run scripts/seed.py before creating tickets.")
    return kams


def pick_kam(kams: list[Admin], *, language: str, index_id: int) -> Admin:
    # Round-robin within whichever KAMs serve the given language(s), same
    # matching rule as CS (see language_matching.split_languages), with a
    # fallback to the full KAM pool when none match — e.g. no KAM covers
    # Bengali yet. Indexed by index_id (the astrologer's own id, not e.g.
    # ticket_id) so the same astrologer always lands on the same KAM — this
    # is their personal point of contact, unlike CS's per-ticket
    # load-balanced assignment.
    wanted = set(split_languages(language)) if language else set()
    matching = [k for k in kams if wanted & set(k.languages)] if wanted else []
    pool = matching or kams
    return pool[(index_id - 1) % len(pool)]


def get_assigned_admin(db: Session, astrologer_id: int) -> AssignedAdmin:
    if not MOCK_MODE:
        raise NotImplementedError("Real admin-mapping integration is not wired up yet.")

    kams = fetch_active_kams(db)
    astrologer = db.get(Astrologer, astrologer_id)
    kam = pick_kam(kams, language=astrologer.language if astrologer else "", index_id=astrologer_id)
    return AssignedAdmin(astrologer_id=astrologer_id, admin_id=kam.id)
