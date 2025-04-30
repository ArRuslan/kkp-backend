from __future__ import annotations

from datetime import datetime
from enum import IntEnum

from tortoise import Model, fields


class ResourceType(IntEnum):
    PHOTO = 1
    VIDEO = 2


class PhotoVideo(Model):
    id: int = fields.BigIntField(pk=True)
    uploaded_at: datetime = fields.DatetimeField(auto_now_add=True)
    type: ResourceType = fields.IntEnumField(ResourceType)
    photo_url: str | None = fields.TextField(null=True, default=None)
    video_url: str | None = fields.TextField(null=True, default=None)
