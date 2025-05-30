from __future__ import annotations

from datetime import datetime

from tortoise import Model, fields

from kkp import models
from kkp.utils.cache import Cache


class Message(Model):
    id: int = fields.BigIntField(pk=True)
    dialog: models.Dialog = fields.ForeignKeyField("models.Dialog")
    author: models.User = fields.ForeignKeyField("models.User")
    text: str = fields.TextField()
    media: models.Media | None = fields.ForeignKeyField("models.Media", null=True, default=None)
    date: datetime = fields.DatetimeField(auto_now_add=True)

    media_id: int | None

    @Cache.decorator()
    async def to_json(self, current_user: models.User) -> dict:
        if self.dialog is not None:
            self.dialog = await self.dialog
        if self.author is not None:
            self.author = await self.author
        if self.media is not None:
            self.media = await self.media

        return {
            "id": self.id,
            "dialog": await self.dialog.to_json(current_user),
            "author": await self.author.to_json_base(),
            "text": self.text,
            "media": self.media.to_json() if self.media is not None else None,
            "date": int(self.date.timestamp()),
        }

    def cache_key(self) -> str:
        return f"message-{self.id}"

    cache_ns = cache_key
