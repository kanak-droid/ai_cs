# MOCKED — replace with real API call.
#
# Real integration: posts to a Slack incoming webhook (or a bot token + chat.postMessage
# call) for the relevant admin's channel. The real call is already written below
# (httpx.post(...)); it's just never reached while SLACK_MOCK_MODE is on. To go live: set
# SLACK_MOCK_MODE=false and SLACK_WEBHOOK_URL to the real webhook — no other code changes.
#
# This has its own mock switch (SLACK_MOCK_MODE), separate from the shared MOCK_MODE
# every other integration uses — Slack can go live independently, since payout/KYC/
# salary/etc. have no real backend to switch to yet.
#
# Under mock mode, instead of calling out to Slack, every notification is written to
# the slack_log table so the admin dashboard's Slack panel can show what "would have"
# been sent.
import logging

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.slack_log import SlackLog

logger = logging.getLogger(__name__)

_SLACK_API = "https://slack.com/api"


def post_message(db: Session, channel: str, text: str, ticket_id: int | None = None) -> SlackLog:
    if settings.SLACK_MOCK_MODE:
        log_entry = SlackLog(channel=channel, message=text, ticket_id=ticket_id, mock=True)
        db.add(log_entry)
        db.flush()
        return log_entry

    response = httpx.post(
        settings.SLACK_WEBHOOK_URL,
        json={
            "text": text,
            "username": "AstroLokal Support",
            # Only resolvable by Slack's servers once PUBLIC_BASE_URL is a real
            # public URL — on localhost this renders as a broken/default icon.
            "icon_url": f"{settings.PUBLIC_BASE_URL}/static/astrolokal-logo.png",
        },
        timeout=10.0,
    )
    response.raise_for_status()
    log_entry = SlackLog(channel=channel, message=text, ticket_id=ticket_id, mock=False)
    db.add(log_entry)
    db.flush()
    return log_entry


def upload_attachment(db: Session, *, attachment_url: str, ticket_id: int) -> None:
    """Pushes a ticket's photo/video INTO Slack (Slack hosts the file itself,
    not just a link back to our server) — durable regardless of our own
    container's disk, and syncs to a KAM/CS's Slack app in the background
    without them opening the admin dashboard at all.

    Independent of post_message's incoming webhook — that can't upload
    files, only text — needs a real Bot Token (files:write scope, bot
    invited to SLACK_UPLOAD_CHANNEL_ID). Best-effort: a failure here is
    logged, never raised. The astrologer's ticket already exists and its
    attachment_url is still reachable regardless — this is purely a
    durability/convenience push, never the only copy.
    """
    if settings.SLACK_MOCK_MODE:
        log_entry = SlackLog(
            channel=settings.SLACK_UPLOAD_CHANNEL_ID or "(unset)",
            message=f"[mock] would upload attachment for ticket #{ticket_id}: {attachment_url}",
            ticket_id=ticket_id,
            mock=True,
        )
        db.add(log_entry)
        db.flush()
        return

    try:
        _real_upload_attachment(db, attachment_url=attachment_url, ticket_id=ticket_id)
    except Exception:
        logger.exception("Slack file upload failed for ticket #%s", ticket_id)


def _real_upload_attachment(db: Session, *, attachment_url: str, ticket_id: int) -> None:
    image = httpx.get(attachment_url, timeout=15.0)
    image.raise_for_status()
    content = image.content
    filename = attachment_url.rsplit("/", 1)[-1] or f"ticket-{ticket_id}-attachment"

    headers = {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}

    # Slack's 3-step external upload flow (files.upload was sunset) —
    # 1) get a one-time upload URL, 2) PUT/POST the raw bytes there,
    # 3) finalize + post it into the channel as a real message.
    init = httpx.post(
        f"{_SLACK_API}/files.getUploadURLExternal",
        headers=headers,
        data={"filename": filename, "length": len(content)},
        timeout=15.0,
    )
    init.raise_for_status()
    init_data = init.json()
    if not init_data.get("ok"):
        raise RuntimeError(f"files.getUploadURLExternal failed: {init_data.get('error')}")

    upload = httpx.post(init_data["upload_url"], files={"file": (filename, content)}, timeout=30.0)
    upload.raise_for_status()

    complete = httpx.post(
        f"{_SLACK_API}/files.completeUploadExternal",
        headers={**headers, "Content-Type": "application/json"},
        json={
            "files": [{"id": init_data["file_id"], "title": filename}],
            "channel_id": settings.SLACK_UPLOAD_CHANNEL_ID,
            "initial_comment": f"📎 Attachment for ticket #{ticket_id}",
        },
        timeout=15.0,
    )
    complete.raise_for_status()
    complete_data = complete.json()
    if not complete_data.get("ok"):
        raise RuntimeError(f"files.completeUploadExternal failed: {complete_data.get('error')}")

    log_entry = SlackLog(
        channel=settings.SLACK_UPLOAD_CHANNEL_ID,
        message=f"Uploaded attachment for ticket #{ticket_id} ({filename})",
        ticket_id=ticket_id,
        mock=False,
    )
    db.add(log_entry)
    db.flush()
