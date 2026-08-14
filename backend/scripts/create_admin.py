"""Grant (or update) an admin's dashboard access — a CLI front-end for
app.services.auth_service.grant_access, for bootstrapping/scripting instead
of using the dashboard's own "Add access" form.

Usage:
    python -m scripts.create_admin --name "Ananya Rao" --email ananya@getlokalapp.com --role kam
    python -m scripts.create_admin --name "Parth" --email parth.a@getlokalapp.com --role kam --access-level admin
    python -m scripts.create_admin --name "Preethi" --email preeti.boge@getlokalapp.com --role cs --languages Hindi,Telugu
"""

import argparse

from app.db.session import SessionLocal
from app.models.enums import AdminAccessLevel, AdminRole
from app.services import auth_service


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=["kam", "cs", "others"])
    parser.add_argument("--access-level", default="normal", choices=["normal", "admin"])
    parser.add_argument("--languages", default="", help="Comma-separated, e.g. Hindi,Telugu")
    args = parser.parse_args()

    languages = [lang.strip() for lang in args.languages.split(",") if lang.strip()]

    db = SessionLocal()
    try:
        admin = auth_service.grant_access(
            db,
            email=args.email,
            name=args.name,
            role=AdminRole(args.role),
            access_level=AdminAccessLevel(args.access_level),
            languages=languages,
        )
        password = auth_service.password_for_access_level(admin.access_level)
        langs = ", ".join(admin.languages) or "none"
        print(
            f"{admin.email} ({admin.role.value}, {admin.access_level.value} access, "
            f"languages: {langs}) — password: {password}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
