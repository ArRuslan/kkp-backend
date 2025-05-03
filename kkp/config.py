from base64 import b64decode
from functools import partial
from os import urandom

from pydantic_core.core_schema import ValidationInfo
from pydantic_settings import BaseSettings
from pydantic import MariaDBDsn, MySQLDsn, AnyUrl, UrlConstraints, Field, field_validator, HttpUrl
from s3lite import Client


class SqliteDsn(AnyUrl):
    _constraints = UrlConstraints(
        allowed_schemes=["sqlite"],
    )


class _Config(BaseSettings):
    is_debug: bool = True
    db_connection_string: MariaDBDsn | MySQLDsn | SqliteDsn = "sqlite://kkp.db"
    bcrypt_rounds: int = 12

    jwt_key: bytes = Field(default_factory=partial(urandom, 16))
    jwt_ttl: int = 86400 * 7

    s3_endpoint: str = "http://127.0.0.1:9000"
    s3_endpoint_public: str = None
    s3_access_key_id: str = None
    s3_access_secret_key: str = None
    s3_bucket_name: str = "kkp"

    # TODO: payment service api key
    # TODO: smtp settings
    # TODO: fcm credentials
    # TODO: redis dsn

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


config = _Config()
S3 = Client(config.s3_access_key_id, config.s3_access_secret_key, config.s3_endpoint_public)
