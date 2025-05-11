from pydantic import BaseModel, EmailStr


class AdminEditUserRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    photo_id: int | None = None
    disable_mfa: bool | None = None