"""File storage for astrologer-shared photos/videos (screenshots, profile
photos, ticket attachments). Two backends, switched by settings.UPLOADS_BACKEND
— "local" (default, disk — see app/core/uploads.py, lost on redeploy/restart/
scale-out) or "s3" (real, durable across all of those). Nothing outside this
module and the upload route needs to know which one is active; both return a
plain public URL string.

S3 public-read must come from a BUCKET POLICY, not a per-object ACL — most
buckets created since ~2023 default to "ACL disabled" (Object Ownership:
Bucket owner enforced), and passing ACL="public-read" to put_object on one of
those fails outright. Whoever provisions the bucket needs to attach a policy
allowing s3:GetObject to "*" (or however open you want it) — this module
deliberately doesn't try to set an ACL at all, so it works on both old- and
new-style buckets.
"""

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.uploads import UPLOAD_DIR


def upload_file(filename: str, content: bytes, content_type: str) -> str:
    """Stores the file, returns its public URL.

    Raises on failure — unlike the Slack photo push (best-effort, never
    blocks ticket creation), a failed upload here means the astrologer
    genuinely has no attachment to send yet, so the caller (POST
    /api/uploads) must surface a real error rather than silently continuing
    as if a file existed.
    """
    if settings.UPLOADS_BACKEND == "s3":
        return _upload_to_s3(filename, content, content_type)
    return _upload_to_local_disk(filename, content)


def _upload_to_local_disk(filename: str, content: bytes) -> str:
    (UPLOAD_DIR / filename).write_bytes(content)
    return f"{settings.PUBLIC_BASE_URL}/uploads/{filename}"


def _s3_client():
    # Built fresh per call (cheap — no network round trip happens until an
    # actual API call), not cached at module scope, so tests that monkeypatch
    # settings per-test never see a stale client from an earlier one.
    return boto3.client(
        "s3",
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _upload_to_s3(filename: str, content: bytes, content_type: str) -> str:
    key = f"uploads/{filename}"
    try:
        _s3_client().put_object(
            Bucket=settings.S3_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=content_type,
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 upload failed: {exc}") from exc
    return f"https://{settings.S3_BUCKET_NAME}.s3.{settings.S3_REGION}.amazonaws.com/{key}"
