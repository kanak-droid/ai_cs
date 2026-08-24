"""One-off: push existing open tickets (created before the Zoho Desk sync
existed) into Zoho. Only tickets still actively being worked — submitted,
assigned_to_kam, under_review, or in_progress — never resolved/closed ones,
which would just add closed-out noise to the Zoho queue.

Safe to re-run: a ticket that already has a zoho_ticket_id (pushed by a
previous run, or by create_ticket/reassign_ticket in the meantime) is
skipped automatically by the same guard those use — so a run interrupted
partway through, or run twice by accident, never double-pushes anything.
Each ticket is committed individually, so progress from an interrupted run
is never lost.

Defaults to a dry run (lists what it would push, pushes nothing) — pass
--execute to actually push. Refuses to run with --execute while
ZOHO_MOCK_MODE is on: that would mark ~all of these tickets as "pushed"
with fake mock-* ids, silently preventing them from ever being really
pushed later (see backfill_push_to_zoho's guard).

Usage:
    python -m scripts.backfill_zoho_tickets            # dry run
    python -m scripts.backfill_zoho_tickets --execute   # actually push
"""

import argparse
import sys
import time

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import TicketStatus
from app.models.ticket import Ticket
from app.services import ticket_service

# Real API calls per ticket (create, plus an attachment upload if it has
# one) — this pause between tickets keeps a ~400-ticket backfill well
# clear of Zoho's per-minute rate limits without needing exact numbers.
_DELAY_SECONDS = 0.5

_OPEN_STATUSES = (
    TicketStatus.SUBMITTED,
    TicketStatus.ASSIGNED_TO_KAM,
    TicketStatus.UNDER_REVIEW,
    TicketStatus.IN_PROGRESS,
)


def main(execute: bool) -> None:
    if execute and settings.ZOHO_MOCK_MODE:
        print(
            "ZOHO_MOCK_MODE is on — refusing to --execute. Running this for real while "
            "mocked would tag every one of these tickets with a fake zoho_ticket_id, "
            "which permanently skips them on any future real run. Flip ZOHO_MOCK_MODE "
            "off first if you actually mean to push these tickets now."
        )
        sys.exit(1)

    db = SessionLocal()
    try:
        tickets = (
            db.query(Ticket)
            .filter(
                Ticket.cs_notified.is_(True),
                Ticket.zoho_ticket_id.is_(None),
                Ticket.status.in_(_OPEN_STATUSES),
            )
            .order_by(Ticket.created_at)
            .all()
        )
        print(f"Found {len(tickets)} open ticket(s) eligible to push to Zoho.")

        if not execute:
            print("Dry run — no changes made. Re-run with --execute to actually push.")
            for t in tickets:
                print(f"  would push ticket #{t.id} ({t.status.value}, category={t.category})")
            return

        pushed = 0
        failed = 0
        for t in tickets:
            ok = ticket_service.backfill_push_to_zoho(db, t)
            db.commit()
            if ok:
                pushed += 1
                print(f"  pushed ticket #{t.id} -> zoho {t.zoho_ticket_id}")
            else:
                failed += 1
                print(f"  FAILED to push ticket #{t.id} (see logs for the real error)")
            time.sleep(_DELAY_SECONDS)

        print(f"Done. Pushed {pushed}, failed {failed}, out of {len(tickets)}.")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually push (default is dry-run).")
    args = parser.parse_args()
    main(execute=args.execute)
