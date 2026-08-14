from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_db
from app.core.security import AdminContext
from app.schemas.auth import AdminLoginRequest, AdminLoginResponse, AdminMeResponse
from app.services import auth_service

router = APIRouter(tags=["admin"])


@router.post("/api/admin/login", response_model=AdminLoginResponse)
def login(body: AdminLoginRequest, db: Session = Depends(get_db)) -> AdminLoginResponse:
    result = auth_service.login_admin(db, body.email, body.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    admin, token = result
    return AdminLoginResponse(access_token=token, admin_id=admin.id, name=admin.name, email=admin.email)


@router.get("/api/admin/me", response_model=AdminMeResponse)
def me(admin: AdminContext = Depends(get_current_admin)) -> AdminMeResponse:
    return AdminMeResponse(admin_id=admin.admin_id, email=admin.email, access_level=admin.access_level)
