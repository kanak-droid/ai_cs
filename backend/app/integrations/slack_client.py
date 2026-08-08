# MOCKED — replace with real API call.
#
# Real integration: posts to a Slack incoming webhook (or a bot token + chat.postMessage
# call) for the relevant admin's channel. The real call is already written below
# (httpx.post(...)); it's just never reached while MOCK_MODE is on. To go live: set
# MOCK_MODE=false and SLACK_WEBHOOK_URL to the real webhook — no other code changes.
#
# Under MOCK_MODE, instead of calling out to Slack, every notification is written to
# the slack_log table so the admin dashboard's Slack panel can show what "would have"
# been sent.
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.config import MOCK_MODE
from app.models.slack_log import SlackLog


def post_message(db: Session, channel: str, text: str, ticket_id: int | None = None) -> SlackLog:
    if MOCK_MODE:
        log_entry = SlackLog(channel=channel, message=text, ticket_id=ticket_id, mock=True)
        db.add(log_entry)
        db.flush()
        return log_entry

    response = httpx.post(
        settings.SLACK_WEBHOOK_URL,
        json={"channel": channel, "text": text},
        timeout=10.0,
    )
    response.raise_for_status()
    log_entry = SlackLog(channel=channel, message=text, ticket_id=ticket_id, mock=False)
    db.add(log_entry)
    db.flush()
    return log_entry
