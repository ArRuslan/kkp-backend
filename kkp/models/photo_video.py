from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from uuid import UUID

from tortoise import Model, fields

from kkp import models
from kkp.config import S3_PUBLIC, config


class ResourceType(IntEnum):
    PHOTO = 1
    VIDEO = 2


class ResourceStatus(IntEnum):
    CREATED = 1
    UPLOADED = 2


# TODO: rename to Media
class PhotoVideo(Model):
    id: int = fields.BigIntField(pk=True)
    uploaded_at: datetime = fields.DatetimeField(auto_now_add=True)
    uploaded_by: models.User = fields.ForeignKeyField("models.User")  # TODO: make nullable ??
    type: ResourceType = fields.IntEnumField(ResourceType)
    status: ResourceStatus = fields.IntEnumField(ResourceStatus, default=ResourceStatus.CREATED)
    # TODO: leave only one field and name it `media_id`
    photo_id: UUID | None = fields.UUIDField(null=True, default=None)
    video_id: UUID | None = fields.UUIDField(null=True, default=None)

    def upload_url(self, ttl: int = 60 * 60) -> str:
        return S3_PUBLIC.share(config.s3_bucket, self.object_key(), ttl)

    def object_key(self) -> str:
        res_id = self.photo_id or self.video_id
        res_name = ResourceType.PHOTO.name.lower()
        return f"animal-{res_name}s/{res_id}"

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "uploaded_at": int(self.uploaded_at.timestamp()),
            "type": self.type,
            "url": S3_PUBLIC.share(config.s3_bucket, self.object_key()),
        }
