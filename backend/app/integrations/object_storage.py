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

import mimetypes

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
    key = f"{settings.S3_KEY_PREFIX}{filename}"
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


def generate_preview_url(url: str, expires_in: int = 3600) -> str:
    """A short-lived, signed URL the browser can load directly — a plain
    <img src>/<a href download>, no Authorization header needed, since the
    signature itself (computed here from our own AWS credentials/IAM role)
    is what proves access, and it's never exposed to the browser. This is
    what actually solves the admin dashboard's attachment preview: the
    object's real https://{bucket}.s3.../{key} URL 403s on a plain
    unauthenticated GET unless the bucket has a public-read policy attached
    — signing it here works regardless (per tech team guidance, 2026-08-18).

    Local-disk URLs are already directly servable by our own static mount
    (no S3, nothing to sign), so they're returned unchanged.
    """
    if settings.UPLOADS_BACKEND == "s3":
        key = _s3_key_from_url(url)
        return _s3_client().generate_presigned_url(
            "get_object", Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key}, ExpiresIn=expires_in
        )
    return url


def download_file(url: str) -> tuple[bytes, str]:
    """Fetches a previously-uploaded file's actual bytes, server-side —
    for anything that needs the real content (pushing it into Slack,
    proxying it to the admin dashboard), not just a URL for someone else's
    browser to load directly.

    For S3, this uses our own AWS credentials via get_object, which reads a
    private object just fine regardless of the bucket's public-read policy
    — unlike a plain unauthenticated GET against the object's URL (what a
    browser's <img src> or a raw httpx.get does), which 403s until that
    policy is attached. Returns (content, content_type).
    """
    if settings.UPLOADS_BACKEND == "s3":
        return _download_from_s3(url)
    return _download_from_local_disk(url)


def _s3_key_from_url(url: str) -> str:
    prefix = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.S3_REGION}.amazonaws.com/"
    if not url.startswith(prefix):
        raise ValueError(f"Not an S3 URL for the configured bucket: {url}")
    return url[len(prefix):]


def _download_from_s3(url: str) -> tuple[bytes, str]:
    key = _s3_key_from_url(url)
    try:
        response = _s3_client().get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"S3 download failed: {exc}") from exc
    content_type = response.get("ContentType") or "application/octet-stream"
    return response["Body"].read(), content_type


def _download_from_local_disk(url: str) -> tuple[bytes, str]:
    filename = url.rsplit("/", 1)[-1]
    content_type, _ = mimetypes.guess_type(filename)
    return (UPLOAD_DIR / filename).read_bytes(), content_type or "application/octet-stream"
