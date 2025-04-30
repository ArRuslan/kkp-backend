from pydantic_settings import BaseSettings
from pydantic import MariaDBDsn, MySQLDsn, AnyUrl, UrlConstraints


class SqliteDsn(AnyUrl):
    _constraints = UrlConstraints(
        allowed_schemes=["sqlite"],
    )


class _Config(BaseSettings):
    is_debug: bool = True
    db_connection_string: MariaDBDsn | MySQLDsn | SqliteDsn = "sqlite://kkp.db"
    # TODO: jwt key
    # TODO: payment service api key
    # TODO: smtp settings
    # TODO: fcm credentials
    # TODO: redis dsn


config = _Config()
