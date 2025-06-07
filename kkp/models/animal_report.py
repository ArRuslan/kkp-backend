from __future__ import annotations

from datetime import datetime

from tortoise import fields

from kkp import models
from kkp.db.custom_model import CustomModel
from kkp.utils.cache import Cache


class AnimalReport(CustomModel):
    id: int = fields.BigIntField(pk=True)
    reported_by: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None, related_name="reported_by")
    animal: models.Animal = fields.ForeignKeyField("models.Animal")
    created_at: datetime = fields.DatetimeField(auto_now_add=True)
    assigned_to: models.User | None = fields.ForeignKeyField("models.User", null=True, default=None, related_name="assigned_to")
    notes: str = fields.TextField(default="")
    media: fields.ManyToManyRelation[models.Media] = fields.ManyToManyField("models.Media")
    location: models.GeoPoint = fields.ForeignKeyField("models.GeoPoint")

    reported_by: int | None
    assigned_to: int | None
    location: int

    @Cache.decorator()
    async def to_json(self) -> dict:
        await self.fetch_related_maybe("reported_by", "assigned_to", "animal", "location")

        return {
            "id": self.id,
            "reported_by": await self.reported_by.to_json() if self.reported_by is not None else None,
            "animal": await self.animal.to_json(),
            "created_at": int(self.created_at.timestamp()),
            "assigned_to": await self.assigned_to.to_json() if self.assigned_to is not None else None,
            "notes": self.notes,
            "media": [
                media.to_json()
                for media in await self.media.all()
            ],
            "location": self.location.to_json(),
        }

    def cache_key(self) -> str:
        return f"animal-report-{self.id}"

    cache_ns = cache_key
