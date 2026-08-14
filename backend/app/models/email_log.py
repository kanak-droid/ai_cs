from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.base import Base


class EmailLog(Base):
    """Mirrors slack_log.py's pattern — mocked email sends land here instead
    of a real inbox, so the admin dashboard can show what "would have" been
    sent (and a tester can grab a set-password link without real email).
    """

    __tablename__ = "email_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    to_email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(default=utcnow)
    mock: Mapped[bool] = mapped_column(default=True)
