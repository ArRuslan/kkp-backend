from base64 import b64decode
from functools import partial
from os import urandom
from pathlib import Path

from aiofcm import FCM as FCMClient
from aiosmtplib import SMTP as SMTPClient
from pydantic import Field, field_validator, RedisDsn
from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings
from s3lite import Client


class _Config(BaseSettings):
    is_debug: bool = True
    root_path: str = ""
    db_connection_string: str = ""
    redis_connection_string: RedisDsn = "redis://127.0.0.1:6379"
    fcm_config_path: Path = "fcm_config.json"
    bcrypt_rounds: int = 12
    public_host: str = "http://127.0.0.1:8080"

    max_photo_size: int = 8 * 1024 * 1024
    max_video_size: int = 64 * 1024 * 104

    jwt_key: bytes = Field(default_factory=partial(urandom, 16))
    jwt_ttl: int = 86400 * 7

    s3_endpoint: str = "http://127.0.0.1:9000"
    s3_endpoint_public: str = None
    s3_access_key_id: str = None
    s3_access_secret_key: str = None
    s3_bucket_name: str = "kkp"

    smtp_host: str = "127.0.0.1"
    smtp_port: int = 10025
    smtp_username: str | None = None
    smtp_password: str | None = None

    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_google_redirect: str = "http://127.0.0.1:8000/auth/google/callback"

    # TODO: payment service api key
    # TODO: maps api credentials ?

    @field_validator("jwt_key", mode="before")
    def decode_jwt_key(cls, value: str | bytes) -> bytes:
        if not isinstance(value, bytes) or len(value) != 16:
            return b64decode(value)
        return value

    @field_validator("s3_endpoint_public", mode="before")
    def set_s3_public_endpoint(cls, value: str | None, values: ValidationInfo) -> str:
        if value is None:
            return values.data["s3_endpoint"]
        return value

    @field_validator("smtp_username", "smtp_password", mode="before")
    def set_smtp_creds_to_none_if_empty(cls, value: str | None) -> str | None:
        return value or None


config = _Config()

S3 = Client(config.s3_access_key_id, config.s3_access_secret_key, config.s3_endpoint)
S3_PUBLIC = Client(config.s3_access_key_id, config.s3_access_secret_key, config.s3_endpoint_public)
SMTP = SMTPClient(
    hostname=config.smtp_host,
    port=config.smtp_port,
    username=config.smtp_username,
    password=config.smtp_password,
)
FCM = FCMClient(str(config.fcm_config_path))