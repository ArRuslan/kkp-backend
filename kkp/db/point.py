from tortoise import fields
from tortoise.exceptions import FieldError


class Point:
    __slots__ = ("lon", "lat",)

    def __init__(self, lon: float, lat: float) -> None:
        self.lon = lon
        self.lat = lat


class PointField(fields.Field[Point]):
    field_type = Point
    SQL_TYPE = "POINT"

    def to_db_value(self, value: Point, _) -> str:
        if not isinstance(value, Point):
            raise FieldError("The value to be saved must be a Point.")
        if not isinstance(value.lon, float):
            raise FieldError("The longitude must be a float.")
        if not isinstance(value.lat, float):
            raise FieldError("The latitude must be a float.")

        return f"POINT({value.lon}, {value.lat})"
