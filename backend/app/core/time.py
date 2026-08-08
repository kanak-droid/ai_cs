from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC datetime for DateTime (without timezone) columns.

    Using timezone.utc and dropping tzinfo avoids datetime.utcnow()'s
    deprecation while keeping storage consistent with the existing
    (non-timezone-aware) DateTime columns.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
