from __future__ import annotations

from enum import IntEnum

import bcrypt
from tortoise import Model, fields

from kkp import models
from kkp.utils.cache import Cache


class UserRole(IntEnum):
    REGULAR = 0
    VET = 10
    VOLUNTEER = 11
    VET_ADMIN = 100
    GLOBAL_ADMIN = 999


class User(Model):
    id: int = fields.BigIntField(pk=True)
    first_name: str = fields.CharField(max_length=64)
    last_name: str = fields.CharField(max_length=64)
    email: str = fields.CharField(max_length=255, unique=True)
    password: str | None = fields.CharField(max_length=128, null=True, default=None)
    role: UserRole = fields.IntEnumField(UserRole, default=UserRole.REGULAR)
    subscriptions: fields.ManyToManyRelation[models.Animal] = fields.ManyToManyField("models.Animal")
    mfa_key: str | None = fields.CharField(max_length=32, null=True, default=None)
    telegram_username: str | None = fields.CharField(max_length=128, null=True, default=None)
    viber_phone: str | None = fields.CharField(max_length=64, null=True, default=None)
    whatsapp_phone: str | None = fields.CharField(max_length=64, null=True, default=None)

    def check_password(self, password: str) -> bool:
        if self.password is None:
            return False
        return bcrypt.checkpw(password.encode("utf8"), self.password.encode("utf8"))

    @Cache.decorator(key_suffix="basic")
    async def to_json_base(self) -> dict:
        photo = await models.UserProfilePhoto.get_or_none(user=self).select_related("photo")

        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "photo": photo.photo.to_json() if photo is not None else None,
            "telegram_username": self.telegram_username,
            "viber_phone": self.viber_phone,
            "whatsapp_phone": self.whatsapp_phone,
        }

    @Cache.decorator(key_suffix="full")
    async def to_json(self) -> dict:
        photo = await models.UserProfilePhoto.get_or_none(user=self).select_related("photo")

        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "role": self.role,
            "mfa_enabled": bool(self.mfa_key),
            "photo": photo.photo.to_json() if photo is not None else None,
            "telegram_username": self.telegram_username,
            "viber_phone": self.viber_phone,
            "whatsapp_phone": self.whatsapp_phone,
        }

    def cache_key(self) -> str:
        return f"user-{self.id}"

    cache_ns = cache_key
