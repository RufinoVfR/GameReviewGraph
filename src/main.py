"""Pipeline entry point.

Builds the ``FilterChain`` (Facade over all concrete filters) with a
``LoggingObserver`` and runs it. New filters are appended to ``FILTERS`` in
pipeline order as they are implemented.

Run with ``make run`` (delegates to ``docker compose run --rm app uv run
python -m src.main``).
"""

from src.comment_graph import CommentGraphFilter
from src.community_detection import CommunityDetectionFilter
from src.final_graph import FinalGraphFilter
from src.metrics import MetricsFilter
from src.preprocessing import PreprocessingFilter
from src.sentence_graph import SentenceGraphFilter
from src.shared.filter_base import AbstractFilter
from src.shared.observers import LoggingObserver
from src.shared.pipeline import FilterChain
from src.tree import TreeFilter
from src.word_graph import WordGraphFilter

# Ordered list of pipeline filters. Extend as downstream filters land.
FILTERS: list[AbstractFilter] = [
    PreprocessingFilter(),
    TreeFilter(),
    WordGraphFilter(),
    SentenceGraphFilter(),
    CommentGraphFilter(),
    FinalGraphFilter(),
    CommunityDetectionFilter(),
    MetricsFilter(),
]


def main() -> None:
    """Instantiate the filter chain and run the full pipeline."""
    chain = FilterChain(FILTERS, observers=[LoggingObserver()])
    chain.run()


if __name__ == "__main__":
    main()
