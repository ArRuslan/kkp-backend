from contextvars import ContextVar
from functools import wraps
from typing import ParamSpec, TypeVar, Callable, Protocol

import aiocache

P = ParamSpec("P")
Tdict = TypeVar("Tdict", bound=dict)


class Cacheable(Protocol):
    def cache_key(self) -> str:
        ...

TC = TypeVar("TC", bound=Cacheable)

class CachedFunc(Protocol):
    async def __call__(self: Cacheable, *args, **kwargs) -> Tdict:
        ...


class Cache:
    _cache: aiocache.BaseCache | None = None
    _disabled: ContextVar[bool] = ContextVar("_disabled", default=False)

    @classmethod
    def _init_maybe(cls) -> None:
        if cls._cache is None:
            cls._cache = aiocache.caches.get("default")

    @classmethod
    async def set(cls, key: str, obj: dict, ttl: int = 60 * 60) -> None:
        cls._init_maybe()
        await cls._cache.set(key, obj, ttl=ttl)

    @classmethod
    async def get(cls, key: str) -> dict | None:
        if cls._disabled.get():
            return None

        cls._init_maybe()
        return await cls._cache.get(key)

    @classmethod
    async def delete(cls, key: str) -> None:
        cls._init_maybe()
        await cls._cache.delete(key)

    @classmethod
    async def delete_obj(cls, obj: Cacheable, *suffixes: str) -> None:
        cls._init_maybe()

        cache_key = obj.cache_key()

        if not suffixes:
            await cls._cache.delete(cache_key)

        for suffix in suffixes:
            await cls._cache.delete(f"{cache_key}-{suffix}")

    @classmethod
    def disable(cls) -> None:
        cls._disabled.set(True)

    @classmethod
    def decorator(cls, ttl: int = 60 * 60, key_suffix: str = "") -> Callable[[CachedFunc], CachedFunc]:
        def real_decorator(func: CachedFunc) -> CachedFunc:
            @wraps(func)
            async def wrapper(self: Cacheable, *args, **kwargs) -> Tdict:
                cache_key = self.cache_key()
                if key_suffix:
                    cache_key += f"-{key_suffix}"

                if not cls._disabled.get() and (cached := await cls.get(cache_key)) is not None:
                    return cached

                result = await func(self, *args, **kwargs)
                await cls.set(cache_key, result, ttl)

                return result

            return wrapper

        return real_decorator
