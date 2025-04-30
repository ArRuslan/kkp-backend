from __future__ import annotations

from enum import IntEnum

from tortoise import Model, fields

from kkp import models


class AnimalStatus(IntEnum):
    UNKNOWN = 0
    FOUND = 1
    ON_TREATMENT = 2
    RELEASED = 3
    WAITING_FOR_ADOPTION = 4
    ADOPTED = 5


class Animal(Model):
    id: int = fields.BigIntField(pk=True)
    name: str = fields.CharField(max_length=128)
    breed: str = fields.CharField(max_length=64)
    status: AnimalStatus = fields.IntEnumField(AnimalStatus)
    description: str = fields.TextField(default="")
    resources: fields.ManyToManyRelation[models.PhotoVideo] = fields.ManyToManyField("models.PhotoVideo")
    current_location: models.GeoPoint | None = fields.ForeignKeyField("models.GeoPoint", null=True)  # ??
