"""Seed the local database with a handful of admins and astrologers so the app
has real-looking data to click through immediately. Safe to re-run — it skips
anything already present.

Usage:
    python -m scripts.seed
"""

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.models.astrologer import Astrologer

ADMINS = [
    {"name": "Ananya Rao", "email": "ananya@astrolokal.example", "slack_channel": "#support-1"},
    {"name": "Vikram Shah", "email": "vikram@astrolokal.example", "slack_channel": "#support-2"},
    {"name": "Meera Iyer", "email": "meera@astrolokal.example", "slack_channel": "#support-3"},
]
DEFAULT_ADMIN_PASSWORD = "astrohelp123"

ASTROLOGERS = [
    {"name": "Priya Sharma", "phone": "+91-98765-00001", "language": "Hindi"},
    {"name": "Rahul Verma", "phone": "+91-98765-00002", "language": "Hinglish"},
    {"name": "Fatima Khan", "phone": "+91-98765-00003", "language": "English"},
    {"name": "Suresh Nair", "phone": "+91-98765-00004", "language": "Malayalam"},
    {"name": "Kavita Joshi", "phone": "+91-98765-00005", "language": "Marathi"},
    {"name": "Arjun Reddy", "phone": "+91-98765-00006", "language": "Telugu"},
]


def seed() -> None:
    db = SessionLocal()
    try:
        admins_by_email = {a.email: a for a in db.query(Admin).all()}
        seeded_admins = []
        for admin_data in ADMINS:
            admin = admins_by_email.get(admin_data["email"])
            if admin is None:
                admin = Admin(
                    name=admin_data["name"],
                    email=admin_data["email"],
                    slack_channel=admin_data["slack_channel"],
                    password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                )
                db.add(admin)
                db.flush()
                print(f"Created admin: {admin.email} (password: {DEFAULT_ADMIN_PASSWORD})")
            seeded_admins.append(admin)

        existing_astrologers = db.query(Astrologer).count()
        if existing_astrologers == 0:
            for i, data in enumerate(ASTROLOGERS):
                assigned_admin = seeded_admins[i % len(seeded_admins)]
                astrologer = Astrologer(
                    name=data["name"],
                    phone=data["phone"],
                    language=data["language"],
                    assigned_admin_id=assigned_admin.id,
                )
                db.add(astrologer)
                print(f"Created astrologer: {astrologer.name} -> admin {assigned_admin.name}")
        else:
            print(f"Skipping astrologer seed — {existing_astrologers} already exist.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
