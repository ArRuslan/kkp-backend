from __future__ import annotations

from tortoise import Model, fields
from tortoise.contrib.mysql.indexes import SpatialIndex

from kkp.db.point import Point, PointField, mbr_contains_sql


class GeoPoint(Model):
    id: int = fields.BigIntField(pk=True)
    name: str | None = fields.CharField(max_length=128, null=True)
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

    @classmethod
    async def create(cls, *, latitude: float, longitude: float, name: str | None = None) -> GeoPoint:
        return await super(cls, GeoPoint).create(
            name=name,
            latitude=latitude,
            longitude=longitude,
            point=Point(longitude, latitude),
        )

    @classmethod
    async def get_near(cls, latitude: float, longitude: float, radius: int = 100) -> GeoPoint | None:
        if not isinstance(radius, (int, float)):
            return None

        point = Point(longitude, latitude)
        point_wkb = point.to_sql_wkb_bin().hex()

        result = await GeoPoint.raw(f"""
            SELECT *, ST_Distance_Sphere(`point`, x'{point_wkb}') `dist` 
            FROM `geopoint` 
            WHERE {mbr_contains_sql(point, radius)} 
            HAVING `dist` < {radius} 
            ORDER BY `dist`  
            LIMIT 1
        """)

        return result[0] if result else None
