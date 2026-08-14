"""Pull the ops team's Google Sheets (roster/KYC/payout) into Postgres.
Meant to run once a day via an external cron/scheduled job — this script
itself doesn't loop or schedule anything.

Usage:
    python -m scripts.sync_sheets
"""

from app.db.session import SessionLocal
from app.services import sheets_sync_service


def main() -> None:
    db = SessionLocal()
    try:
        results = sheets_sync_service.sync_all(db)
    finally:
        db.close()

    for name, result in results.items():
        print(f"{name}: {result}")


if __name__ == "__main__":
    main()
