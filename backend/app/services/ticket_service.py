"""Owns every write to Ticket.status and TicketStatusHistory.

This is the ONLY module allowed to mutate ticket status. `_record_status`
inserts the history row and mirrors `ticket.status` in the same transaction,
so the two can never diverge — there is deliberately no other way to change a
ticket's status (no DB trigger, no ORM event hook; see the build plan for why).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.integrations import admin_mapping_client, slack_client
from app.models.enums import TicketStatus
from app.models.ticket import Ticket
from app.models.ticket_status_history import TicketStatusHistory


def _record_status(
    db: Session, ticket: Ticket, status: TicketStatus, *, changed_by: str, note: str | None = None
) -> None:
    db.add(TicketStatusHistory(ticket_id=ticket.id, status=status, changed_by=changed_by, note=note))
    ticket.status = status


def create_ticket(
    db: Session,
    *,
    astrologer_id: int,
    category: str,
    sub_category: str,
    description: str,
    description_en: str,
    preferred_language: str,
    attachment_url: str | None = None,
) -> Ticket:
    """Create a ticket, then auto-assign it and notify Slack — all in one transaction.

    This cross-integration sequencing (create -> assign -> notify) belongs here,
    not in the agent or in a route handler.
    """
    ticket = Ticket(
        astrologer_id=astrologer_id,
        category=category,
        sub_category=sub_category,
        description=description,
        description_en=description_en,
        preferred_language=preferred_language,
        attachment_url=attachment_url,
        status=TicketStatus.SUBMITTED,
    )
    db.add(ticket)
    db.flush()  # assigns ticket.id

    _record_status(db, ticket, TicketStatus.SUBMITTED, changed_by="system", note="Ticket submitted")

    assignment = admin_mapping_client.get_assigned_admin(db, astrologer_id)
    ticket.assigned_admin_id = assignment.admin_id
    _record_status(
        db,
        ticket,
        TicketStatus.ASSIGNED_TO_KAM,
        changed_by="system",
        note=f"Auto-assigned to admin #{assignment.admin_id}",
    )

    slack_client.post_message(
        db,
        channel="#support",
        text=(
            f"New ticket #{ticket.id} ({category}/{sub_category}) from astrologer "
            f"{astrologer_id}, assigned to admin #{assignment.admin_id}."
        ),
        ticket_id=ticket.id,
    )

    db.commit()
    db.refresh(ticket)
    return ticket


def transition_status(
    db: Session, ticket: Ticket, new_status: TicketStatus, *, changed_by: str, note: str | None = None
) -> Ticket:
    _record_status(db, ticket, new_status, changed_by=changed_by, note=note)
    db.commit()
    db.refresh(ticket)
    return ticket


def get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


def get_ticket_for_astrologer(db: Session, ticket_id: int, astrologer_id: int) -> Ticket:
    ticket = get_ticket(db, ticket_id)
    if ticket.astrologer_id != astrologer_id:
        raise NotFoundError(f"Ticket {ticket_id} not found")
    return ticket


def list_tickets_for_astrologer(db: Session, astrologer_id: int) -> list[Ticket]:
    stmt = (
        select(Ticket)
        .where(Ticket.astrologer_id == astrologer_id)
        .order_by(Ticket.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def list_all_tickets(
    db: Session,
    *,
    status: TicketStatus | None = None,
    assigned_admin_id: int | None = None,
    sort_desc: bool = True,
) -> list[Ticket]:
    stmt = select(Ticket)
    if status is not None:
        stmt = stmt.where(Ticket.status == status)
    if assigned_admin_id is not None:
        stmt = stmt.where(Ticket.assigned_admin_id == assigned_admin_id)
    stmt = stmt.order_by(Ticket.created_at.desc() if sort_desc else Ticket.created_at.asc())
    return list(db.scalars(stmt).all())
