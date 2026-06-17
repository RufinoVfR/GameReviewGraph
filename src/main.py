"""Pipeline entry point.

Builds the ``FilterChain`` (Facade over all concrete filters) with a
``LoggingObserver`` and runs it. New filters are appended to ``FILTERS`` in
pipeline order as they are implemented.

Run with ``make run`` (delegates to ``docker compose run --rm app uv run
python -m src.main``).
"""

from src.preprocessing import PreprocessingFilter
from src.shared.filter_base import AbstractFilter
from src.shared.observers import LoggingObserver
from src.shared.pipeline import FilterChain

# Ordered list of pipeline filters. Extend as downstream filters land.
FILTERS: list[AbstractFilter] = [
    PreprocessingFilter(),
]


def main() -> None:
    """Instantiate the filter chain and run the full pipeline."""
    chain = FilterChain(FILTERS, observers=[LoggingObserver()])
    chain.run()


if __name__ == "__main__":
    main()
