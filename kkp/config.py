from base64 import b64decode
from functools import partial
from os import urandom

from pydantic_settings import BaseSettings
from pydantic import MariaDBDsn, MySQLDsn, AnyUrl, UrlConstraints, Field, field_validator


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

    # TODO: payment service api key
    # TODO: smtp settings
    # TODO: fcm credentials
    # TODO: redis dsn

    @classmethod
    @field_validator("jwt_key", mode="before")
    def decode_jwt_key(cls, value: str | bytes) -> bytes:
        if not isinstance(value, bytes) or len(value) != 16:
            return b64decode(value)
        return value


config = _Config()
