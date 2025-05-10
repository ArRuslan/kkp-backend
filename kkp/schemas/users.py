from pydantic import BaseModel, EmailStr

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
