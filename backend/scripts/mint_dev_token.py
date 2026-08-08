"""Mint a local-dev astrologer JWT.

In production, the astrologer's JWT is issued by the main AstroLokal backend and
handed to the chat webview via its URL query string; this backend only ever
verifies it. Locally there's no such issuer, so this CLI signs one with the same
shared secret (JWT_SECRET) for manual testing.

Usage:
    python -m scripts.mint_dev_token --astrologer-id 1 --name "Priya Sharma" --language Hindi
"""

import argparse
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings


def mint_token(astrologer_id: int, name: str, language: str, expires_in_hours: int) -> str:
    payload = {
        "astrologer_id": astrologer_id,
        "name": name,
        "language": language,
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.ASTROLOGER_TOKEN_ALGORITHM)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--astrologer-id", type=int, required=True)
    parser.add_argument("--name", type=str, required=True)
    parser.add_argument("--language", type=str, default="English")
    parser.add_argument("--expires-in-hours", type=int, default=24)
    args = parser.parse_args()

    token = mint_token(args.astrologer_id, args.name, args.language, args.expires_in_hours)
    print(token)
    print(f"\nWebview URL: http://localhost:5173/?token={token}", flush=True)


if __name__ == "__main__":
    main()
