"""One-off: recompute kam_notified/cs_notified for existing tickets from
current data (category + the astrologer's current priority), mirroring the
exact logic in ticket_service.create_ticket. The migration that added these
columns backfilled them to `true` for every existing row (safe default —
preserves old visibility); this script instead makes old tickets reflect
the real notified-flags fix (see docs/chatbot-approach.md §7c), same as if
they'd been created after it.

Not idempotent-sensitive — safe to re-run any time (e.g. after priorities
change in the sheet).

Usage:
    python -m scripts.backfill_ticket_notified
"""

from app.db.session import SessionLocal
from app.models.ticket import Ticket
from app.services import ticket_service


def main() -> None:
    db = SessionLocal()
    try:
        changed = 0
        for ticket in db.query(Ticket).all():
            is_vip = ticket_service.is_vip_priority(db, ticket.astrologer_id)
            _, kam_notified, cs_notified = ticket_service.routing_for_ticket(ticket.category, is_vip)

            if ticket.kam_notified != kam_notified or ticket.cs_notified != cs_notified:
                ticket.kam_notified = kam_notified
                ticket.cs_notified = cs_notified
                changed += 1

        db.commit()
        print(f"Recomputed notified-flags for all tickets — {changed} row(s) changed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
