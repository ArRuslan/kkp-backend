from __future__ import annotations

from enum import IntEnum

import bcrypt
from tortoise import Model, fields

from kkp import models


class UserRole(IntEnum):
    REGULAR = 0
    VET = 10
    VET_ADMIN = 100
    GLOBAL_ADMIN = 999


class User(Model):
    id: int = fields.BigIntField(pk=True)
    first_name: str = fields.CharField(max_length=64)
    last_name: str = fields.CharField(max_length=64)
    email: str = fields.CharField(max_length=255, unique=True)
    password: str = fields.CharField(max_length=128)
    role: UserRole = fields.IntEnumField(UserRole, default=UserRole.REGULAR)
    subscriptions: fields.ManyToManyRelation[models.Animal] = fields.ManyToManyField("models.Animal")
    mfa_key: str | None = fields.CharField(max_length=32, null=True, default=None)
    photo: models.Media | None = fields.ForeignKeyField("models.Media", null=True, default=None)

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf8"), self.password.encode("utf8"))
