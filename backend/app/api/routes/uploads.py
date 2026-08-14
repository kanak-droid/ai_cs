import mimetypes
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.deps import get_current_astrologer
from app.core.security import AstrologerContext
from app.integrations import object_storage

router = APIRouter(tags=["uploads"])

MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_CONTENT_PREFIXES = ("image/", "video/")


@router.post("/api/uploads")
async def upload_attachment(
    file: UploadFile,
    astrologer: AstrologerContext = Depends(get_current_astrologer),
) -> dict:
    if not file.content_type or not file.content_type.startswith(ALLOWED_CONTENT_PREFIXES):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only images or videos can be uploaded.")

    body = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "File is too large (max 15MB).")

    extension = mimetypes.guess_extension(file.content_type) or ""
    filename = f"{uuid.uuid4().hex}{extension}"
    url = object_storage.upload_file(filename, body, file.content_type)

    return {"url": url}
