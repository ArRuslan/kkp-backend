from fastapi import APIRouter, Query

from kkp.dependencies import JwtAuthAdminDepN, AdminUserDep
from kkp.models import Media, User, UserProfilePhoto, MediaStatus
from kkp.schemas.admin.users import AdminEditUserRequest, UsersQuery
from kkp.schemas.common import PaginationResponse
from kkp.schemas.users import UserInfo
from kkp.utils.cache import Cache
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/users", dependencies=[JwtAuthAdminDepN])


@router.get("", response_model=PaginationResponse[UserInfo])
async def get_users(query: UsersQuery = Query()):
    users_query = User.filter()

    if query.id is not None:
        users_query = users_query.filter(id=query.id)
    if query.role is not None:
        users_query = users_query.filter(role=query.role)
    if query.has_mfa is not None:
        users_query = users_query.filter(mfa_key__not_isnull=query.has_mfa)

    order = query.order_by
    if query.order == "desc":
        order = f"-{order}"

    users_query = users_query.order_by(order)

    Cache.disable()
    return {
        "count": await users_query.count(),
        "result": [
            await user.to_json()
            for user in await users_query \
                .limit(query.page_size) \
                .offset(query.page_size * (query.page - 1))
        ],
    }


@router.get("/{user_id}", response_model=UserInfo)
async def get_user(user: AdminUserDep):
    Cache.disable()
    return await user.to_json()


@router.patch("/{user_id}", response_model=UserInfo)
async def edit_user(user: AdminUserDep, data: AdminEditUserRequest):
    if data.email:
        if await User.filter(id__not=user.id, email=data.email).exists():
            raise CustomMessageException("Email is already used by another user!")

    update_data = data.model_dump(exclude_defaults=True, exclude={"photo_id", "disable_mfa"})
    if data.photo_id is not None:
        if data.photo_id == 0:
            await UserProfilePhoto.filter(user=user).delete()
            await Cache.delete_obj(user)
        else:
            if (media := await Media.get_or_none(id=data.photo_id, status=MediaStatus.UPLOADED)) is None:
                raise CustomMessageException("Media does not exist!")
            await UserProfilePhoto.update_or_create(user=user, defaults={"media": media})
            await Cache.delete_obj(user)
    if data.disable_mfa:
        update_data["mfa_key"] = None

    if update_data:
        await user.update_from_dict(update_data).save(update_fields=list(update_data.keys()))
        await Cache.delete_obj(user)

    return await user.to_json()


@router.delete("/{user_id}", status_code=204)
async def delete_user(user: AdminUserDep):
    await Cache.delete_obj(user)
    await user.delete()