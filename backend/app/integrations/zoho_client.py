# MOCKED — replace with real API calls.
#
# Real integration: Zoho Desk REST API v1. Push: create a ticket there when
# one gets raised to a CS on our side, then keep its status in sync as ours
# changes. Pull is NOT this file — that's the inbound webhook
# (app/api/routes/integrations/zoho_webhook.py), which calls back into
# ticket_service directly rather than through here.
#
# Unlike every other integration in this app, Zoho auth is OAuth (client
# id/secret + a long-lived refresh token) rather than a static key — there's
# no "just paste in a token" here. _get_access_token() exchanges the refresh
# token for a short-lived access token and caches it in memory until it's
# about to expire, refreshing on demand. To go live: create an OAuth client
# in the Zoho API Console (Self Client or Server-based, Desk.tickets.ALL
# scope), generate a refresh token, and set ZOHO_CLIENT_ID/
# ZOHO_CLIENT_SECRET/ZOHO_REFRESH_TOKEN/ZOHO_ORG_ID/ZOHO_DEPARTMENT_ID, then
# flip ZOHO_MOCK_MODE off — no other code changes.
#
# Own mock switch (ZOHO_MOCK_MODE), same reasoning as SLACK_MOCK_MODE — can
# go live independently of every other integration here.
#
# Called from ticket_service.py's _maybe_push_to_zoho/_record_status/
# escalate_to_kam — same belt-and-suspenders safety requirement as
# moengage_client: every real-network exception is caught and logged here,
# never raised, so a Zoho outage can never block a real ticket write.
import logging
import time

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import object_storage, queue_performance_client
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)

# Zoho Desk's own status set is coarser than ours — see the mapping this
# feeds (ticket_service.py). escalated_to_kam overrides to "Escalated"
# regardless of the underlying TicketStatus.
_STATUS_MAP = {
    "submitted": "Open",
    "assigned_to_kam": "Open",
    "under_review": "Open",
    "in_progress": "Open",
    "resolved": "Closed",
    "closed": "Closed",
}

# In-memory cache for the OAuth access token — Zoho's are short-lived
# (~1 hour), so refreshing on every call would be wasteful and refreshing
# never would eventually 401. Module-level is fine: one process, one token.
_access_token: str | None = None
_access_token_expires_at: float = 0.0

# Same reasoning for the agent list — a small, slow-changing set, not worth
# a real API call on every single ticket push. Keyed by nothing (one org),
# just a flat cached list refreshed hourly.
_agents_cache: list[dict] | None = None
_agents_cache_expires_at: float = 0.0


def zoho_status_for(ticket: Ticket) -> str:
    if ticket.escalated_to_kam:
        return "Escalated"
    return _STATUS_MAP[ticket.status.value]


