"""Observer pattern — PipelineObserver and LoggingObserver.

Observers decouple pipeline lifecycle events (start, complete, skip) from
the filters and the chain itself. Register instances with FilterChain to
react to these events without modifying any filter or pipeline code.
"""

from abc import ABC, abstractmethod


class PipelineObserver(ABC):
    """Abstract observer for pipeline lifecycle events (Observer pattern).

    Subclass this to add custom behavior on filter start, completion, or skip.
    Instances are registered with ``FilterChain`` and must not modify filter
    inputs, outputs, or pipeline state.
    """

    @abstractmethod
    def on_start(self, filter_name: str) -> None:
        """Called immediately before a filter begins execution.

        Args:
            filter_name: Value of ``AbstractFilter.name`` for the starting filter.
        """

    @abstractmethod
    def on_complete(self, filter_name: str, elapsed: float) -> None:
        """Called after a filter finishes execution successfully.

        Args:
            filter_name: Value of ``AbstractFilter.name`` for the completed filter.
            elapsed: Wall-clock elapsed time in seconds.
        """

    @abstractmethod
    def on_skip(self, filter_name: str) -> None:
        """Called when a filter is skipped due to the ``--from`` flag.

        Args:
            filter_name: Value of ``AbstractFilter.name`` for the skipped filter.
        """


class LoggingObserver(PipelineObserver):
    """Concrete observer that prints timestamped status lines to stdout."""

    def on_start(self, filter_name: str) -> None:
        """Print a start message for the given filter.

        Args:
            filter_name: Name of the filter starting.
        """
        print(f"[{filter_name}] starting...")

    def on_complete(self, filter_name: str, elapsed: float) -> None:
        """Print a completion message with elapsed time.

        Args:
            filter_name: Name of the filter that completed.
            elapsed: Wall-clock time in seconds.
        """
        print(f"[{filter_name}] done ({elapsed:.2f}s)")

    def on_skip(self, filter_name: str) -> None:
        """Print a skip message for the given filter.

        Args:
            filter_name: Name of the filter being skipped.
        """
        print(f"[{filter_name}] skipped")
