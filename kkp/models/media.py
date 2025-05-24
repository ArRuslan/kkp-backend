from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from uuid import UUID, uuid4

from tortoise import Model, fields

from kkp import models
from kkp.config import S3_PUBLIC, config


class MediaType(IntEnum):
    PHOTO = 1
    VIDEO = 2


class MediaStatus(IntEnum):
    CREATED = 1
    UPLOADED = 2


class Media(Model):
    id: int = fields.BigIntField(pk=True)
    uploaded_at: datetime = fields.DatetimeField(auto_now_add=True)
    uploaded_by: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None)
    type: MediaType = fields.IntEnumField(MediaType)
    status: MediaStatus = fields.IntEnumField(MediaStatus, default=MediaStatus.CREATED)
    media_id: UUID = fields.UUIDField(default=uuid4)

    def upload_url(self, ttl: int = 60 * 60) -> str:
        return S3_PUBLIC.share(config.s3_bucket_name, self.object_key(), ttl, True)

    def object_key(self) -> str:
        return f"{self.type.name.lower()}s/{self.media_id}"

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "uploaded_at": int(self.uploaded_at.timestamp()),
            "type": self.type,
            "url": S3_PUBLIC.share(config.s3_bucket_name, self.object_key()),
        }
