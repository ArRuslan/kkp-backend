from __future__ import annotations

from tortoise import Model, fields


class GeoPoint(Model):
    id: int = fields.BigIntField(pk=True)
    name: str | None = fields.CharField(max_length=128)
    latitude: float = fields.FloatField()
    longitude: float = fields.FloatField()
