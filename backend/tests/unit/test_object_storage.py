import pytest
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.uploads import UPLOAD_DIR
from app.integrations import object_storage


class _FakeS3Client:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = []

    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error


def test_local_backend_is_the_default(monkeypatch):
    assert settings.UPLOADS_BACKEND == "local"


def test_local_upload_writes_the_file_and_returns_its_url(monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "local")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "http://localhost:8000")

    url = object_storage.upload_file("test-file.jpg", b"hello", "image/jpeg")

    assert url == "http://localhost:8000/uploads/test-file.jpg"
    written = UPLOAD_DIR / "test-file.jpg"
    assert written.read_bytes() == b"hello"
    written.unlink()


def test_s3_upload_never_touches_the_real_network(monkeypatch):
    # No mock here beyond swapping the client factory — this test's whole
    # point is proving upload_file("s3", ...) can't reach real AWS.
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    fake_client = _FakeS3Client()
    monkeypatch.setattr(object_storage, "_s3_client", lambda: fake_client)

    url = object_storage.upload_file("photo.jpg", b"bytes", "image/jpeg")

    assert url == "https://astrohelp-test-bucket.s3.ap-south-1.amazonaws.com/uploads/photo.jpg"
    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["Bucket"] == "astrohelp-test-bucket"
    assert call["Key"] == "uploads/photo.jpg"
    assert call["Body"] == b"bytes"
    assert call["ContentType"] == "image/jpeg"
    # Deliberately no ACL param — most buckets now default to ACLs disabled;
    # public-read must come from a bucket policy, not per-object ACLs.
    assert "ACL" not in call


def test_s3_upload_uses_the_configured_key_prefix(monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")
    monkeypatch.setattr(settings, "S3_KEY_PREFIX", "supply-issues/")

    fake_client = _FakeS3Client()
    monkeypatch.setattr(object_storage, "_s3_client", lambda: fake_client)

    url = object_storage.upload_file("photo.jpg", b"bytes", "image/jpeg")

    assert url == "https://astrohelp-test-bucket.s3.ap-south-1.amazonaws.com/supply-issues/photo.jpg"
    assert fake_client.calls[0]["Key"] == "supply-issues/photo.jpg"


def test_s3_upload_failure_raises_rather_than_silently_continuing(monkeypatch):
    # Unlike the Slack photo push (best-effort), a failed upload here means
    # the astrologer has no attachment at all — the caller must see a real
    # error, not a URL pointing at nothing.
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    error = ClientError({"Error": {"Code": "AccessDenied", "Message": "nope"}}, "PutObject")
    monkeypatch.setattr(object_storage, "_s3_client", lambda: _FakeS3Client(error=error))

    with pytest.raises(RuntimeError):
        object_storage.upload_file("photo.jpg", b"bytes", "image/jpeg")
