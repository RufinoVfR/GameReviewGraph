"""Chain of Responsibility + Facade pattern — FilterChain.

FilterChain is the single entry point to the pipeline. It walks the ordered
list of filters in sequence, optionally starting from a named filter, and
notifies all registered observers about lifecycle events. Exceptions inside
filters propagate immediately (fail-fast).
"""

import time

from src.shared.filter_base import AbstractFilter
from src.shared.observers import PipelineObserver


class FilterChain:
    """Ordered chain of pipeline filters (Chain of Responsibility + Facade).

    Acts as a Facade over all concrete filters: callers in ``main.py`` interact
    only with ``run()``. Internally it walks the handler chain in order,
    skipping filters before ``from_filter`` when specified, and notifying all
    registered observers at each lifecycle event.
    """

    def __init__(
        self,
        filters: list[AbstractFilter],
        observers: list[PipelineObserver] | None = None,
    ) -> None:
        """Initialize the chain with an ordered list of filters.

        Args:
            filters: Ordered list of concrete filters. Execution follows this order.
            observers: Optional observers to notify on lifecycle events.
        """
        self._filters: list[AbstractFilter] = list(filters)
        self._observers: list[PipelineObserver] = list(observers or [])

    def run(self, from_filter: str | None = None) -> None:
        """Execute filters in order, optionally starting from ``from_filter``.

        Filters before ``from_filter`` receive an ``on_skip`` notification and
        are not executed. If ``from_filter`` is ``None``, all filters run.
        Any uncaught exception inside a filter propagates immediately and
        aborts the rest of the chain.

        Args:
            from_filter: Value of ``AbstractFilter.name`` to start from.
                         ``None`` means run all filters.

        Raises:
            ValueError: If ``from_filter`` does not match any filter name.
        """
        if from_filter is not None:
            known = {f.name for f in self._filters}
            if from_filter not in known:
                raise ValueError(
                    f"Unknown filter name: {from_filter!r}. "
                    f"Valid names: {sorted(known)}"
                )

        skipping = from_filter is not None
        for f in self._filters:
            if skipping:
                if f.name == from_filter:
                    skipping = False
                else:
                    self._notify_skip(f.name)
                    continue

            self._notify_start(f.name)
            start = time.perf_counter()
            f.execute()
            elapsed = time.perf_counter() - start
            self._notify_complete(f.name, elapsed)

    def add_filter(self, f: AbstractFilter) -> None:
        """Append a filter to the end of the chain.

        Args:
            f: Concrete filter instance to add.
        """
        self._filters.append(f)

    def add_observer(self, o: PipelineObserver) -> None:
        """Register an observer to receive lifecycle events.

        Args:
            o: Observer instance to add.
        """
        self._observers.append(o)

    def _notify_start(self, filter_name: str) -> None:
        """Fire the on_start event to all observers.

        Args:
            filter_name: Name of the filter about to start.
        """
        for obs in self._observers:
            try:
                obs.on_start(filter_name)
            except Exception:
                pass

    def _notify_complete(self, filter_name: str, elapsed: float) -> None:
        """Fire the on_complete event to all observers.

        Args:
            filter_name: Name of the filter that completed.
            elapsed: Elapsed time in seconds.
        """
        for obs in self._observers:
            try:
                obs.on_complete(filter_name, elapsed)
            except Exception:
                pass

    def _notify_skip(self, filter_name: str) -> None:
        """Fire the on_skip event to all observers.

        Args:
            filter_name: Name of the filter being skipped.
        """
        for obs in self._observers:
            try:
                obs.on_skip(filter_name)
            except Exception:
                pass
