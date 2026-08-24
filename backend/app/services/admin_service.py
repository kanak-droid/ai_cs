from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models.admin import Admin


def maybe_end_scheduled_leave(db: Session, admin: Admin) -> None:
    """Lazy, on-read auto-revert for a scheduled leave's end date — same
    not-dependent-on-anyone-looking convention as
    ticket_service._maybe_auto_close_stale. Call this on every admin that
    gets read where an expired leave would matter: the admins list endpoint,
    and both round-robin eligibility queries (admin_mapping_client,
    cs_assignment_client) — those filter is_temporarily_inactive at the SQL
    level, so they must run this over their wider candidate set BEFORE that
    filter is applied, not after, or a stale-True admin would never be
    loaded in the first place to get fixed.
    """
    if (
        admin.is_temporarily_inactive
        and admin.leave_until is not None
        and utcnow().date() > admin.leave_until
    ):
        admin.is_temporarily_inactive = False
        admin.leave_until = None
        db.commit()
