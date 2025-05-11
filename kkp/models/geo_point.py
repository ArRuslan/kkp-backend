from __future__ import annotations

from tortoise import Model, fields
from tortoise.contrib.mysql.indexes import SpatialIndex

from kkp.db.point import Point, PointField


class GeoPoint(Model):
    id: int = fields.BigIntField(pk=True)
    name: str | None = fields.CharField(max_length=128)
    latitude: float = fields.FloatField()
    longitude: float = fields.FloatField()
    point: Point = PointField()

    class Meta:
        indexes = [
            SpatialIndex(fields=("point",))
        ]

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
