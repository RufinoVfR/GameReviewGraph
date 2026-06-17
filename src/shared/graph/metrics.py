"""Graph properties: degree, density, and weight statistics."""

from src.shared.graph.ops import iter_edges
from src.types import Graph


def neighbor_count(graph: Graph, node_key: str) -> int:
    """Return the number of neighbours of node_key (unweighted degree).

    Args:
        graph: Graph to query.
        node_key: Node key to inspect.

    Returns:
        Count of entries in the node's matrix row that are != 0.0.
    """
    i = graph.index[node_key]
    return sum(1 for weight in graph.matrix[i] if weight != 0.0)


def total_edge_weight(graph: Graph, node_key: str) -> float:
    """Return the sum of edge weights incident to node_key (weighted degree).

    Args:
        graph: Graph to query.
        node_key: Node key to inspect.

    Returns:
        Sum of the node's matrix row.
    """
    i = graph.index[node_key]
    return sum(graph.matrix[i])


def node_count(graph: Graph) -> int:
    """Return the total number of nodes in the graph.

    Args:
        graph: Graph to query.

    Returns:
        Number of nodes.
    """
    return len(graph.nodes)


def edge_count(graph: Graph) -> int:
    """Return the number of unique undirected edges.

    Args:
        graph: Graph to query.

    Returns:
        Number of edges with non-zero weight.
    """
    return sum(1 for _ in iter_edges(graph))


def density(graph: Graph) -> float:
    """Return the ratio of actual edges to the maximum possible edges.

    density = 2 * edge_count / (n * (n - 1)) where n = node_count.

    Args:
        graph: Graph to query.

    Returns:
        Density in [0.0, 1.0], or 0.0 for graphs with fewer than 2 nodes.
    """
    n = node_count(graph)
    if n < 2:
        return 0.0
    return 2 * edge_count(graph) / (n * (n - 1))


def average_edge_weight(graph: Graph) -> float:
    """Return the mean edge weight across all unique edges.

    Args:
        graph: Graph to query.

    Returns:
        Mean weight, or 0.0 for graphs with no edges.
    """
    weights = [weight for _, _, weight in iter_edges(graph)]
    if not weights:
        return 0.0
    return sum(weights) / len(weights)
