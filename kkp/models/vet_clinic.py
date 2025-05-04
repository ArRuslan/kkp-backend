from __future__ import annotations

from tortoise import Model, fields

from kkp import models


class VetClinic(Model):
    id: int = fields.BigIntField(pk=True)
    location: models.GeoPoint = fields.ForeignKeyField("models.GeoPoint")
    admin: models.User | None = fields.ForeignKeyField("models.User", null=True, related_name="vet_admin")  # make non nullable??
    employees: fields.ManyToManyRelation[models.User] = fields.ManyToManyField("models.User")
