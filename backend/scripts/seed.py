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
    {"name": "Ananya Rao", "email": "ananya@getlokalapp.com", "slack_channel": "#support-1"},
    {"name": "Vikram Shah", "email": "vikram@getlokalapp.com", "slack_channel": "#support-2"},
    {"name": "Meera Iyer", "email": "meera@getlokalapp.com", "slack_channel": "#support-3"},
]
DEFAULT_ADMIN_PASSWORD = "astrohelp123"

ASTROLOGERS = [
    # user_id here is a made-up placeholder (90001+), not a real platform id —
    # it only exists so the webview can be opened locally with
    # ?user_id=<value> the same way it would for a real, linked astrologer.
    {"name": "Priya Sharma", "phone": "+91-98765-00001", "language": "Hindi", "user_id": 90001},
    {"name": "Rahul Verma", "phone": "+91-98765-00002", "language": "Hinglish", "user_id": 90002},
    {"name": "Fatima Khan", "phone": "+91-98765-00003", "language": "English", "user_id": 90003},
    {"name": "Suresh Nair", "phone": "+91-98765-00004", "language": "Malayalam", "user_id": 90004},
    {"name": "Kavita Joshi", "phone": "+91-98765-00005", "language": "Marathi", "user_id": 90005},
    {"name": "Arjun Reddy", "phone": "+91-98765-00006", "language": "Telugu", "user_id": 90006},
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
                    user_id=data["user_id"],
                    assigned_admin_id=assigned_admin.id,
                )
                db.add(astrologer)
                print(
                    f"Created astrologer: {astrologer.name} -> admin {assigned_admin.name} "
                    f"(webview: http://localhost:5173/?user_id={astrologer.user_id})"
                )
        else:
            print(f"Skipping astrologer seed — {existing_astrologers} already exist.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
