from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from tortoise import Model, fields

from kkp import models


class DonationStatus(IntEnum):
    CREATED = 0
    PROCESSED = 1


class Donation(Model):
    id: int = fields.BigIntField(pk=True)
    user: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None)
    amount: float = fields.FloatField()
    date: datetime = fields.DatetimeField(auto_now_add=True)
    comment: str | None = fields.TextField(null=True, default=None)
    goal: models.DonationGoal = fields.ForeignKeyField("models.DonationGoal")
    status: DonationStatus = fields.IntEnumField(DonationStatus, default=DonationStatus.CREATED)
    paypal_id: str = fields.CharField(max_length=128, default="")

    async def to_json(self) -> dict:
        self.goal = await self.goal
        if self.user is not None:
            self.user = await self.user

        return {
            "id": self.id,
            "user": await self.user.to_json_base() if self.user else None,
            "amount": self.amount,
            "date": int(self.date.timestamp()),
            "comment": self.comment,
            "goal": self.goal.to_json(),
        }
