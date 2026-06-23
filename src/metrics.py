"""MetricsFilter — Filter 8 of the pipeline.

Computes the quality metrics of a community partition:

- **Weighted degree centrality** (US12) for each vertex inside its community,
  ``C(v) = Σ weight(v, u)`` over neighbours ``u`` in the same community, and the
  N most central word nodes per community as the topic's representative terms.
- **Modularity Q** (US13) of the whole partition,
  ``Q = (1/2m) Σ_ij [A_ij − k_i·k_j/2m] δ(c_i, c_j)``, an objective score of how
  much denser the intra-community links are than chance.

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()``.
"""

from typing import Any

from src.config import N_CENTRAL_TERMS
from src.shared.filter_base import AbstractFilter
from src.shared.graph import deserialize_graph, iter_edges, total_edge_weight
from src.types import Graph


def weighted_degree_centrality(graph: Graph) -> dict[str, float]:
    """Calculate the weighted degree centrality of each vertex.

    The centrality of a vertex v is the sum of the weights of all edges
    incident to v. Equivalently, it is the sum of all entries in the
    corresponding row of the adjacency matrix.

    Time complexity: O(|E|) via the precomputed adjacency row sum per vertex.

    Args:
        graph: The input graph.

    Returns:
        A dict mapping node_key -> weighted_degree_centrality.
    """
    return {node_key: total_edge_weight(graph, node_key) for node_key in graph.nodes}


def calculate_modularity(graph: Graph, components: dict[int, list[str]]) -> float:
    """Compute the weighted modularity Q of a community partition.

    Implements, from scratch, the Newman weighted modularity::

        Q = (1 / 2m) × Σ_ij [A_ij − k_i·k_j / 2m] × δ(c_i, c_j)

    where ``A_ij`` is the weight of edge (i, j) (``0`` if absent), ``k_i`` the
    weighted degree of vertex ``i`` (reusing ``weighted_degree_centrality`` from
    US12), ``2m`` the sum of all weighted degrees, and ``δ(c_i, c_j)`` is ``1``
    iff ``i`` and ``j`` belong to the same community. ``m`` is therefore the
    total undirected edge weight (each edge counted once).

    To avoid the O(|V|²) double loop over every vertex pair, Q is computed via
    the algebraically equivalent per-community decomposition::

        Q = Σ_C [ 2·W_in(C) / 2m − (Σ_tot(C) / 2m)² ]

    where ``W_in(C)`` is the summed weight of edges with both endpoints in ``C``
    (each counted once) and ``Σ_tot(C)`` the summed weighted degree of ``C``.
    This walks each edge once — O(|E|).

    Args:
        graph: The graph the partition is defined over (the final graph after
            cutting). Edges and weights are read from its adjacency matrix.
        components: Mapping of community_id to the list of node keys in it.

    Returns:
        Modularity Q as a float in ``[-1, 1]``. Returns ``0.0`` for a graph with
        no edges (``2m == 0``), where Q is undefined.
    """
    degrees = weighted_degree_centrality(graph)
    m2 = sum(degrees.values())  # 2m — the sum of all weighted degrees
    if m2 == 0.0:
        return 0.0

    community_of: dict[str, int] = {
        node: community_id
        for community_id, nodes in components.items()
        for node in nodes
    }

    internal_weight: dict[int, float] = {}  # Σ edge weight inside each community
    for u, v, weight in iter_edges(graph):
        community = community_of.get(u)
        if community is not None and community == community_of.get(v):
            internal_weight[community] = internal_weight.get(community, 0.0) + weight

    degree_sum: dict[int, float] = {}  # Σ_tot(C): summed weighted degree per community
    for node, community in community_of.items():
        degree_sum[community] = degree_sum.get(community, 0.0) + degrees.get(node, 0.0)

    modularity = 0.0
    for community, total_degree in degree_sum.items():
        within = internal_weight.get(community, 0.0)
        modularity += (2.0 * within) / m2 - (total_degree / m2) ** 2
    return modularity


