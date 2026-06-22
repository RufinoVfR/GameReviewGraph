"""CommunityDetectionFilter — Filter 7 of the pipeline.

Reads the unified ``final_graph.json`` produced by Filter 6, reduces it to a
Minimum Spanning Tree (Prim), and applies progressive edge cutting to partition
the graph into K communities. Only **relational** edges (connecting nodes of the
same level — ``w_↔w_``, ``s_↔s_``, ``c_↔c_``) are candidates for removal;
**hierarchical** edges (``w_→s_``, ``s_→c_``) are excluded from cutting so the
structural links between levels are preserved in every community.

The algorithm terminates when exactly K=10 communities are found or when no
more cuttable relational edges remain (whichever comes first). In the latter
case the achieved community count is logged and the partial result is returned.

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()``.
"""

import argparse
import logging

from src.config import K
from src.shared.filter_base import AbstractFilter
from src.shared.graph import (
    connected_components,
    copy_graph,
    count_components,
    deserialize_graph,
    has_edge,
    iter_edges,
    minimum_spanning_tree,
    neighbor_count,
    remove_edge,
)
from src.types import Communities, Graph

logger = logging.getLogger(__name__)

_LEVEL_PREFIXES: tuple[str, ...] = ("w_", "s_", "c_")


def _is_relational(u: str, v: str) -> bool:
    """Return True if edge (u, v) connects nodes at the same graph level.

    Relational edges link nodes that share a level prefix (``w_↔w_``,
    ``s_↔s_``, ``c_↔c_``) and represent semantic similarity. Hierarchical
    edges (``w_→s_``, ``s_→c_``) cross level boundaries and must be excluded
    from progressive cutting so the structural containment tree is preserved.

    Args:
        u: First node key (e.g. ``"w_fps"`` or ``"s_5"``).
        v: Second node key (e.g. ``"w_lag"`` or ``"c_3"``).

    Returns:
        True if both nodes share the same level prefix, False otherwise.
    """
    for prefix in _LEVEL_PREFIXES:
        if u.startswith(prefix) and v.startswith(prefix):
            return True
    return False


def _cut_edges(mst: Graph, k: int) -> Communities:
    """Apply progressive edge cutting on an MST, skipping hierarchical edges.

    Iterates the MST's edges in ascending weight order and removes each
    relational edge whose both endpoints have degree > 1. After every removal
    the component count is checked; the loop stops as soon as ``k`` components
    are reached or no more cuttable relational edges remain. Hierarchical edges
    (those crossing level boundaries) are never removed, preserving the
    structural links between word, sentence, and comment nodes within each
    community.

    Args:
        mst: Working copy of the Minimum Spanning Tree. Mutated in place.
        k: Target number of communities.

    Returns:
        Mapping of 1-indexed community id to the list of node keys in that
        community, derived from the connected components of the modified MST.
    """
    sorted_edges = sorted(iter_edges(mst), key=lambda e: e[2])
    for u, v, _ in sorted_edges:
        if not has_edge(mst, u, v):
            continue
        if not _is_relational(u, v):
            continue
        if neighbor_count(mst, u) > 1 and neighbor_count(mst, v) > 1:
            remove_edge(mst, u, v)
            if count_components(mst) >= k:
                break
    components = connected_components(mst)
    return {i + 1: component for i, component in enumerate(components)}


class CommunityDetectionFilter(AbstractFilter):
    """Detect communities in the final graph via MST + progressive edge cutting (Filter 7).

    Reads ``final_graph.json``, builds a Minimum Spanning Tree (Prim, O(V²)),
    and iteratively removes the weakest relational edges whose both endpoints
    have degree > 1 until K=10 communities are found or no more cuttable
    edges remain. Hierarchical edges (``w_→s_``, ``s_→c_``) are never cut so
    the structural containment links between levels are preserved in the output.

    The result is written to ``communities.json`` as a mapping of 1-indexed
    community id (string key for JSON compatibility) to the list of node keys
    (``w_``, ``s_``, ``c_`` prefixed) belonging to that community.
    """

    name = "community_detection"
    input_key = "final_graph"
    output_key = "communities"

    def process(self, data: dict) -> dict:
        """Build communities from the unified final graph.

        Deserializes the graph, constructs its MST via Prim's algorithm, and
        applies progressive edge cutting restricted to relational edges. If
        the target of K=10 communities cannot be achieved (too few cuttable
        relational edges survive in the MST), the achieved count is logged and
        the partial result is returned unchanged.

        Args:
            data: Serialized final graph dict (output of ``serialize_graph``,
                loaded from MinIO by ``execute()``).

        Returns:
            Dict mapping community id (str, 1-indexed) to a list of node keys.
            Keys are strings because JSON does not support integer keys;
            downstream consumers must cast them to ``int`` when needed.
        """
        graph = deserialize_graph(data)
        mst = minimum_spanning_tree(copy_graph(graph))
        communities = _cut_edges(mst, K)
        achieved = len(communities)
        if achieved < K:
            logger.warning(
                "community_detection: target K=%d not reached — achieved %d "
                "communities (MST had too few cuttable relational edges).",
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
