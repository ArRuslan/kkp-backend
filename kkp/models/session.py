from __future__ import annotations

from datetime import datetime
from os import urandom

from tortoise import fields, Model

from kkp import models
from kkp.config import config
from kkp.utils.jwt import JWT


class Session(Model):
    id: int = fields.BigIntField(pk=True)
    user: models.User = fields.ForeignKeyField("models.User")
    nonce: str = fields.CharField(max_length=16, default=lambda: urandom(8).hex())
    created_at: datetime = fields.DatetimeField(auto_now_add=True)

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