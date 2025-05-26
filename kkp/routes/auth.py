from os import urandom
from time import time

import bcrypt
from fastapi import APIRouter
from starlette.responses import JSONResponse

from kkp.config import config
from kkp.dependencies import JwtSessionDep, JwtAuthUserDep
from kkp.models import User, Session, ExternalAuth, ExtAuthType
from kkp.schemas.auth import RegisterResponse, RegisterRequest, LoginResponse, LoginRequest, MfaResponse, \
    MfaVerifyRequest, GoogleAuthUrlData, ConnectGoogleData, GoogleOAuthData, ResetPasswordRequest, \
    RealResetPasswordRequest, GoogleIdOAuthData, GoogleClientIdData
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.google_id_token import verify_oauth2_token
from kkp.utils.google_oauth import authorize_google
from kkp.utils.jwt import JWT
from kkp.utils.mfa import Mfa
from kkp.utils.notification_util import send_notification

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
            }, config.jwt_key, expires_in=mfa_ttl),
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
    if (payload := JWT.decode(data.mfa_token, config.jwt_key)) is None:
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
        "expires_at": int(time() + config.jwt_ttl),
    }


@router.get("/google", response_model=GoogleAuthUrlData)
async def google_auth_link():
    return {
        "url": (
            f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={config.oauth_google_client_id}"
            f"&redirect_uri={config.oauth_google_redirect}&scope=profile%20email&access_type=offline"
        ),
    }



@router.get("/google/mobile", response_model=GoogleClientIdData)
async def google_auth_mobile_client_id():
    return {
        "client_id": config.oauth_google_client_id,
    }


@router.post("/google/connect", response_model=GoogleAuthUrlData)
async def google_auth_connect_link(user: JwtAuthUserDep):
    if await ExternalAuth.filter(user=user).exists():
        raise CustomMessageException("You already have connected google account.")

    state = JWT.encode({"user_id": user.id, "type": "google-connect"}, config.jwt_key, expires_in=180)
    return {
        "url": (
            f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={config.oauth_google_client_id}"
            f"&redirect_uri={config.oauth_google_redirect}&scope=profile%20email&access_type=offline&state={state}"
        ),
    }


@router.post("/google/callback", response_model=ConnectGoogleData)
async def google_auth_callback(data: GoogleOAuthData):
    state = JWT.decode(data.state or "", config.jwt_key)
    if state is not None and state.get("type") != "google-connect":
        state = None

    data, token_data = await authorize_google(data.code)
    existing_auth = await ExternalAuth.get_or_none(type=ExtAuthType.GOOGLE, external_id=data["id"]).select_related("user")
    if existing_auth is not None:
        existing_auth.access_token = token_data["access_token"]
        existing_auth.refresh_token = token_data.get("refresh_token", "")
        existing_auth.token_expires_at = int(time() + token_data["expires_in"])
        await existing_auth.save(update_fields=["access_token", "refresh_token", "token_expires_at"])

    user = None
    if state is not None and existing_auth is None:
        # Connect external service to a user account
        if await ExternalAuth.filter(user__id=state["user_id"]).exists():
            raise CustomMessageException("This google account is already connected to an account.")

        await ExternalAuth.create(
            user=await User.get(id=state["user_id"]),
            type="google",
            external_id=data["id"],
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            token_expires_at=int(time() + token_data["expires_in"]),
        )
    elif state is not None and existing_auth is not None:
        # Trying to connect an external account that is already connected, ERROR!!
        raise CustomMessageException("This google account is already connected to an account.")
    elif state is None and existing_auth is None:
        user = await User.get_or_none(email=data["email"])
        if user is None:
            user = await User.create(
                email=data["email"],
                first_name=data["given_name"],
                last_name=data["family_name"],
            )
        await ExternalAuth.create(
            user=user,
            type=ExtAuthType.GOOGLE,
            external_id=data["id"],
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            token_expires_at=int(time() + token_data["expires_in"]),
        )
    elif state is None and existing_auth is not None:
        # Authorize user
        user = existing_auth.user
    else:
        raise RuntimeError("Unreachable")

    if user is None:
        return {"token": None, "expires_at": 0, "connect": True}

    session = await Session.create(user=user, active=True)
    return {
        "token": session.to_jwt(),
        "expires_at": int(time() + config.jwt_ttl),
        "connect": False,
    }


@router.post("/google/mobile-callback", response_model=LoginResponse)
async def google_auth_mobile_callback(data: GoogleIdOAuthData):
    try:
        id_info = await verify_oauth2_token(data.id_token, config.oauth_google_client_id)
    except ValueError:
        raise CustomMessageException("Failed to verify token.")

    existing_auth = await ExternalAuth.get_or_none(type=ExtAuthType.GOOGLE, external_id=id_info["sub"]).select_related("user")
    if existing_auth is not None:
        existing_auth.access_token = "id"
        existing_auth.refresh_token = "id"
        existing_auth.token_expires_at = 0
        await existing_auth.save(update_fields=["access_token", "refresh_token", "token_expires_at"])

    if existing_auth is None:
        user = await User.get_or_none(email=id_info["email"])
        if user is None:
            user = await User.create(
                email=id_info["email"],
                first_name=id_info["given_name"],
                last_name=id_info["family_name"],
            )
        await ExternalAuth.create(
            user=user,
            type=ExtAuthType.GOOGLE,
            external_id=id_info["sub"],
            access_token="id",
            refresh_token="id",
            token_expires_at=0,
        )
    elif existing_auth is not None:
        # Authorize user
        user = existing_auth.user
    else:
        raise RuntimeError("Unreachable")

    session = await Session.create(user=user, active=True)
    return {
        "token": session.to_jwt(),
        "expires_at": int(time() + config.jwt_ttl),
    }


@router.post("/reset-password/request", status_code=204)
async def request_reset_password(data: ResetPasswordRequest):
    if (user := await User.get_or_none(email=data.email)) is None:
        return

    if config.SMTP_PORT <= 0:
        raise CustomMessageException("Smtp is not configured!")

    reset_token = JWT.encode({"u": user.id, "type": "password-reset"}, config.JWT_KEY, expires_in=60 * 30)

    await send_notification(
        user,
        "Password reset",
        (
            f"Click the following link to reset your password: "
            f"{config.public_host}/reset-password?reset_token={reset_token}"
        ),
        fcm=False,
    )


@router.post("/reset-password/reset", status_code=204)
async def reset_password(data: RealResetPasswordRequest):
    if (payload := JWT.decode(data.reset_token, config.JWT_KEY)) is None or payload.get("type") != "password-reset":
        raise CustomMessageException("Password reset request is invalid!")
    if (user := await User.get_or_none(id=payload["u"])) is None:
        raise CustomMessageException("User not found!")

    user.password = bcrypt.hashpw(data.new_password.encode("utf8"), bcrypt.gensalt(config.bcrypt_rounds)).decode("utf8")
    await user.save(update_fields=["password"])
