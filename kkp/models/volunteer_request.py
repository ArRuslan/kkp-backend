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
    text: str = fields.TextField()
    medias: fields.ManyToManyRelation[models.Media]
    status: VolRequestStatus = fields.IntEnumField(VolRequestStatus, default=VolRequestStatus.REQUESTED)
