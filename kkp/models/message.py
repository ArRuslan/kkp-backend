from __future__ import annotations

from datetime import datetime

from tortoise import Model, fields

from kkp import models


class Message(Model):
    id: int = fields.BigIntField(pk=True)
    dialog: models.Dialog = fields.ForeignKeyField("models.Dialog")
    author: models.User = fields.ForeignKeyField("models.User")
    text: str = fields.TextField()
    media: models.Media | None = fields.ForeignKeyField("models.Media", null=True, default=None)
    date: datetime = fields.DatetimeField(auto_now_add=True)
    # TODO: replies?