def _get_access_token() -> str:
    global _access_token, _access_token_expires_at
    # 60s safety margin so a token doesn't expire mid-request.
    if _access_token and time.monotonic() < _access_token_expires_at - 60:
        return _access_token

    response = httpx.post(
        f"{settings.ZOHO_ACCOUNTS_DOMAIN}/oauth/v2/token",
        params={
            "refresh_token": settings.ZOHO_REFRESH_TOKEN,
            "client_id": settings.ZOHO_CLIENT_ID,
            "client_secret": settings.ZOHO_CLIENT_SECRET,
            "grant_type": "refresh_token",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
    _access_token = data["access_token"]
    _access_token_expires_at = time.monotonic() + data.get("expires_in", 3600)
    return _access_token


def _headers() -> dict:
    return {
        "Authorization": f"Zoho-oauthtoken {_get_access_token()}",
        "orgId": settings.ZOHO_ORG_ID,
    }


def _get_agents() -> list[dict]:
    global _agents_cache, _agents_cache_expires_at
    if settings.ZOHO_MOCK_MODE:
        return []
    if _agents_cache is not None and time.monotonic() < _agents_cache_expires_at:
        return _agents_cache

    response = httpx.get(
        f"{settings.ZOHO_API_DOMAIN}/api/v1/agents", headers=_headers(), timeout=10.0
    )
    response.raise_for_status()
    _agents_cache = response.json().get("data", [])
    _agents_cache_expires_at = time.monotonic() + 3600
    return _agents_cache


def find_agent_id_by_email(email: str | None) -> str | None:
    """Best-effort match of an AstroHelp admin's email to a real Zoho Desk
    agent, so a pushed ticket lands pre-assigned to the right CS instead of
    sitting Unassigned. Returns None — never raises — if there's no email,
    no matching agent, or the lookup itself fails; an admin whose email
    differs between the two systems just leaves the ticket unassigned, same
    as today, rather than guessing wrong.
    """
    if not email:
        return None
    try:
        agents = _get_agents()
    except Exception:
        logger.exception("Zoho Desk agent lookup failed")
        return None
    for agent in agents:
        if (agent.get("emailId") or "").lower() == email.lower():
            return agent.get("id")
    return None


def create_ticket(db: Session, ticket: Ticket) -> str | None:
    """Returns the new Zoho ticket id, or None if mocked or the real call
    failed — callers treat None as "not pushed", never as an error to
    surface to the astrologer/admin."""
    astrologer = ticket.astrologer
    # Same priority lookup/label convention as the Slack ticket-created
    # notification (ticket_service.create_ticket) — lets a CS spot a VIP
    # astrologer's ticket in the Zoho queue without opening it. Caught on
    # its own, separate from the real-network try/except below — a
    # priority-lookup failure must never abort ticket creation either.
    try:
        priority = queue_performance_client.get_queue_performance(db, ticket.astrologer_id).priority
    except Exception:
        logger.exception("Priority lookup failed for ticket #%s; using Unranked in Zoho subject", ticket.id)
        priority = None
    priority_label = f"P{priority}" if priority is not None else "Unranked"
    # Leftmost so it's visible even when the ticket list truncates a long
    # subject — priority is the most scannable thing for triage.
    subject = (
        f"({priority_label}) [AstroHelp #{ticket.id}] {ticket.category} / {ticket.sub_category}"
    )

    if settings.ZOHO_MOCK_MODE:
        fake_id = f"mock-{ticket.id}"
        logger.info("[mock] Would create Zoho Desk ticket %s: %s", fake_id, subject)
        return fake_id

    try:
        payload = {
            "subject": subject,
            "description": ticket.description_en,
            "departmentId": settings.ZOHO_DEPARTMENT_ID,
            "status": zoho_status_for(ticket),
            "contact": {
                "lastName": astrologer.name or f"Astrologer #{astrologer.id}",
                "phone": astrologer.phone,
            },
        }
        agent_id = find_agent_id_by_email(ticket.assigned_cs.email if ticket.assigned_cs else None)
        if agent_id:
            payload["assigneeId"] = agent_id

        response = httpx.post(
            f"{settings.ZOHO_API_DOMAIN}/api/v1/tickets", headers=_headers(), json=payload, timeout=10.0
        )
        response.raise_for_status()
        return response.json()["id"]
    except Exception:
        logger.exception("Zoho Desk ticket creation failed for AstroHelp ticket #%s", ticket.id)
        return None


def post_comment(zoho_ticket_id: str, comment: str) -> None:
    """Adds a comment to a Zoho ticket — used to carry the astrologer's
    full chat transcript (see chat_session_service.get_transcript_text),
    kept separate from the ticket's own short description. Posted as a
    private/internal comment (isPublic=False) — the astrologer has no
    Zoho customer portal login, so there's no audience for it to be
    public toward; this is purely for whoever on the team works the
    ticket. Best-effort, same as every other call here.

    contentType is explicitly "plainText" — Zoho defaults new comments to
    "html" if this is left out, which silently collapses our \\n\\n turn
    breaks into one run-on paragraph (confirmed live 2026-08-24: HTML
    ignores raw newlines). Declaring plainText makes Zoho render real line
    breaks instead.
    """
    if settings.ZOHO_MOCK_MODE:
        logger.info("[mock] Would post comment to Zoho Desk ticket %s: %s", zoho_ticket_id, comment)
        return

    try:
        response = httpx.post(
            f"{settings.ZOHO_API_DOMAIN}/api/v1/tickets/{zoho_ticket_id}/comments",
            headers=_headers(),
            json={"content": comment, "contentType": "plainText", "isPublic": False},
            timeout=15.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Zoho Desk comment post failed for ticket %s", zoho_ticket_id)


def upload_attachment(zoho_ticket_id: str, attachment_url: str) -> None:
    """Pushes a ticket's screenshot/video INTO the Zoho ticket as a real
    attachment (Zoho Desk hosts the file itself, not just a link) — same
    reasoning and pattern as slack_client.upload_attachment. Best-effort:
    a failure here is logged, never raised — the ticket itself already
    exists in Zoho regardless, this is purely a convenience/durability push.
    """
    if settings.ZOHO_MOCK_MODE:
        logger.info(
            "[mock] Would upload attachment to Zoho Desk ticket %s: %s", zoho_ticket_id, attachment_url
        )
        return

    try:
        content, content_type = object_storage.download_file(attachment_url)
        filename = attachment_url.rsplit("/", 1)[-1] or f"ticket-{zoho_ticket_id}-attachment"
        response = httpx.post(
            f"{settings.ZOHO_API_DOMAIN}/api/v1/tickets/{zoho_ticket_id}/attachments",
            headers=_headers(),
            files={"file": (filename, content, content_type)},
            timeout=30.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Zoho Desk attachment upload failed for ticket %s", zoho_ticket_id)


def update_assignee(zoho_ticket_id: str, agent_id: str) -> None:
    if settings.ZOHO_MOCK_MODE:
        logger.info("[mock] Would set Zoho Desk ticket %s assignee to %s", zoho_ticket_id, agent_id)
        return

    try:
        response = httpx.patch(
            f"{settings.ZOHO_API_DOMAIN}/api/v1/tickets/{zoho_ticket_id}",
            headers=_headers(),
            json={"assigneeId": agent_id},
            timeout=10.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Zoho Desk assignee update failed for ticket %s", zoho_ticket_id)


def update_status(zoho_ticket_id: str, zoho_status: str) -> None:
    if settings.ZOHO_MOCK_MODE:
        logger.info("[mock] Would set Zoho Desk ticket %s status to %s", zoho_ticket_id, zoho_status)
        return

    try:
        response = httpx.patch(
            f"{settings.ZOHO_API_DOMAIN}/api/v1/tickets/{zoho_ticket_id}",
            headers=_headers(),
            json={"status": zoho_status},
            timeout=10.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Zoho Desk status update failed for ticket %s", zoho_ticket_id)
