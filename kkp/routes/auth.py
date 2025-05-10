from os import urandom
from time import time

import bcrypt
from fastapi import APIRouter
from starlette.responses import JSONResponse

from kkp.config import config
from kkp.dependencies import JwtSessionDep
from kkp.models import User, Session
from kkp.schemas.auth import RegisterResponse, RegisterRequest, LoginResponse, LoginRequest, MfaResponse, \
    MfaVerifyRequest
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.jwt import JWT
from kkp.utils.mfa import Mfa

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


@router.post("/login", response_model=LoginResponse | MfaResponse)
async def login(data: LoginRequest):
    if (user := await User.get_or_none(email=data.email)) is None:
        raise CustomMessageException("User with this credentials is not found!")

    if not user.check_password(data.password):
        raise CustomMessageException("User with this credentials is not found!")

    session = await Session.create(user=user, active=user.mfa_key is None)
    if user.mfa_key is not None:
        mfa_ttl = 30 * 60
        return JSONResponse({
            "mfa_token": JWT.encode({
                "s": session.id,
                "u": user.id,
                "n": session.nonce[:8],
            }, config.JWT_KEY, expires_in=mfa_ttl),
            "expires_at": int(time() + mfa_ttl),
        }, 400)

    return {
        "token": session.to_jwt(),
        "expires_at": int(time() + config.jwt_ttl),
    }


@router.post("/logout", status_code=204)
async def logout_user(session: JwtSessionDep):
    await session.delete()


@router.post("/login/mfa", response_model=LoginResponse)
async def verify_mfa_login(data: MfaVerifyRequest):
    if (payload := JWT.decode(data.mfa_token, config.JWT_KEY)) is None:
        raise CustomMessageException("Invalid mfa token!")

    session = await Session.get_or_none(
        id=payload["s"], user__id=payload["u"], nonce__startswith=payload["n"], active=False,
    ).select_related("user")
    if session is None:
        raise CustomMessageException("Invalid mfa token!")

    if session.user.mfa_key is not None and data.mfa_code not in Mfa.get_codes(session.user.mfa_key):
        raise CustomMessageException("Invalid code.")

    session.nonce = urandom(8).hex()
    session.active = True
    await session.save(update_fields=["nonce", "active"])

    return {
        "token": session.to_jwt(),
        "expires_at": int(time() + config.AUTH_JWT_TTL),
    }
