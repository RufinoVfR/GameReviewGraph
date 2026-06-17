"""Strategy pattern — CommunityDetectionStrategy.

Defines the abstract strategy and the default implementation
(ProgressiveEdgeCuttingStrategy) for community detection in the final graph.
Inject an alternative strategy into CommunityDetectionFilter to swap
algorithms without modifying the filter.
"""

from abc import ABC, abstractmethod

from src.shared.graph import (
    copy_graph,
    count_components,
    connected_components,
    degree,
    has_edge,
    iter_edges,
    remove_edge,
)
from src.types import Communities, Graph


class CommunityDetectionStrategy(ABC):
    """Abstract strategy for graph community detection (Strategy pattern).

    Subclass this to provide an alternative partitioning algorithm.
    The default implementation is ``ProgressiveEdgeCuttingStrategy``.
    """

    @abstractmethod
    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition graph nodes into at most k communities.

        Args:
            graph: Unified adjacency dict (final_graph.json format).
                   Must not be mutated — implementations must copy if needed.
            k: Target number of communities.

        Returns:
            Mapping of community_id (1-indexed int) to list of node keys.
        """


class ProgressiveEdgeCuttingStrategy(CommunityDetectionStrategy):
    """Default community detection via progressive edge cutting.

    Algorithm:
        1. Sort all edges ascending by weight.
        2. For each edge (u, v): if degree(u) > 1 and degree(v) > 1, remove it.
        3. After each removal, count connected components via BFS.
        4. Stop when components >= k or no more removable edges remain.

    The input graph is never mutated; ``copy_graph`` is called before any
    edge removal. All traversal is delegated to ``src.shared.graph``.
    """

    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition graph into k communities by progressive edge cutting.

        Args:
            graph: Unified graph adjacency dict. Not mutated.
            k: Target number of communities to detect.

        Returns:
            Mapping of community_id (1-indexed) to list of node keys.
        """
        working = copy_graph(graph)
        sorted_edges = sorted(iter_edges(working), key=lambda e: e[2])
        for u, v, _ in sorted_edges:
            if not has_edge(working, u, v):
                continue
            if degree(working, u) > 1 and degree(working, v) > 1:
                remove_edge(working, u, v)
                if count_components(working) >= k:
                    break
        components = connected_components(working)
        return {i + 1: component for i, component in enumerate(components)}
