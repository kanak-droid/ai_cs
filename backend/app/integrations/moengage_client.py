# MOCKED — replace with real API call.
#
# Real integration: MoEngage's Data API "track event" call — one event per
# ticket status change, so MoEngage's own dashboard-configured campaigns
# decide which transitions actually trigger a push notification to the
# astrologer (and what the copy/deep-link is) — this backend's only job is
# to emit the event reliably, never to send a push itself. The real call is
# already written below (httpx.post(...)); it's just never reached while
# MOENGAGE_MOCK_MODE is on. To go live: confirm the exact event/attribute
# names MoEngage expects against their Data API docs (the shape below is a
# reasonable best guess, not yet verified against a real account), set
# MOENGAGE_MOCK_MODE=false, MOENGAGE_EVENT_API_URL/APP_ID/API_KEY — no other
# code changes.
#
# This has its own mock switch (MOENGAGE_MOCK_MODE), separate from the
# shared MOCK_MODE every other integration uses — same reasoning as
# SLACK_MOCK_MODE (this can go live independently of payout/KYC/salary,
# which have no real backend to switch to yet).
#
# Called from ticket_service._record_status — the single choke point for
# every ticket status write — so this fires for every status change with no
# risk of a call site being missed. Because of that, a MoEngage outage or a
# bug in this module must NEVER be able to block a real ticket status
# transition: every exception from the real network call is caught and
# logged here, not raised, and the caller wraps this call too as
# defense-in-depth (see _record_status's comment).
import logging

import httpx

from app.core.config import settings
from app.models.ticket import Ticket

logger = logging.getLogger(__name__)


def send_ticket_status_event(
    ticket: Ticket, *, new_status: str, changed_by: str, note: str | None
) -> None:
    astrologer = ticket.astrologer
    # MoEngage identifies a customer by the id its SDK registered the device
    # under, in the host app — that's Astrologer.user_id (the real AstroLokal
    # platform's user id), not our own internal `id` or the ops-sheet
    # `expert_id`. No user_id linked yet means we have no way to attribute
    # the event to a real MoEngage customer, so skip rather than send a
    # meaningless one.
    if astrologer is None or astrologer.user_id is None:
        logger.info(
            "Skipping MoEngage event for ticket #%s — astrologer has no linked user_id",
            ticket.id,
        )
        return

    attributes = {
        "ticket_id": ticket.id,
        "status": new_status,
        "category": ticket.category,
        "sub_category": ticket.sub_category,
        "note": note or "",
        "changed_by": changed_by,
    }

    if settings.MOENGAGE_MOCK_MODE:
        logger.info(
            "[mock] MoEngage event ticket_status_changed for user_id=%s: %s",
            astrologer.user_id,
            attributes,
        )
        return

    try:
        response = httpx.post(
            settings.MOENGAGE_EVENT_API_URL.format(app_id=settings.MOENGAGE_APP_ID),
            auth=(settings.MOENGAGE_APP_ID, settings.MOENGAGE_API_KEY),
            json={
                "type": "event",
                "customer_id": str(astrologer.user_id),
                "actions": [
                    {
                        "action": "ticket_status_changed",
                        "attributes": attributes,
                    }
                ],
            },
            timeout=10.0,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("MoEngage event send failed for ticket #%s", ticket.id)
