from pydantic import BaseModel, EmailStr


class VerifyResponse(BaseModel):
    astrologer_id: int
    name: str
    language: str


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginResponse(BaseModel):
    access_token: str
    admin_id: int
    name: str
    email: str


class AdminMeResponse(BaseModel):
    admin_id: int
    email: str
