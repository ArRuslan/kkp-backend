from typing import TypedDict

from httpx import AsyncClient

from kkp.config import config
from kkp.utils.custom_exception import CustomMessageException

GOOGLE_TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"


class GoogleOAuthResponse(TypedDict):
    id: str
    email: str
    given_name: str
    family_name: str


class GoogleOAuthToken(TypedDict):
    access_token: str
    refresh_token: str
    expires_in: int


async def authorize_google(code: str) -> tuple[GoogleOAuthResponse, GoogleOAuthToken]:
    data = {
        "code": code,
        "client_id": config.oauth_google_client_id,
        "client_secret": config.oauth_google_client_secret,
        "redirect_uri": config.oauth_google_redirect,
        "grant_type": "authorization_code",
    }

    async with AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, json=data)
        if "error" in resp.json():
            raise CustomMessageException(f"Error: {resp.json()['error']}")
        token_data = resp.json()

        info_resp = await client.get(GOOGLE_USERINFO_URL,
                                     headers={"Authorization": f"Bearer {token_data['access_token']}"})
        return info_resp.json(), token_data