from fastapi import APIRouter

from kkp.dependencies import JwtAuthAdminDepN, AdminUserDep
from kkp.models import Media, User, UserProfilePhoto
from kkp.schemas.admin.users import AdminEditUserRequest
from kkp.schemas.common import PaginationResponse, PaginationQuery
from kkp.schemas.users import UserInfo
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/users", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[UserInfo])
async def get_users(query: PaginationQuery):
    return {
        "count": await User.all().count(),
        "result": [
            await user.to_json()
            for user in await User.all() \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{user_id}", response_model=UserInfo)
async def get_user(user: AdminUserDep):
    return await user.to_json()


@router.patch("/{user_id}", response_model=UserInfo)
async def edit_user(user: AdminUserDep, data: AdminEditUserRequest):
    if data.email:
        if await User.filter(id__not=user.id, email=data.email).exists():
            raise CustomMessageException("Email is already used by another user!")

    update_data = data.model_dump(exclude_defaults=True, exclude={"photo_id", "mfa_enabled"})
    if data.photo_id is not None:
        if data.photo_id == 0:
            await UserProfilePhoto.filter(user=user).delete()
        else:
            if (media := await Media.get_or_none(id=data.photo_id, uploaded_by=user)) is None:
                raise CustomMessageException("Media does not exist!")
            await UserProfilePhoto.update_or_create(user=user, defaults={"media": media})
    if data.disable_mfa:
        update_data["mfa_key"] = None
    if update_data:
        await user.update_from_dict(update_data).save(update_fields=list(update_data.keys()))

    return await user.to_json()


@router.delete("/{user_id}", status_code=204)
async def delete_user(user: AdminUserDep):
    await user.delete()