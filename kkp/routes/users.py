from fastapi import APIRouter

from kkp.dependencies import JwtAuthUserDep
from kkp.models import Media, User, UserProfilePhoto
from kkp.schemas.users import UserInfo, UserEditRequest
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/user")


@router.get("/info", response_model=UserInfo)
async def get_user_info(user: JwtAuthUserDep):
    return await user.to_json()


@router.patch("/info", response_model=UserInfo)
async def update_user_info(user: JwtAuthUserDep, data: UserEditRequest):
    if data.email:
        if await User.filter(id__not=user.id, email=data.email).exists():
            raise CustomMessageException("Email is already used by another user!")

    update_data = data.model_dump(exclude_defaults=True, exclude={"photo_id"})
    if data.photo_id is not None:
        if data.photo_id == 0:
            await UserProfilePhoto.filter(user=user).delete()
        else:
            if (media := await Media.get_or_none(id=data.photo_id, uploaded_by=user)) is None:
                raise CustomMessageException("Media does not exist!")
            await UserProfilePhoto.update_or_create(user=user, defaults={"media": media})
    if update_data:
        await user.update_from_dict(update_data).save(update_fields=list(update_data.keys()))

    return await user.to_json()