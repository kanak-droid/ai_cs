"""Close every RESOLVED ticket the astrologer never responded to within 48
hours. Optional — the same check already happens lazily whenever anyone
loads a ticket (see ticket_service._maybe_auto_close_stale), which is
reliable in practice since both the astrologer's chat and the admin
dashboard read tickets regularly. Run this only if you want a stronger,
not-dependent-on-someone-looking guarantee, via an external cron/scheduled
job — this script itself doesn't loop or schedule anything.

Usage:
    python -m scripts.auto_close_resolved_tickets
"""

from app.db.session import SessionLocal
from app.services import ticket_service


def main() -> None:
    db = SessionLocal()
    try:
        closed = ticket_service.auto_close_stale_resolved_tickets(db)
    finally:
        db.close()

    print(f"Auto-closed {len(closed)} ticket(s): {[t.id for t in closed]}")


if __name__ == "__main__":
    main()
