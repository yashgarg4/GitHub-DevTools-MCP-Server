"""In-memory TTL cache for GitHub API responses.

Provides a @cached(ttl=seconds) decorator for async functions.
Cache keys are derived automatically from function name + arguments.
"""

import time
import functools
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    data: Any
    expires_at: float


class TTLCache:
    """Simple in-memory cache with per-entry TTL expiration."""

    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._hits: int = 0
        self._misses: int = 0

    def get(self, key: str) -> Any | None:
        """Get a value from cache. Returns None if missing or expired."""
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        if time.time() > entry.expires_at:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return entry.data

    def set(self, key: str, data: Any, ttl: int) -> None:
        """Store a value with a TTL in seconds."""
        self._store[key] = CacheEntry(data=data, expires_at=time.time() + ttl)

    def clear(self) -> int:
        """Clear all cached entries. Returns the number of entries cleared."""
        count = len(self._store)
        self._store.clear()
        self._hits = 0
        self._misses = 0
        return count

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        return {
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{(self._hits / total * 100):.0f}%" if total > 0 else "0%",
        }


# Global cache instance shared across all decorated functions
_cache = TTLCache()


def get_cache() -> TTLCache:
    """Get the global cache instance."""
    return _cache


def cached(ttl: int = 300):
    """Decorator that caches async function results with a TTL (in seconds).

    Cache key is built from function name + all arguments.
    Only caches successful results — exceptions are never cached.

    Args:
        ttl: Time-to-live in seconds. Default is 300 (5 minutes).

    Usage:
        @cached(ttl=120)
        async def get_repo_info(owner, repo):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name + args
            key_parts = [func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            # Check cache
            result = _cache.get(key)
            if result is not None:
                return result

            # Cache miss — call the actual function
            result = await func(*args, **kwargs)

            # Only cache successful results (not exceptions)
            _cache.set(key, result, ttl)
            return result

        return wrapper

    return decorator
