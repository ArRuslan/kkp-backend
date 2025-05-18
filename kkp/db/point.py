from __future__ import annotations

import struct

from pypika_tortoise import CustomFunction
from tortoise import fields
from tortoise.exceptions import FieldError
from tortoise.expressions import Function


class Point:
    # Mysql (and mariadb) uses following format: SRID (4 bytes int) + WKB,
    #  e.g. SRID (4 bytes) + BYTE ORDER (1 byte) + TYPE (4 bytes int) + X (8 bytes double) + Y (8 bytes double)
    #  https://dev.mysql.com/doc/refman/5.7/en/gis-data-formats.html
    MYSQL_GEOM_BIN_FMT = "<ibidd"

    __slots__ = ("lon", "lat",)

    def __init__(self, lon: float, lat: float) -> None:
        self.lon = lon
        self.lat = lat

    def to_sql_wkb_bin(self) -> bytes:
        return struct.pack(self.MYSQL_GEOM_BIN_FMT, 0, 1, 1, self.lon, self.lat)

    @classmethod
    def from_sql_wkb_bin(cls, wkb: bytes) -> Point:
        _, _, _, lon, lat = struct.unpack(cls.MYSQL_GEOM_BIN_FMT, wkb)
        return cls(lon, lat)

    def __repr__(self) -> str:
        return f"Point({self.lon}, {self.lat})"


class PointField(fields.Field[Point]):
    field_type = Point
    SQL_TYPE = "POINT"

    def to_db_value(self, value: Point, _) -> bytes:
        if not isinstance(value, Point):
            raise FieldError("The value to be saved must be a Point.")
        if not isinstance(value.lon, float):
            raise FieldError("The longitude must be a float.")
        if not isinstance(value.lat, float):
            raise FieldError("The latitude must be a float.")

        return value.to_sql_wkb_bin()

    def to_python_value(self, value: bytes | str | Point) -> Point:
        if isinstance(value, Point):
            return value
        if not isinstance(value, bytes):
            value = bytes.fromhex(value)

        if len(value) != 25:
            raise FieldError("Invalid wkb point value.")
        if value[4] != 1:
            raise FieldError(f"Unsupported byte order: '{value[4]}', only '1' is supported now.")

        return Point.from_sql_wkb_bin(value)


class STDistanceSphere(Function):
    database_func = CustomFunction("ST_Distance_Sphere", ["point_a", "point_b"])

    def __init__(self, point_a: str | Point, point_b: str | Point) -> None:
        if isinstance(point_a, Point):
            point_a = point_a.to_sql_wkb_bin()
        if isinstance(point_b, Point):
            point_b = point_b.to_sql_wkb_bin()

        super().__init__(point_a, point_b)