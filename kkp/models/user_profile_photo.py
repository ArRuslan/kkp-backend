from __future__ import annotations

from tortoise import Model, fields

from kkp import models


class UserProfilePhoto(Model):
    id: int = fields.BigIntField(pk=True)
    user: models.User = fields.OneToOneField("models.User")
    photo: models.Media = fields.ForeignKeyField("models.Media")
