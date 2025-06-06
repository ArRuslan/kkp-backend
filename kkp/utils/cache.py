from contextvars import ContextVar
from enum import Enum, auto
from functools import wraps
from typing import ParamSpec, TypeVar, Callable, Protocol

import aiocache

P = ParamSpec("P")
Tdict = TypeVar("Tdict", bound=dict)


class _CacheDisabled(Enum):
    NONE = auto()
    READ = auto()
    READWRITE = auto()


class Cacheable(Protocol):
    def cache_key(self) -> str:  # pragma: no cover
        ...

    def cache_ns(self) -> str:  # pragma: no cover
        ...

TC = TypeVar("TC", bound=Cacheable)

class CachedFunc(Protocol):
    async def __call__(self: Cacheable, *args, **kwargs) -> Tdict:  # pragma: no cover
        ...


class Cache:
    _cache: aiocache.BaseCache | None = None
    _disabled: ContextVar[_CacheDisabled] = ContextVar("_disabled", default=_CacheDisabled.NONE)
    _suffix: ContextVar[str] = ContextVar("_suffix", default="")

    @classmethod
    def _init_maybe(cls) -> None:
        if cls._cache is None:
            cls._cache = aiocache.caches.get("default")

    @classmethod
    async def set(cls, ns: str, key: str, obj: dict, ttl: int = 60 * 60) -> None:
        if cls._disabled.get() is _CacheDisabled.READWRITE:
            return None

        cls._init_maybe()
        await cls._cache.set(key, obj, namespace=ns, ttl=ttl)

    @classmethod
    async def get(cls, ns: str, key: str) -> dict | None:
        if cls._disabled.get() in (_CacheDisabled.READ, _CacheDisabled.READWRITE):
            return None

        cls._init_maybe()
        return await cls._cache.get(key, namespace=ns)

    @classmethod
    async def delete_obj(cls, obj: Cacheable) -> None:
        cls._init_maybe()
        await cls._cache.clear(namespace=obj.cache_ns())

    @classmethod
    def disable(cls, completely: bool = False) -> None:
        cls._disabled.set(_CacheDisabled.READWRITE if completely else _CacheDisabled.READ)

    @classmethod
    def suffix(cls, suffix: str) -> None:
        cls._suffix.set(suffix)

    @classmethod
    def decorator(cls, ttl: int = 60 * 60, key_suffix: str = "") -> Callable[[CachedFunc], CachedFunc]:
        def real_decorator(func: CachedFunc) -> CachedFunc:
            @wraps(func)
            async def wrapper(self: Cacheable, *args, **kwargs) -> Tdict:
                cache_ns = self.cache_ns()
                cache_key = self.cache_key()
                if key_suffix:
                    cache_key += f"-{key_suffix}"
                if cls._suffix.get():
                    cache_key += f"-{cls._suffix.get()}"

                if (cached := await cls.get(cache_ns, cache_key)) is not None:
                    return cached

                result = await func(self, *args, **kwargs)
                await cls.set(cache_ns, cache_key, result, ttl)

                return result

            return wrapper

        return real_decorator
