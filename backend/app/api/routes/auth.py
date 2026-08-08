from fastapi import APIRouter, Depends

from app.api.deps import get_current_astrologer
from app.core.security import AstrologerContext
from app.schemas.auth import VerifyResponse

router = APIRouter(tags=["auth"])


@router.get("/api/auth/verify", response_model=VerifyResponse)
def verify(astrologer: AstrologerContext = Depends(get_current_astrologer)) -> VerifyResponse:
    # If get_current_astrologer didn't raise 401, the token is valid — by construction.
    return VerifyResponse(
        astrologer_id=astrologer.astrologer_id,
        name=astrologer.name,
        language=astrologer.language,
    )
