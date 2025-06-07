from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from tortoise import Model, fields

from kkp import models
from kkp.db.custom_model import CustomModel
from kkp.utils.cache import Cache


class DonationStatus(IntEnum):
    CREATED = 0
    PROCESSED = 1


class Donation(CustomModel):
    id: int = fields.BigIntField(pk=True)
    user: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None)
    amount: float = fields.FloatField()
    date: datetime = fields.DatetimeField(auto_now_add=True)
    comment: str | None = fields.TextField(null=True, default=None)
    goal: models.DonationGoal = fields.ForeignKeyField("models.DonationGoal")
    status: DonationStatus = fields.IntEnumField(DonationStatus, default=DonationStatus.CREATED)
    paypal_id: str = fields.CharField(max_length=128, default="")

    @Cache.decorator()
    async def to_json(self) -> dict:
        await self.fetch_related_maybe("goal", "user")

        return {
            "id": self.id,
            "user": await self.user.to_json_base() if self.user else None,
            "amount": self.amount,
            "date": int(self.date.timestamp()),
            "comment": self.comment,
            "goal": await self.goal.to_json(),
        }

    def cache_key(self) -> str:
        return f"donation-{self.id}"

    cache_ns = cache_key
