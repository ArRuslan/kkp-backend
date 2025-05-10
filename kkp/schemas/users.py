from pydantic import BaseModel, EmailStr, Field

from kkp.models import UserRole
from kkp.schemas.media import MediaInfo


class UserInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    role: UserRole
    mfa_enabled: bool
    photo: MediaInfo | None


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
