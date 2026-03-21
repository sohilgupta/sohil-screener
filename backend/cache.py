"""
Cache layer — Redis primary, thread-safe in-memory LRU fallback.

Usage:
    cache = CacheClient.from_env()
    await cache.get("key")
    await cache.set("key", value, ttl=3600)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_SENTINEL = object()


# ──────────────────────────────────────────────────────────────────────────────
# In-memory LRU cache (fallback when Redis is unavailable)
# ──────────────────────────────────────────────────────────────────────────────

class _LRUCache:
    """Thread-safe in-memory cache with TTL and max-size eviction."""

    def __init__(self, max_size: int = 256) -> None:
        self._store: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key, _SENTINEL)
            if entry is _SENTINEL:
                return None
            value, expires_at = entry
            if expires_at and time.monotonic() > expires_at:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = time.monotonic() + ttl if ttl else None
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expires_at)
            if len(self._store) > self._max_size:
                self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def flush(self) -> None:
        async with self._lock:
            self._store.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Redis client wrapper
# ──────────────────────────────────────────────────────────────────────────────

class _RedisCache:
    """Thin async wrapper around redis.asyncio."""

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._redis.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        serialised = json.dumps(value, default=str)
        if ttl:
            await self._redis.setex(key, ttl, serialised)
        else:
            await self._redis.set(key, serialised)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def flush(self) -> None:
        await self._redis.flushdb()

    async def ping(self) -> bool:
        try:
            return await self._redis.ping()
        except Exception:
            return False


# ──────────────────────────────────────────────────────────────────────────────
# Public CacheClient (selects backend automatically)
# ──────────────────────────────────────────────────────────────────────────────

class CacheClient:
    """
    Unified cache interface.

    - If REDIS_URL env var is set and Redis is reachable → use Redis.
    - Otherwise falls back silently to in-memory LRU cache.
    """

    def __init__(self, backend) -> None:
        self._backend = backend

    @classmethod
    async def from_env(cls) -> "CacheClient":
        redis_url = os.getenv("REDIS_URL", "")
        if redis_url:
            try:
                rc = _RedisCache(redis_url)
                if await rc.ping():
                    logger.info("Cache: connected to Redis at %s", redis_url)
                    return cls(rc)
                else:
                    logger.warning("Cache: Redis unreachable, using in-memory LRU")
            except Exception as exc:
                logger.warning("Cache: Redis init failed (%s), using in-memory LRU", exc)
        else:
            logger.info("Cache: REDIS_URL not set, using in-memory LRU")
        return cls(_LRUCache())

    @property
    def backend_name(self) -> str:
        return self._backend.__class__.__name__

    async def get(self, key: str) -> Optional[Any]:
        try:
            return await self._backend.get(key)
        except Exception as exc:
            logger.debug("Cache get error: %s", exc)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            await self._backend.set(key, value, ttl=ttl)
        except Exception as exc:
            logger.debug("Cache set error: %s", exc)

    async def delete(self, key: str) -> None:
        try:
            await self._backend.delete(key)
        except Exception as exc:
            logger.debug("Cache delete error: %s", exc)

    async def flush(self) -> None:
        try:
            await self._backend.flush()
        except Exception as exc:
            logger.debug("Cache flush error: %s", exc)
