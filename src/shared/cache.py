"""Redis cache backend for pipeline filter results.

Provides a single ``RedisCache`` class used by ``AbstractFilter`` to store and
retrieve filter results between runs. Results are serialized with pickle and
stored under the ``filter:`` key prefix.

Usage is mediated through the module-level ``get_cache()`` factory, which
returns a lazily initialized singleton. Concrete filters never import this
module directly — ``AbstractFilter`` calls it internally.
"""

import pickle
from typing import Any

import redis as redis_lib

from src.config import REDIS_URL

_PREFIX = "filter"
_instance: "RedisCache | None" = None


def get_cache() -> "RedisCache":
    """Return the module-level RedisCache singleton, creating it on first call.

    Returns:
        Shared ``RedisCache`` instance.
    """
    global _instance
    if _instance is None:
        _instance = RedisCache()
    return _instance


class RedisCache:
    """Store and retrieve filter results in Redis using pickle serialization.

    Keys follow the pattern ``filter:<filter_name>``,
    e.g. ``filter:word_graph``, ``filter:community_detection``.
    """

    def __init__(self) -> None:
        """Initialize the Redis client from ``REDIS_URL``."""
        self._client = redis_lib.from_url(REDIS_URL, decode_responses=False)

    def _key(self, name: str) -> str:
        """Return the Redis key for a filter result.

        Args:
            name: Filter name (``AbstractFilter.name``).

        Returns:
            Prefixed key string, e.g. ``"filter:word_graph"``.
        """
        return f"{_PREFIX}:{name}"

    def get(self, name: str) -> Any | None:
        """Retrieve a cached filter result.

        Args:
            name: Filter name (``AbstractFilter.name``).

        Returns:
            Deserialized Python object, or ``None`` on a cache miss.
        """
        raw = self._client.get(self._key(name))
        if raw is None:
            return None
        return pickle.loads(raw)

    def set(self, name: str, obj: Any) -> None:
        """Cache a filter result indefinitely.

        Args:
            name: Filter name (``AbstractFilter.name``).
            obj: Python object to serialize and store.
        """
        self._client.set(self._key(name), pickle.dumps(obj))

    def delete(self, name: str) -> None:
        """Remove a single cached filter result.

        Args:
            name: Filter name whose cache entry should be invalidated.
        """
        self._client.delete(self._key(name))

    def flush(self) -> None:
        """Remove all cached filter results (equivalent to ``make clean``).

        Only deletes keys matching the ``filter:*`` pattern — other Redis
        data in the same database is not affected.
        """
        keys = self._client.keys(f"{_PREFIX}:*")
        if keys:
            self._client.delete(*keys)
