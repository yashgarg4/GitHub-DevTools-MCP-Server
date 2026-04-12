"""Tests for the TTL cache system."""

import time

import pytest
import respx
from httpx import Response

from github_mcp.cache import TTLCache, cached, get_cache
from github_mcp.github_client import get_repo_info


class TestTTLCache:
    """Unit tests for the TTLCache class."""

    def test_set_and_get(self):
        cache = TTLCache()
        cache.set("key1", {"data": "value"}, ttl=60)
        assert cache.get("key1") == {"data": "value"}

    def test_get_missing_key_returns_none(self):
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        cache = TTLCache()
        cache.set("key1", "value", ttl=0)  # expires immediately
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_clear_removes_all_entries(self):
        cache = TTLCache()
        cache.set("k1", "v1", ttl=60)
        cache.set("k2", "v2", ttl=60)
        count = cache.clear()
        assert count == 2
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_stats_tracks_hits_and_misses(self):
        cache = TTLCache()
        cache.set("key1", "value", ttl=60)
        cache.get("key1")  # hit
        cache.get("key1")  # hit
        cache.get("missing")  # miss
        stats = cache.stats
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["entries"] == 1
        assert stats["hit_rate"] == "67%"

    def test_stats_empty_cache(self):
        cache = TTLCache()
        stats = cache.stats
        assert stats["entries"] == 0
        assert stats["hit_rate"] == "0%"


class TestCachedDecorator:
    """Tests for the @cached decorator."""

    @pytest.mark.asyncio
    async def test_caches_result_on_second_call(self):
        call_count = 0

        @cached(ttl=60)
        async def my_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = await my_func(5)
        result2 = await my_func(5)
        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # only called once — second was cached

    @pytest.mark.asyncio
    async def test_different_args_are_cached_separately(self):
        get_cache().clear()
        call_count = 0

        @cached(ttl=60)
        async def my_func_b(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        await my_func_b(5)
        await my_func_b(10)
        assert call_count == 2  # different args = different cache keys

    @pytest.mark.asyncio
    async def test_exceptions_are_not_cached(self):
        call_count = 0

        @cached(ttl=60)
        async def my_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        with pytest.raises(ValueError):
            await my_func()
        with pytest.raises(ValueError):
            await my_func()
        assert call_count == 2  # called twice — errors not cached


class TestCacheIntegration:
    """Integration tests: cache + GitHub client functions."""

    @pytest.mark.asyncio
    async def test_get_repo_info_uses_cache(self, mock_github_env, sample_repo_response):
        # Clear global cache before test
        get_cache().clear()

        with respx.mock:
            route = respx.get(
                "https://api.github.com/repos/octocat/Hello-World"
            ).mock(return_value=Response(200, json=sample_repo_response))

            # First call — hits the API
            result1 = await get_repo_info("octocat", "Hello-World")
            assert result1["stars"] == 100
            assert route.call_count == 1

            # Second call — served from cache
            result2 = await get_repo_info("octocat", "Hello-World")
            assert result2["stars"] == 100
            assert route.call_count == 1  # still 1 — no second API call

        # Clean up
        get_cache().clear()
