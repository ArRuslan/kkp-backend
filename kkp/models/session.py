from __future__ import annotations

from datetime import datetime
from os import urandom
from typing import Any

from pytz import UTC
from tortoise import fields, Model, BaseDBAsyncClient
from tortoise.contrib.mysql.indexes import SpatialIndex
from tortoise.models import MODEL

from kkp import models
from kkp.config import config
from kkp.db.point import PointField, Point
from kkp.utils.jwt import JWT


class Session(Model):
    id: int = fields.BigIntField(pk=True)
    user: models.User = fields.ForeignKeyField("models.User")
    nonce: str = fields.CharField(max_length=16, default=lambda: urandom(8).hex())
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    active: bool = fields.BooleanField(default=True)

    fcm_token: str | None = fields.TextField(null=True, default=None)
    fcm_token_time: int = fields.BigIntField(default=0)

    location: Point = PointField()
    location_time: datetime = fields.DatetimeField()

    class Meta:
        indexes = [
            SpatialIndex(fields=("location",))
        ]

    @classmethod
    async def create(
        cls: type[MODEL], using_db: BaseDBAsyncClient | None = None, **kwargs: Any
    ) -> MODEL:
        if "location" not in kwargs:
            kwargs["location"] = Point(0., 0.)
        if "location_time" not in kwargs:
            kwargs["location_time"] = datetime.fromtimestamp(0, UTC)
        return await super().create(using_db=using_db, **kwargs)

    def to_jwt(self) -> str:
        return JWT.encode(
            {
                "u": self.user.id,
                "s": self.id,
                "n": self.nonce,
            },
            config.jwt_key,
            expires_in=config.jwt_ttl,
        )

    @classmethod
    async def from_jwt(cls, token: str) -> Session | None:
        if (payload := JWT.decode(token, config.jwt_key)) is None:
            return None

        return await Session.get_or_none(
            id=payload["s"], user__id=payload["u"], nonce=payload["n"]
        ).select_related("user")