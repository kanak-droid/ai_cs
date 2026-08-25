"""One-off: recompute kam_notified/cs_notified for existing tickets from
current data (category + the astrologer's current priority), mirroring the
exact logic in ticket_service.create_ticket. The migration that added these
columns backfilled them to `true` for every existing row (safe default —
preserves old visibility); this script instead makes old tickets reflect
the real notified-flags fix (see docs/chatbot-approach.md §7c), same as if
they'd been created after it. Also the right tool to re-run after any
future change to routing_for_ticket's policy (e.g. the 2026-08-25 change
moving "technical"/"no_visibility"/"profile"/"phone_change" to CS-only,
regardless of priority) — it makes every existing open ticket's flags match
the new rule instead of only affecting tickets created from that point on.

Not idempotent-sensitive — safe to re-run any time (e.g. after priorities
change in the sheet, or after a routing policy change).

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
            priority = ticket_service.astrologer_priority(db, ticket.astrologer_id)
            kam_notified, cs_notified = ticket_service.routing_for_ticket(ticket.category, priority)

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
