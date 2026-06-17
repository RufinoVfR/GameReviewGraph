"""Template Method pattern — AbstractFilter.

Every concrete filter in the pipeline inherits from this class and implements
only ``process()``. The ``execute()`` method is the invariant skeleton that
reads from S3, delegates to ``process()``, writes back to S3, and manages
the Redis cache — all without any action from the subclass.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.config import S3_KEYS
from src.shared.cache import get_cache
from src.shared.storage import get_storage


class AbstractFilter(ABC):
    """Base class for all pipeline filters (Template Method pattern).

    Subclasses must declare three class-level attributes and implement
    ``process()``. All I/O and caching is handled by ``execute()`` via the
    S3 storage backend (``src/shared/storage.py``) and the Redis cache backend
    (``src/shared/cache.py``).

    Class attributes:
        name: Unique slug identifying this filter (e.g. ``"word_graph"``).
        input_key: Key into ``S3_KEYS`` for the filter's primary input artifact.
        output_key: Key into ``S3_KEYS`` for the filter's output artifact.
        output_format: ``"json"`` (default) or ``"text"`` for plain-text output.
        extra_input_keys: Additional ``S3_KEYS`` keys required by multi-input
            filters (e.g. ``["tree"]`` for ``sentence_graph``). When non-empty,
            ``process()`` receives a dict instead of a plain object — see
            ``_load_input()`` for the exact shape.
    """

    name: str
    input_key: str
    output_key: str
    output_format: str = "json"
    extra_input_keys: list[str] = []

    def execute(self, use_cache: bool = True) -> None:
        """Run the full filter lifecycle: cache check → load → process → save.

        On a Redis cache hit, the cached result is written to S3 and
        ``process()`` is skipped. On a miss, ``process()`` is called, the
        result is written to S3, and then cached in Redis.

        Args:
            use_cache: When ``False``, the Redis cache is **not** read, so
                ``process()`` always runs (force reprocessing). The fresh result
                is still written to S3 and saved to the cache, refreshing any
                stale entry. Defaults to ``True``.
        """
        if use_cache:
            cached = self._load_cache()
            if cached is not None:
                self._write_output(cached)
                return
        data = self._load_input()
        result = self.process(data)
        self._write_output(result)
        self._save_cache(result)

    @abstractmethod
    def process(self, data: Any) -> Any:
        """Apply the filter's domain transformation.

        Args:
            data: Python object loaded from the S3 input artifact.

        Returns:
            Transformed result to be written to the S3 output artifact.
        """

    def _load_input(self) -> Any:
        """Download the filter's input artifact(s) from S3.

        When ``extra_input_keys`` is empty (the default), returns the primary
        artifact as a plain Python object — identical to the previous behaviour,
        no changes needed in single-input filters.

        When ``extra_input_keys`` is non-empty, returns a dict of the form::

            {
                "primary": <primary artifact>,
                "<extra_key_1>": <artifact>,
                ...
            }

        Multi-input filters declare ``extra_input_keys`` at class level and
        destructure this dict inside ``process()``.

        Returns:
            Parsed JSON object, or a dict of multiple parsed JSON objects.
        """
        primary = get_storage().read_json(S3_KEYS[self.input_key])
        if not self.extra_input_keys:
            return primary
        result: dict[str, Any] = {"primary": primary}
        for key in self.extra_input_keys:
            result[key] = get_storage().read_json(S3_KEYS[key])
        return result

    def _write_output(self, result: Any) -> None:
        """Upload the filter's result to S3.

        Uses ``write_text`` for ``output_format == "text"`` (e.g. report.txt),
        and ``write_json`` for all other formats.

        Args:
            result: Python object to serialize and upload.
        """
        name = S3_KEYS[self.output_key]
        if self.output_format == "text":
            get_storage().write_text(name, result)
        else:
            get_storage().write_json(name, result)

    def _load_cache(self) -> Any | None:
        """Retrieve the cached result for this filter from Redis.

        Returns:
            Deserialized object on a cache hit, or ``None`` on a miss.
        """
        return get_cache().get(self.name)

    def _save_cache(self, result: Any) -> None:
        """Persist this filter's result in Redis.

        Args:
            result: Python object to cache.
        """
        get_cache().set(self.name, result)
