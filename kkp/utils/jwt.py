import hmac
import json
from base64 import urlsafe_b64encode, urlsafe_b64decode
from hashlib import sha256
from time import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat import backends
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

_CERTIFICATE_MARKER = b"-----BEGIN CERTIFICATE-----"
_BACKEND = backends.default_backend()
_PADDING = padding.PKCS1v15()
_SHA256 = hashes.SHA256()


def assert_(value: ..., exc_cls: type[Exception] = ValueError):  # pragma: no cover
    if not value:
        raise exc_cls


class JWT:
    @staticmethod
    def _b64encode(data: bytes | dict) -> str:
        if isinstance(data, dict):
            data = json.dumps(data, separators=(',', ':')).encode("utf8")

        return urlsafe_b64encode(data).decode("utf8").strip("=")

    @staticmethod
    def _b64decode(data: str | bytes) -> bytes:
        if isinstance(data, str):
            data = data.encode("utf8")

        if len(data) % 4 != 0:
            data += b"=" * (-len(data) % 4)

        return urlsafe_b64decode(data)

    @staticmethod
    def _verify_hs256(data: bytes, secret: bytes) -> bytes:
        sig = hmac.new(secret, data, sha256).digest()
        return sig

    @staticmethod
    def _verify_rs256(data: bytes, key: bytes, signature: bytes) -> bytes:
        if _CERTIFICATE_MARKER in key:
            cert = load_pem_x509_certificate(key, _BACKEND)
            pubkey = cert.public_key()
        else:
            pubkey = serialization.load_pem_public_key(key, _BACKEND)

        try:
            pubkey.verify(signature, data, _PADDING, _SHA256)
            return signature
        except (ValueError, InvalidSignature):
            return b""

    @staticmethod
    def decode(token: str, secret: str | bytes | dict[str, str]) -> dict | None:
        try:
            header, payload, signature = token.split(".")
            header_dict = json.loads(JWT._b64decode(header).decode("utf8"))
            assert_(header_dict.get("alg") in ("HS256", "RS256"))
            assert_(header_dict.get("typ") == "JWT")
            assert_((exp := header_dict.get("exp", 0)) > time() or exp == 0)
            signature = JWT._b64decode(signature)
        except (IndexError, ValueError):
            return None

        data = f"{header}.{payload}".encode("utf8")
        if header_dict["alg"] == "HS256":
            sig = JWT._verify_hs256(data, secret)
        elif header_dict["alg"] == "RS256":
            if (kid := header_dict.get("kid")) is None or not isinstance(secret, dict) or kid not in secret:
                return None

            sig = JWT._verify_rs256(data, secret[kid].encode("utf8"), signature)
        else:
            return None

        if sig == signature:
            payload = JWT._b64decode(payload).decode("utf8")
            return json.loads(payload)

    @staticmethod
    def encode(
            payload: dict, secret: str | bytes, expire_timestamp: int | float = 0, expires_in: int = None,
    ) -> str:
        if expire_timestamp == 0 and expires_in is not None:
            expire_timestamp = int(time() + expires_in)

        header = {
            "alg": "HS256",
            "typ": "JWT",
            "exp": int(expire_timestamp)
        }
        header = JWT._b64encode(header)
        payload = JWT._b64encode(payload)

        signature = f"{header}.{payload}".encode("utf8")
        signature = hmac.new(secret, signature, sha256).digest()
        signature = JWT._b64encode(signature)

        return f"{header}.{payload}.{signature}"