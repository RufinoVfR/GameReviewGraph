"""CommunityDetectionFilter — Filter 7 of the pipeline.

Reads the unified ``final_graph.json`` produced by Filter 6 and partitions it
into communities via an injectable ``CommunityDetectionStrategy`` (Strategy
pattern). The default strategy — ``ProgressiveEdgeCuttingStrategy`` — reduces the
graph to a Minimum Spanning Tree (Prim) and progressively cuts the weakest
**relational** edges (``w_↔w_``, ``s_↔s_``, ``c_↔c_``); **hierarchical** edges
(``w_→s_``, ``s_→c_``) are never cut so the structural links between levels are
preserved in every community.

All traversal, MST construction, and the cutting loop live in
``src.shared.graph`` and ``src.shared.strategies`` — this filter only wires a
strategy to the Template Method. The alternative strategies compared in the
final report (US14) are injected the same way, without touching this class.

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()``.
"""

import argparse
import logging

from src.config import K
from src.shared.filter_base import AbstractFilter
from src.shared.graph import deserialize_graph
from src.shared.strategies import (
    CommunityDetectionStrategy,
    ProgressiveEdgeCuttingStrategy,
)

logger = logging.getLogger(__name__)


class CommunityDetectionFilter(AbstractFilter):
    """Detect communities in the final graph via an injectable strategy (Filter 7).

    Reads ``final_graph.json`` and delegates partitioning to the configured
    ``CommunityDetectionStrategy`` (default: ``ProgressiveEdgeCuttingStrategy`` —
    MST + progressive cutting of the weakest relational edges until K=10
    communities are found or no more cuttable edges remain). Hierarchical edges
    are never cut by the default strategy, so the containment links between
    levels survive in the output.

    The result is written to ``communities.json`` as a mapping of 1-indexed
    community id (string key for JSON compatibility) to the list of node keys
    (``w_``, ``s_``, ``c_`` prefixed) belonging to that community.
    """

    name = "community_detection"
    input_key = "final_graph"
    output_key = "communities"

    def __init__(self, strategy: CommunityDetectionStrategy | None = None) -> None:
        """Wire the community-detection strategy to the filter.

        Args:
            strategy: Partitioning algorithm to use. Defaults to
                ``ProgressiveEdgeCuttingStrategy`` (the enunciado's baseline).
                Inject an alternative (e.g. the methods compared in the final
                report) without subclassing the filter.
        """
        super().__init__()
        self.strategy = strategy or ProgressiveEdgeCuttingStrategy()

    def process(self, data: dict) -> dict:
        """Build communities from the unified final graph.

        Deserializes the graph and delegates to the configured strategy. If the
        target of K=10 communities cannot be achieved (e.g. too few cuttable
        edges survive), the achieved count is logged and the partial result is
        returned unchanged.

        Args:
            data: Serialized final graph dict (output of ``serialize_graph``,
                loaded from MinIO by ``execute()``).

        Returns:
            Dict mapping community id (str, 1-indexed) to a list of node keys.
            Keys are strings because JSON does not support integer keys;
            downstream consumers must cast them to ``int`` when needed.
        """
        graph = deserialize_graph(data)
        communities = self.strategy.detect(graph, K)
        achieved = len(communities)

        if achieved < K:
            logger.warning(
                "community_detection: target K=%d not reached — achieved %d "
                "communities (too few cuttable edges for this strategy).",
                K,
                achieved,
            )
        else:
            logger.info(
                "community_detection: found %d communities (K=%d).", achieved, K
            )

        return {str(community_id): nodes for community_id, nodes in communities.items()}


def main() -> None:
    """Parse CLI flags and run the community detection filter."""
    parser = argparse.ArgumentParser(prog="python -m src.community_detection")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force reprocessing, ignoring any cached result in Redis.",
    )
    args = parser.parse_args()
    CommunityDetectionFilter().execute(use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
