from fastapi import APIRouter

from kkp.dependencies import JwtAuthUserDep
from kkp.models import Media, VolunteerRequest, VolRequestStatus, UserRole
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
        raise CustomMessageException("You cannot request volunteer status moore that 10 times", 400)
    if await VolunteerRequest.filter(user=user, status=VolRequestStatus.REQUESTED).exists():
        raise CustomMessageException("You already have requested volunteer status", 400)

    medias = await Media.filter(uploaded_by=user, id__in=data.media_ids)
    vol_request = await VolunteerRequest.create(user=user, text=data.text)
    await vol_request.medias.add(*medias)

    return await vol_request.to_json()
