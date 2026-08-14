# MOCKED — replace with real API call.
#
# Real integration: send via a transactional email provider (SendGrid, SES,
# Postmark, etc.) or plain SMTP. This has its own mock switch (EMAIL_MOCK_MODE,
# same reasoning as SLACK_MOCK_MODE) — under mock mode, instead of sending,
# every email is written to the email_log table so the admin dashboard's
# Email Log panel shows what "would have" been sent (and a tester can grab a
# set-password link without needing a real inbox). To go live: set
# EMAIL_MOCK_MODE=false and implement the real send below — no other code
# changes needed, since callers only see the function signature.
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.email_log import EmailLog


def send_email(db: Session, *, to_email: str, subject: str, body: str) -> EmailLog:
    if not settings.EMAIL_MOCK_MODE:
        raise NotImplementedError("Real email delivery is not wired up yet.")

    log_entry = EmailLog(to_email=to_email, subject=subject, body=body, mock=True)
    db.add(log_entry)
    db.flush()
    return log_entry