def _normalize_communities(raw_communities: dict[Any, list[str]]) -> dict[int, list[str]]:
    """Normalize community identifiers to integers.

    Args:
        raw_communities: Community mapping with possibly-string keys
            (JSON deserializes int keys as strings).

    Returns:
        The same mapping with int keys.
    """
    return {int(community_id): list(nodes) for community_id, nodes in raw_communities.items()}


def _community_centrality(graph: Graph, nodes: list[str]) -> dict[str, float]:
    """Compute weighted degree centrality restricted to one community.

    Args:
        graph: The full graph (edges outside the community are ignored).
        nodes: Node keys belonging to the community.

    Returns:
        A dict mapping node_key -> centrality computed only over edges
        whose other endpoint is also inside the community.
    """
    community_nodes = [node for node in nodes if node in graph.index]
    community_indices = {node: graph.index[node] for node in community_nodes}

    centrality: dict[str, float] = {}
    for node_key in community_nodes:
        row_index = community_indices[node_key]
        total = 0.0
        for other_key in community_nodes:
            if other_key == node_key:
                continue
            total += graph.matrix[row_index][community_indices[other_key]]
        centrality[node_key] = total
    return centrality


def get_top_terms(
    components: dict[int, list[str]],
    graph: Graph,
    centrality: dict[str, float],
    n: int,
) -> dict[int, list[str]]:
    """Extract the top N word nodes by centrality from each community.

    Filters each community to include only word-level nodes (keys with prefix
    ``w_``), then selects the n highest-centrality words. If a community has
    fewer than n words, all words in that community are included.

    Args:
        components: Community mapping (community_id -> [node_keys, ...]).
        graph: The graph containing the nodes (kept for interface compatibility).
        centrality: The precomputed centrality dict (node_key -> centrality).
        n: Number of top terms to extract per community.

    Returns:
        A dict mapping community_id -> [top n word nodes, ...], sorted by
        centrality descending and node key ascending as a tie-breaker.
    """
    _ = graph
    top_terms: dict[int, list[str]] = {}

    for community_id, nodes in components.items():
        word_nodes = [node_key for node_key in nodes if node_key.startswith("w_")]
        sorted_words = sorted(
            word_nodes,
            key=lambda node_key: (-centrality.get(node_key, 0.0), node_key),
        )
        top_terms[community_id] = sorted_words[:n]

    return top_terms


class MetricsFilter(AbstractFilter):
    """Compute weighted degree centrality and extract top terms by community."""

    name = "metrics"
    input_key = "communities"
    extra_input_keys = ["final_graph"]
    output_key = "metrics"

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process communities and the unified graph to compute metrics.

        Computes, per community, the intra-community weighted degree centrality
        and its top central terms, plus the global modularity Q of the whole
        partition as an objective quality score.

        Args:
            data: Multi-input payload ``{"primary": <communities dict>,
                "final_graph": <serialized final graph>}``.

        Returns:
            Dict with ``"centrality"`` (node_key -> centrality), ``"top_terms"``
            (community_id -> [word nodes]), and ``"modularity"`` (float Q).
        """
        communities = _normalize_communities(data["primary"])
        graph = deserialize_graph(data["final_graph"])

        centrality: dict[str, float] = {}
        top_terms: dict[int, list[str]] = {}

        for community_id, nodes in communities.items():
            community_centrality = _community_centrality(graph, nodes)
            centrality.update(community_centrality)
            top_terms[community_id] = get_top_terms(
                {community_id: nodes},
                graph,
                community_centrality,
                n=N_CENTRAL_TERMS,
            )[community_id]

        return {
            "centrality": centrality,
            "top_terms": top_terms,
            "modularity": calculate_modularity(graph, communities),
        }


if __name__ == "__main__":
    MetricsFilter().execute()