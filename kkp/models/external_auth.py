from __future__ import annotations

from enum import IntEnum

from tortoise import Model, fields

from kkp import models


class ExtAuthType(IntEnum):
    GOOGLE = 1


class ExternalAuth(Model):
    id: int = fields.BigIntField(pk=True)
    external_id: str = fields.CharField(max_length=255, unique=True)
    user: models.User = fields.OneToOneField("models.User")
    type: ExtAuthType = fields.IntEnumField(ExtAuthType)
    access_token: str = fields.TextField()
    refresh_token: str = fields.TextField()
    token_expires_at: int = fields.BigIntField()
