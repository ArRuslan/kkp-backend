from __future__ import annotations

from datetime import datetime

from tortoise import Model, fields

from kkp import models


class Donation(Model):
    id: int = fields.BigIntField(pk=True)
    user: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None)
    amount: float = fields.FloatField()
    date: datetime = fields.DatetimeField(auto_now_add=True)
    comment: str | None = fields.TextField(null=True, default=None)