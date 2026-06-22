"""Pipeline entry point.

Builds the ``FilterChain`` (Facade over all concrete filters) with a
``LoggingObserver`` and runs it. New filters are appended to ``FILTERS`` in
pipeline order as they are implemented.

Run with ``make run`` (delegates to ``docker compose run --rm app uv run
python -m src.main``).
"""

from src.comment_graph import CommentGraphFilter
from src.preprocessing import PreprocessingFilter
from src.shared.filter_base import AbstractFilter
from src.shared.observers import LoggingObserver
from src.shared.pipeline import FilterChain
from src.tree import TreeFilter
from src.word_graph import WordGraphFilter
from src.sentence_graph import SentenceGraphFilter


# Ordered list of pipeline filters. Extend as downstream filters land.
# CommentGraphFilter (Filter 5) consumes sentence_graph.json + preprocessed.json;
# WordGraphFilter (3) and SentenceGraphFilter (4) slot in above it once landed.
FILTERS: list[AbstractFilter] = [
    PreprocessingFilter(),
    TreeFilter(),
    CommentGraphFilter(),
    WordGraphFilter(),
    SentenceGraphFilter(),
]


def main() -> None:
    """Instantiate the filter chain and run the full pipeline."""
    chain = FilterChain(FILTERS, observers=[LoggingObserver()])
    chain.run()


if __name__ == "__main__":
    main()
