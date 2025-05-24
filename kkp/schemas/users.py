from pydantic import BaseModel, EmailStr, Field

from kkp.models import UserRole
from kkp.schemas.media import MediaInfo


class UserBaseInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    photo: MediaInfo | None


class UserInfo(UserBaseInfo):
    email: EmailStr
    role: UserRole
    mfa_enabled: bool


class UserEditRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    photo_id: int | None = None


class UserMfaEnableRequest(BaseModel):
    password: str
    key: str = Field(min_length=16, max_length=16, pattern=r'^[A-Z2-7]{16}$')
    code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')


class UserMfaDisableRequest(BaseModel):
    password: str
    code: str = Field(min_length=6, max_length=6, pattern=r'^\d{6}$')


class RegisterDeviceRequest(BaseModel):
    fcm_token: str


class UpdateLocationRequest(BaseModel):
    latitude: float
    longitude: float


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
