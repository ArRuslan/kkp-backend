from os import urandom
from time import time

import bcrypt
from fastapi import APIRouter
from starlette.responses import JSONResponse

from kkp.config import config
from kkp.dependencies import JwtSessionDep, JwtAuthUserDep
from kkp.models import User, Session, ExternalAuth, ExtAuthType
from kkp.schemas.auth import RegisterResponse, RegisterRequest, LoginResponse, LoginRequest, MfaResponse, \
    MfaVerifyRequest, GoogleAuthUrlData, ConnectGoogleData, GoogleOAuthData
from kkp.utils.custom_exception import CustomMessageException
from kkp.utils.google_oauth import authorize_google
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


@router.get("/google", response_model=GoogleAuthUrlData)
async def google_auth_link():
    return {
        "url": (
            f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={config.OAUTH_GOOGLE_CLIENT_ID}"
            f"&redirect_uri={config.OAUTH_GOOGLE_REDIRECT}&scope=profile%20email&access_type=offline"
        ),
    }


@router.post("/google/connect", response_model=GoogleAuthUrlData)
async def google_auth_connect_link(user: JwtAuthUserDep):
    if await ExternalAuth.filter(user=user).exists():
        raise CustomMessageException("You already have connected google account.")

    state = JWT.encode({"user_id": user.id, "type": "google-connect"}, config.JWT_KEY, expires_in=180)
    return {
        "url": (
            f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={config.OAUTH_GOOGLE_CLIENT_ID}"
            f"&redirect_uri={config.OAUTH_GOOGLE_REDIRECT}&scope=profile%20email&access_type=offline&state={state}"
        ),
    }


@router.post("/google/callback", response_model=ConnectGoogleData)
async def google_auth_callback(data: GoogleOAuthData):
    state = JWT.decode(data.state or "", config.JWT_KEY)
    if state is not None and state.get("type") != "google-connect":
        state = None

    data, token_data = await authorize_google(data.code)
    existing_auth = await ExternalAuth.get_or_none(type=ExtAuthType.GOOGLE, external_id=data["id"]).select_related("user")
    if existing_auth is not None:
        existing_auth.access_token = token_data["access_token"]
        existing_auth.refresh_token = token_data["refresh_token"]
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
            refresh_token=token_data["refresh_token"],
            expires_at=int(time() + token_data["expires_in"]),
        )
    elif state is not None and existing_auth is not None:
        # Trying to connect an external account that is already connected, ERROR!!
        raise CustomMessageException("This google account is already connected to an account.")
    elif state is None and existing_auth is None:
        # Register new user
        user = await User.create(first_name=data["given_name"], last_name=data["family_name"])
        await ExternalAuth.create(
            user=user,
            type="google",
            external_id=data["id"],
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            expires_at=int(time() + token_data["expires_in"]),
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
    }