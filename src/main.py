"""Pipeline entry point.

Builds the ``FilterChain`` (Facade over all concrete filters) with a
``LoggingObserver`` and runs it. New filters are appended to ``FILTERS`` in
pipeline order as they are implemented.

Run with ``make run`` (delegates to ``docker compose run --rm app uv run
python -m src.main``).
"""

from src.analysis import AnalysisFilter
from src.comment_graph import CommentGraphFilter
from src.community_detection import CommunityDetectionFilter
from src.final_graph import FinalGraphFilter
from src.metrics import MetricsFilter
from src.preprocessing import PreprocessingFilter
from src.report_text import ReportTextFilter
from src.sentence_graph import SentenceGraphFilter
from src.shared.filter_base import AbstractFilter
from src.shared.observers import LoggingObserver
from src.shared.pipeline import FilterChain
from src.shared.strategies import CommentSubgraphStrategy
from src.tree import TreeFilter
from src.word_graph import WordGraphFilter

# Ordered list of pipeline filters. Extend as downstream filters land.
#
# The community-detection filter is wired to the comment-subgraph strategy
# (method 4 of the final-report benchmark). Although greedy modularity scores a
# higher global Q (≈ 0.62), that Q is dominated by the word/sentence structure
# and the greedy partition collapses all 200 comments into a single community —
# degenerate for the frontend, which navigates comment communities. Method 4
# partitions the c_↔c_ subgraph into 10 balanced comment communities (no
# singletons), the cleanest comment grouping for the explorer. communities.json
# — and therefore metrics.json and the frontend bundle — carry this partition.
# The full 5-method comparison is still produced independently by AnalysisFilter.
FILTERS: list[AbstractFilter] = [
    PreprocessingFilter(),
    TreeFilter(),
    WordGraphFilter(),
    SentenceGraphFilter(),
    CommentGraphFilter(),
    FinalGraphFilter(),
    CommunityDetectionFilter(strategy=CommentSubgraphStrategy()),
    MetricsFilter(),
    AnalysisFilter(),
    ReportTextFilter(),
]


def main() -> None:
    """Instantiate the filter chain and run the full pipeline."""
    chain = FilterChain(FILTERS, observers=[LoggingObserver()])
    chain.run()


if __name__ == "__main__":
    main()
