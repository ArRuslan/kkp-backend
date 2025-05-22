from pydantic import BaseModel, EmailStr, Field

from kkp.config import config
from kkp.models.user import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    if config.is_debug:
        role: UserRole = UserRole.REGULAR


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    token: str
    expires_at: int


class LoginResponse(RegisterResponse):
    ...


class MfaResponse(BaseModel):
    mfa_token: str
    expires_at: int


class MfaVerifyRequest(BaseModel):
    mfa_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
    mfa_token: str


class GoogleOAuthData(BaseModel):
    code: str
    state: str | None = None


class GoogleIdOAuthData(BaseModel):
    id_token: str


class GoogleAuthUrlData(BaseModel):
    url: str


class ConnectGoogleData(LoginResponse):
    token: str | None
    connect: bool


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class RealResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str