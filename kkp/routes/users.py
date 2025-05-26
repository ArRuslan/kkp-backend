from datetime import datetime
from time import time

import bcrypt
from fastapi import APIRouter
from pytz import UTC

from kkp.config import config
from kkp.db.point import Point
from kkp.dependencies import JwtAuthUserDep, JwtSessionDep
from kkp.models import Media, User, UserProfilePhoto
from kkp.schemas.users import UserInfo, UserEditRequest, UserMfaEnableRequest, UserMfaDisableRequest, \
    RegisterDeviceRequest, UpdateLocationRequest, PasswordChangeRequest
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.mfa import Mfa

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
            await UserProfilePhoto.update_or_create(user=user, defaults={"photo": media})

    if update_data:
        await user.update_from_dict(update_data).save(update_fields=list(update_data.keys()))

    return await user.to_json()


@router.post("/mfa/enable", response_model=UserInfo)
async def enable_mfa(user: JwtAuthUserDep, data: UserMfaEnableRequest):
    if user.mfa_key is not None:
        raise CustomMessageException("Mfa already enabled.")
    if data.code not in Mfa.get_codes(data.key):
        raise CustomMessageException("Invalid code.")
    if not user.check_password(data.password):
        raise CustomMessageException("Wrong password!")

    user.mfa_key = data.key
    await user.save(update_fields=["mfa_key"])

    return await user.to_json()


@router.post("/mfa/disable", response_model=UserInfo)
async def disable_mfa(user: JwtAuthUserDep, data: UserMfaDisableRequest):
    if user.mfa_key is None:
        raise CustomMessageException("Mfa is not enabled.")
    if data.code not in Mfa.get_codes(user.mfa_key):
        raise CustomMessageException("Invalid code.")
    if not user.check_password(data.password):
        raise CustomMessageException("Wrong password!")

    user.mfa_key = None
    await user.save(update_fields=["mfa_key"])

    return await user.to_json()


@router.post("/register-device", status_code=204)
async def register_device_for_notifications(session: JwtSessionDep, data: RegisterDeviceRequest):
    session.fcm_token = data.fcm_token
    session.fcm_token_time = int(time())
    await session.save(update_fields=["fcm_token", "fcm_token_time"])


@router.post("/unregister-device", status_code=204)
async def unregister_device_for_notifications(session: JwtSessionDep):
    session.fcm_token = None
    session.fcm_token_time = 0
    await session.save(update_fields=["fcm_token", "fcm_token_time"])


@router.post("/location", status_code=204)
async def update_user_location(session: JwtSessionDep, data: UpdateLocationRequest):
    session.location = Point(data.longitude, data.latitude)
    session.location_time = datetime.now(UTC)
    await session.save(update_fields=["location", "location_time"])


@router.patch("/password", response_model=UserInfo)
async def change_user_password(user: JwtAuthUserDep, data: PasswordChangeRequest):
    if not user.check_password(data.old_password):
        raise CustomMessageException("Wrong password!")

    user.password = bcrypt.hashpw(data.new_password.encode("utf8"), bcrypt.gensalt(config.bcrypt_rounds)).decode("utf8")
    await user.save(update_fields=["password"])

    return await user.to_json()

