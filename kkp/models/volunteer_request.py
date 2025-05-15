from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from tortoise import fields, Model

from kkp import models


class VolRequestStatus(IntEnum):
    REQUESTED = 1
    APPROVED = 2
    REFUSED = 3


class VolunteerRequest(Model):
    id: int = fields.BigIntField(pk=True)
    user: models.User = fields.ForeignKeyField("models.User")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    reviewed_at: datetime | None = fields.DatetimeField(null=True, default=None)
    text: str = fields.TextField()
    review_text: str | None = fields.TextField(null=True, default=None)
    medias: fields.ManyToManyRelation[models.Media] = fields.ManyToManyField("models.Media")
    status: VolRequestStatus = fields.IntEnumField(VolRequestStatus, default=VolRequestStatus.REQUESTED)

    async def to_json(self) -> dict:
        self.user = await self.user

        return {
            "id": self.id,
            "user": await self.user.to_json_base(),
            "created_at": int(self.created_at.timestamp()),
            "reviewed_at": int(self.reviewed_at.timestamp()) if self.reviewed_at is not None else None,
            "text": self.text,
            "review_text": self.review_text,
            "medias": [
                media.to_json()
                for media in self.medias
            ],
            "status": self.status,
        }
