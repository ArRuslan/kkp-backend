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

    async def to_json(self) -> dict:
        to_fetch = []
        if self.reported_by is not None:
            to_fetch.append("reported_by")
        if self.assigned_to is not None:
            to_fetch.append("assigned_to")
        if self.animal is not None:
            to_fetch.append("animal")
        if self.location is not None:
            to_fetch.append("location")

        if to_fetch:
            await self.fetch_related(*to_fetch)

        return {
            "id": self.id,
            "reported_by": self.reported_by.to_json() if self.reported_by is not None else None,
            "animal": await self.animal.to_json(),
            "created_at": int(self.created_at.timestamp()),
            "assigned_to": self.assigned_to.to_json() if self.assigned_to is not None else None,
            "notes": self.notes,
            "media": [
                media.to_json()
                for media in await self.media.all()
            ],
            "location": self.location.to_json(),
        }
