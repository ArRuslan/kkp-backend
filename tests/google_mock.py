import json
import re
from base64 import urlsafe_b64encode
from os import urandom
from time import time

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import utils
from httpx import Request, Response

from kkp.config import config
from kkp.utils.google_id_token import GOOGLE_ISSUERS
from kkp.utils.google_oauth import GoogleOAuthResponse
from kkp.utils.jwt import JWT, JWT_RS_SHA256, JWT_RS_PADDING


class GoogleMockState:
    CAPTURE_RE = re.compile(r".+/v2/checkout/orders/\d+\.\d+/capture")
    _ID_PRIVATE_KEY = None
    _ID_PUBLIC_KEY = None
    _ID_PUBLIC_KEY_ID = None
    _ID_PUBLIC_KEY_PEM = None

    def __init__(
            self, client_id: str = config.oauth_google_client_id, client_secret: str = config.oauth_google_client_secret,
            redirect_uri: str = config.oauth_google_redirect, iss: str | None = None
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._jwt_iss = iss or GOOGLE_ISSUERS[0]
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

    def _generate_keys_if_none(self) -> None:
        if self._ID_PRIVATE_KEY is not None and self._ID_PUBLIC_KEY is not None:
            return

        self._ID_PRIVATE_KEY = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )

        self._ID_PUBLIC_KEY = self._ID_PRIVATE_KEY.public_key()
        self._ID_PUBLIC_KEY_ID = hex(self._ID_PUBLIC_KEY.public_numbers().n)[-16:]
        self._ID_PUBLIC_KEY_PEM = self._ID_PUBLIC_KEY.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf8")

    def certs_callback(self, _: Request) -> Response:
        self._generate_keys_if_none()
        return Response(status_code=200, json={self._ID_PUBLIC_KEY_ID: self._ID_PUBLIC_KEY_PEM})

    def certs_callback_fail(self, _: Request) -> Response:
        return Response(status_code=400, json={})

    def get_id_token_for_user(self, email: str) -> str:
        if email not in self._users:
            self.add_user(email)

        user = self._users[email]

        self._generate_keys_if_none()

        header = JWT._b64encode({
            "exp": int(time() + 60),
            "alg": "RS256",
            "typ": "JWT",
            "kid": self._ID_PUBLIC_KEY_ID,
        })
        payload = JWT._b64encode({
            "aud": self._client_id,
            "iss": self._jwt_iss,
            "sub": user["id"],
            "email": email,
            "given_name": user["given_name"],
            "family_name": user["family_name"],
        })

        jwt_hash = hashes.Hash(JWT_RS_SHA256)
        jwt_hash.update(f"{header}.{payload}".encode("utf8"))
        digest = jwt_hash.finalize()

        signature = self._ID_PRIVATE_KEY.sign(digest, JWT_RS_PADDING, utils.Prehashed(JWT_RS_SHA256))
        signature = JWT._b64encode(signature)

        return f"{header}.{payload}.{signature}"
