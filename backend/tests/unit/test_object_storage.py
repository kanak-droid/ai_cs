import pytest
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.uploads import UPLOAD_DIR
from app.integrations import object_storage


class _FakeS3Body:
    def __init__(self, content: bytes):
        self._content = content

    def read(self) -> bytes:
        return self._content


class _FakeS3Client:
    def __init__(
        self,
        error: Exception | None = None,
        get_object_result: dict | None = None,
        presigned_url: str = "https://signed.example/x",
    ):
        self.error = error
        self.calls = []
        self._get_object_result = get_object_result
        self._presigned_url = presigned_url

    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error

    def get_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self._get_object_result

    def generate_presigned_url(self, client_method, **kwargs):
        self.calls.append({"client_method": client_method, **kwargs})
        if self.error:
            raise self.error
        return self._presigned_url


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


def test_local_preview_url_is_returned_unchanged(monkeypatch):
    # Already directly servable by our own static mount — nothing to sign.
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "local")

    url = object_storage.generate_preview_url("http://localhost:8000/uploads/photo.jpg")

    assert url == "http://localhost:8000/uploads/photo.jpg"


def test_s3_preview_url_is_signed_with_our_own_credentials(monkeypatch):
    # The point: this never exposes AWS credentials to the browser — the
    # signature is computed here, server-side, and the resulting URL is
    # what's safe to hand to the browser directly (per tech team guidance,
    # 2026-08-18) — an <img src> pointed at the raw object URL 403s without
    # a public-read bucket policy, but a signed URL works regardless.
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    fake_client = _FakeS3Client(presigned_url="https://astrohelp-test-bucket.s3.../signed")
    monkeypatch.setattr(object_storage, "_s3_client", lambda: fake_client)

    url = object_storage.generate_preview_url(
        "https://astrohelp-test-bucket.s3.ap-south-1.amazonaws.com/supply-issues/photo.jpg"
    )

    assert url == "https://astrohelp-test-bucket.s3.../signed"
    call = fake_client.calls[0]
    assert call["client_method"] == "get_object"
    assert call["Params"] == {"Bucket": "astrohelp-test-bucket", "Key": "supply-issues/photo.jpg"}
    assert call["ExpiresIn"] == 3600


def test_local_download_reads_the_file_back_with_a_guessed_content_type(monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "local")
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "http://localhost:8000")
    url = object_storage.upload_file("readback.png", b"pixels", "image/png")

    content, content_type = object_storage.download_file(url)

    assert content == b"pixels"
    assert content_type == "image/png"
    (UPLOAD_DIR / "readback.png").unlink()


def test_s3_download_uses_our_own_credentials_not_a_public_url(monkeypatch):
    # The whole point: get_object works with our AWS credentials regardless
    # of whether the bucket has a public-read policy — unlike a plain GET
    # against the object's URL, which 403s without one (confirmed live
    # 2026-08-18, both for the admin dashboard's <img> and Slack's fetch).
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    fake_client = _FakeS3Client(
        get_object_result={"Body": _FakeS3Body(b"real-bytes"), "ContentType": "image/jpeg"}
    )
    monkeypatch.setattr(object_storage, "_s3_client", lambda: fake_client)

    content, content_type = object_storage.download_file(
        "https://astrohelp-test-bucket.s3.ap-south-1.amazonaws.com/supply-issues/photo.jpg"
    )

    assert content == b"real-bytes"
    assert content_type == "image/jpeg"
    assert fake_client.calls[0]["Bucket"] == "astrohelp-test-bucket"
    assert fake_client.calls[0]["Key"] == "supply-issues/photo.jpg"


def test_s3_download_falls_back_to_a_generic_content_type_when_s3_has_none(monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    fake_client = _FakeS3Client(get_object_result={"Body": _FakeS3Body(b"bytes")})
    monkeypatch.setattr(object_storage, "_s3_client", lambda: fake_client)

    _content, content_type = object_storage.download_file(
        "https://astrohelp-test-bucket.s3.ap-south-1.amazonaws.com/supply-issues/photo.jpg"
    )

    assert content_type == "application/octet-stream"


def test_s3_download_rejects_a_url_for_a_different_bucket(monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    with pytest.raises(ValueError):
        object_storage.download_file("https://someone-elses-bucket.s3.us-east-1.amazonaws.com/x.jpg")


def test_s3_download_failure_raises(monkeypatch):
    monkeypatch.setattr(settings, "UPLOADS_BACKEND", "s3")
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "astrohelp-test-bucket")
    monkeypatch.setattr(settings, "S3_REGION", "ap-south-1")

    error = ClientError({"Error": {"Code": "AccessDenied", "Message": "nope"}}, "GetObject")
    monkeypatch.setattr(object_storage, "_s3_client", lambda: _FakeS3Client(error=error))

    with pytest.raises(RuntimeError):
        object_storage.download_file(
            "https://astrohelp-test-bucket.s3.ap-south-1.amazonaws.com/supply-issues/photo.jpg"
        )
