"""Community scoring metrics — implemented from scratch, reused by two filters.

Holds the pure scoring functions shared between ``metrics.py`` (Filter 8) and
``analysis.py`` (Filter 9): weighted degree centrality, the top central terms per
community, Newman's weighted modularity Q, and partition balance statistics. They
live here — not inside a filter — because a concrete filter must never import
internal functions from another filter; both filters import from this module
instead.

No I/O and no graph mutation: every function is a read-only computation over a
``Graph`` (adjacency matrix) and/or a ``Communities`` partition.
"""

from typing import Any

from src.shared.graph import iter_edges, total_edge_weight
from src.types import Communities, Graph


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
    weighted degree of vertex ``i`` (reusing ``weighted_degree_centrality``),
    ``2m`` the sum of all weighted degrees, and ``δ(c_i, c_j)`` is ``1`` iff
    ``i`` and ``j`` belong to the same community. ``m`` is therefore the total
    undirected edge weight (each edge counted once).

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


def normalize_communities(raw_communities: dict[Any, list[str]]) -> dict[int, list[str]]:
    """Normalize community identifiers to integers.

    Args:
        raw_communities: Community mapping with possibly-string keys
            (JSON deserializes int keys as strings).

    Returns:
        The same mapping with int keys.
    """
    return {int(community_id): list(nodes) for community_id, nodes in raw_communities.items()}


def community_centrality(graph: Graph, nodes: list[str]) -> dict[str, float]:
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


def partition_stats(communities: Communities) -> dict[str, int]:
    """Summarize the balance of a community partition.

    Reduces a partition to the size descriptors used in the final report's
    cross-method comparison: how many communities there are, the smallest and
    largest community size, how many are singletons (size 1), and how many
    comment nodes (prefix ``c_``) the partition covers.

    Args:
        communities: Mapping of community_id to its list of node keys.

    Returns:
        A dict with keys ``n_communities``, ``size_min``, ``size_max``,
        ``singletons`` and ``n_comments``. For an empty partition all values
        are ``0``.
    """
    sizes = [len(nodes) for nodes in communities.values()]
    n_comments = sum(
        1 for nodes in communities.values() for node in nodes if node.startswith("c_")
    )
    if not sizes:
        return {
            "n_communities": 0,
            "size_min": 0,
            "size_max": 0,
            "singletons": 0,
            "n_comments": 0,
        }
    return {
        "n_communities": len(sizes),
        "size_min": min(sizes),
        "size_max": max(sizes),
        "singletons": sum(1 for size in sizes if size == 1),
        "n_comments": n_comments,
    }
