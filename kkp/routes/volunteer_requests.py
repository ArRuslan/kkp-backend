from fastapi import APIRouter

from kkp.dependencies import JwtAuthUserDep
from kkp.models import Media, VolunteerRequest, VolRequestStatus, UserRole, MediaStatus
from kkp.schemas.volunteer_requests import VolunteerRequestInfo, CreateVolunteerRequest
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/volunteer-requests")


@router.get("", response_model=list[VolunteerRequestInfo])
async def get_volunteer_requests(user: JwtAuthUserDep):
    return [
        await vol_request.to_json()
        for vol_request in await VolunteerRequest.filter(user=user).order_by("-id")
    ]


@router.post("", response_model=VolunteerRequestInfo)
async def create_volunteer_requests(user: JwtAuthUserDep, data: CreateVolunteerRequest):
    if user.role >= UserRole.VOLUNTEER:
        raise CustomMessageException("Your role is already volunteer or higher", 400)
    if await VolunteerRequest.filter(user=user).count() > 10:
        raise CustomMessageException("You cannot request volunteer status more that 10 times", 400)
    if await VolunteerRequest.filter(user=user, status=VolRequestStatus.REQUESTED).exists():
        raise CustomMessageException("You already have requested volunteer status", 400)

    medias = await Media.filter(uploaded_by=user, id__in=data.media_ids, status=MediaStatus.UPLOADED)
    vol_request = await VolunteerRequest.create(
        user=user,
        text=data.text,
        full_name=data.full_name,
        has_vehicle=data.has_vehicle,
        phone_number=data.phone_number,
        city=data.city,
        availability=data.availability,
        help=data.help,
        telegram_username=data.telegram_username,
        viber_phone=data.viber_phone,
        whatsapp_phone=data.whatsapp_phone,
    )
    await vol_request.medias.add(*medias)

    return await vol_request.to_json()
