from pydantic import BaseModel, Field
from pydantic_extra_types.phone_numbers import PhoneNumber

from kkp.models import VolRequestStatus
from kkp.models.volunteer_request import VolAvailability, VolHelp
from kkp.schemas.media import MediaInfo
from kkp.schemas.users import UserBaseInfo


PhoneNumber.phone_format = "E164"


class VolunteerRequestInfo(BaseModel):
    id: int
    user: UserBaseInfo
    created_at: int
    reviewed_at: int
    text: str
    review_text: str
    medias: list[MediaInfo]
    status: VolRequestStatus
    full_name: str
    has_vehicle: bool
    phone_number: PhoneNumber
    city: str
    availability: VolAvailability
    help: VolHelp
    telegram_username: str | None
    viber_phone: PhoneNumber | None
    whatsapp_phone: PhoneNumber | None


class CreateVolunteerRequest(BaseModel):
    full_name: str
    text: str
    media_ids: list[int] = Field(max_length=15)
    has_vehicle: bool
    phone_number: PhoneNumber
    city: str
    availability: VolAvailability
    help: VolHelp
    telegram_username: str | None = None
    viber_phone: PhoneNumber | None = None
    whatsapp_phone: PhoneNumber | None = None
