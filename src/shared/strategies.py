"""Strategy pattern — CommunityDetectionStrategy.

Defines the abstract strategy and the default implementation
(ProgressiveEdgeCuttingStrategy) for community detection in the final graph.
Inject an alternative strategy into CommunityDetectionFilter to swap
algorithms without modifying the filter.
"""

from abc import ABC, abstractmethod

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

    The input graph is never mutated; a shallow copy of each adjacency dict
    is made before any edges are removed.
    """

    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition graph into k communities by progressive edge cutting.

        Args:
            graph: Unified graph adjacency dict. Not mutated.
            k: Target number of communities to detect.

        Returns:
            Mapping of community_id (1-indexed) to list of node keys.
        """
        working = self._copy(graph)
        for u, v, _ in self._sort_edges(working):
            if u not in working or v not in working[u]:
                continue
            if self._degree(working, u) > 1 and self._degree(working, v) > 1:
                self._remove_edge(working, u, v)
                if self._count_components(working) >= k:
                    break
        return self._label_components(working)

    def _copy(self, graph: Graph) -> Graph:
        """Return a shallow copy of the adjacency dict.

        Args:
            graph: Source adjacency dict.

        Returns:
            New dict where each neighbor dict is also a new dict.
        """
        return {node: dict(neighbors) for node, neighbors in graph.items()}

    def _sort_edges(self, graph: Graph) -> list[tuple[str, str, float]]:
        """Return all unique edges sorted ascending by weight.

        Args:
            graph: Adjacency dict to extract edges from.

        Returns:
            List of ``(u, v, weight)`` tuples, each undirected edge once.
        """
        seen: set[frozenset[str]] = set()
        edges: list[tuple[str, str, float]] = []
        for u, neighbors in graph.items():
            for v, w in neighbors.items():
                key = frozenset({u, v})
                if key not in seen:
                    seen.add(key)
                    edges.append((u, v, w))
        edges.sort(key=lambda e: e[2])
        return edges

    def _degree(self, graph: Graph, node: str) -> int:
        """Return the number of neighbors of a node.

        Args:
            graph: Adjacency dict.
            node: Node key to query.

        Returns:
            Number of adjacent nodes.
        """
        return len(graph.get(node, {}))

    def _remove_edge(self, graph: Graph, u: str, v: str) -> None:
        """Remove the undirected edge (u, v) from the adjacency dict.

        Args:
            graph: Adjacency dict to mutate.
            u: First endpoint.
            v: Second endpoint.
        """
        graph[u].pop(v, None)
        graph[v].pop(u, None)

    def _count_components(self, graph: Graph) -> int:
        """Count connected components via BFS.

        Args:
            graph: Adjacency dict.

        Returns:
            Number of connected components.
        """
        visited: set[str] = set()
        count = 0
        for node in graph:
            if node not in visited:
                self._bfs(graph, node, visited)
                count += 1
        return count

    def _bfs(self, graph: Graph, start: str, visited: set[str]) -> None:
        """Mark all nodes reachable from ``start`` via BFS.

        Args:
            graph: Adjacency dict.
            start: Starting node key.
            visited: Set updated in place with all reachable node keys.
        """
        queue = [start]
        visited.add(start)
        while queue:
            node = queue.pop(0)
            for neighbor in graph.get(node, {}):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

    def _label_components(self, graph: Graph) -> Communities:
        """Assign 1-indexed community IDs to connected components.

        Args:
            graph: Adjacency dict after edge cutting.

        Returns:
            Mapping of community_id (1-indexed) to list of node keys.
        """
        visited: set[str] = set()
        communities: Communities = {}
        community_id = 1
        for node in graph:
            if node not in visited:
                component: list[str] = []
                self._bfs_collect(graph, node, visited, component)
                communities[community_id] = component
                community_id += 1
        return communities

    def _bfs_collect(
        self,
        graph: Graph,
        start: str,
        visited: set[str],
        component: list[str],
    ) -> None:
        """Collect all nodes reachable from ``start`` into ``component``.

        Args:
            graph: Adjacency dict.
            start: Starting node key.
            visited: Set updated in place with visited node keys.
            component: List updated in place with collected node keys.
        """
        queue = [start]
        visited.add(start)
        while queue:
            node = queue.pop(0)
            component.append(node)
            for neighbor in graph.get(node, {}):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
