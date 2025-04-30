from time import time

import bcrypt
from fastapi import APIRouter

from kkp.config import config
from kkp.models import User, Session
from kkp.schemas.auth import RegisterResponse, RegisterRequest, LoginResponse, LoginRequest
from kkp.utils.custom_exception import CustomMessageException

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=RegisterResponse)
async def register(data: RegisterRequest):
    if await User.filter(email=data.email).exists():
        raise CustomMessageException("User with this email already registered!")

    password = bcrypt.hashpw(data.password.encode("utf8"), bcrypt.gensalt(config.bcrypt_rounds)).decode("utf8")
    user = await User.create(
        email=data.email,
        password=password,
        first_name=data.first_name,
        last_name=data.last_name,
    )
    if config.is_debug:
        user.role = data.role
        await user.save(update_fields=["role"])
    session = await Session.create(user=user)

    return {
        "token": session.to_jwt(),
        "expires_at": int(time() + config.jwt_ttl),
    }


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest):
    if (user := await User.get_or_none(email=data.email)) is None:
        raise CustomMessageException("User with this credentials is not found!")

    if not user.check_password(data.password):
        raise CustomMessageException("User with this credentials is not found!")

    session = await Session.create(user=user)
    return {
        "token": session.to_jwt(),
        "expires_at": int(time() + config.jwt_ttl),
    }


# TODO: add logout