from __future__ import annotations

from datetime import datetime
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


class AnimalGender(IntEnum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 1


class Animal(Model):
    id: int = fields.BigIntField(pk=True)
    name: str = fields.CharField(max_length=128)
    breed: str = fields.CharField(max_length=64)
    status: AnimalStatus = fields.IntEnumField(AnimalStatus)
    description: str = fields.TextField(default="")
    medias: fields.ManyToManyRelation[models.Media] = fields.ManyToManyField("models.Media")
    current_location: models.GeoPoint | None = fields.ForeignKeyField("models.GeoPoint", null=True)  # ??
    updated_at: datetime = fields.DatetimeField(auto_now_add=True)
    gender: AnimalGender = fields.IntEnumField(AnimalGender, default=AnimalGender.UNKNOWN)

    async def to_json(self, current_user: models.User | None = None) -> dict:
        total_media_count = await self.medias.all().count()
        medias = await self.medias.all().order_by("-id").limit(5)

        if self.current_location is not None:
            self.current_location = await self.current_location

        subscribed = False
        if current_user is not None:
            subscribed = await current_user.subscriptions.filter(id=self.id).exists()

        return {
            "id": self.id,
            "name": self.name,
            "breed": self.breed,
            "status": self.status,
            "gender": self.gender,
            "description": self.description,
            "media": {
                "count": total_media_count,
                "result": [
                    media.to_json()
                    for media in medias
                ]
            },
            "current_location": self.current_location.to_json() if self.current_location is not None else None,
            "updated_at": int(self.updated_at.timestamp()),
            "subscribed": subscribed,
        }
