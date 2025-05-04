from __future__ import annotations

from datetime import datetime

from tortoise import Model, fields

from kkp import models


class AnimalReport(Model):
    id: int = fields.BigIntField(pk=True)
    reported_by: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None, related_name="reported_by")
    animal: models.Animal = fields.ForeignKeyField("models.Animal")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    assigned_to: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None, related_name="assigned_to")
    notes: str = fields.TextField(default="")
    media: fields.ManyToManyRelation[models.Media] = fields.ManyToManyField("models.Media")
    location: models.GeoPoint = fields.ForeignKeyField("models.GeoPoint")
