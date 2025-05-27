import json
import re
from base64 import urlsafe_b64encode
from os import urandom

from httpx import Request, Response

from kkp.config import config
from kkp.utils.google_oauth import GoogleOAuthResponse


class GoogleMockState:
    CAPTURE_RE = re.compile(r".+/v2/checkout/orders/\d+\.\d+/capture")

    def __init__(self, client_id: str = config.oauth_google_client_id, client_secret: str = config.oauth_google_client_secret, redirect_uri: str = config.oauth_google_redirect) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._users: dict[str, GoogleOAuthResponse] = {}
        self._codes: dict[str, str] = {}
        self._tokens: dict[str, str] = {}

    def token_callback(self, request: Request) -> Response:
        expected_json = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }
        got_json = json.loads(request.content)

        if "code" not in got_json or got_json["code"] not in self._codes:
            return Response(status_code=401, json={"error": "invalid_grant"})

        for key, value in expected_json.items():
            if got_json.get(key) != value:
                return Response(status_code=401, json={"error": "invalid_data"})

        token = urlsafe_b64encode(urandom(64)).decode()
        self._tokens[token] = self._codes.pop(got_json["code"])

        return Response(status_code=200, json={
            "access_token": token,
            "refresh_token": "whatever-it-is-not-used-anyway",
            "expires_in": 3600,
        })

    def userinfo_callback(self, request: Request) -> Response:
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response(status_code=401, json={"error": "invalid_grant"})
        auth_header = auth_header[7:].strip()
        if auth_header not in self._tokens:
            return Response(status_code=401, json={"error": "invalid_grant"})

        user_email = self._tokens[auth_header]
        user_info = self._users[user_email]

        return Response(status_code=200, json=user_info)

    def add_user(self, email: str, first: str = "testr", last: str = "testl") -> str:
        code = urlsafe_b64encode(urandom(32)).decode()

        if email not in self._users:
            self._users[email] = {
                "id": str(len(self._users)),
                "email": email,
                "given_name": first,
                "family_name": last,
            }

        self._codes[code] = email
        return code
