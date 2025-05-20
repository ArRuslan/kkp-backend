from __future__ import annotations

from datetime import datetime

from tortoise import Model, fields


class DonationGoal(Model):
    id: int = fields.BigIntField(pk=True)
    name: str = fields.CharField(max_length=128)
    description: str = fields.TextField()
    need_amount: float = fields.FloatField()
    got_amount: float = fields.FloatField(default=0)
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    ended_at: datetime | None = fields.DatetimeField(auto_now_add=True, null=True, default=None)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "need_amount": self.need_amount,
            "got_amount": self.got_amount,
            "created_at": int(self.created_at.timestamp()),
            "ended_at": int(self.ended_at.timestamp()) if self.ended_at else None,
        }
