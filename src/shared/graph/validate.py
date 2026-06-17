"""Structural validation of Graph: symmetry, node prefixes, isolated nodes, self-loops."""

from src.shared.graph.metrics import neighbor_count
from src.types import Graph


def is_symmetric(graph: Graph) -> bool:
    """Return True if matrix[i][j] == matrix[j][i] for every i, j.

    Args:
        graph: Graph to check.

    Returns:
        True if the adjacency matrix is symmetric.
    """
    n = len(graph.nodes)
    for i in range(n):
        for j in range(i + 1, n):
            if graph.matrix[i][j] != graph.matrix[j][i]:
                return False
    return True


def invalid_prefixes(
    graph: Graph,
    allowed: tuple[str, ...] = ("w_", "s_", "c_"),
) -> list[str]:
    """Return node keys whose prefix is not in the allowed set.

    Args:
        graph: Graph to check.
        allowed: Tuple of valid node key prefixes.

    Returns:
        Node keys that do not start with any prefix in allowed. Empty list
        means every node follows the convention.
    """
    return [node_key for node_key in graph.nodes if not node_key.startswith(allowed)]


def isolated_nodes(graph: Graph) -> list[str]:
    """Return nodes with degree 0 (no edges).

    Args:
        graph: Graph to check.

    Returns:
        Node keys with no incident edges.
    """
    return [node_key for node_key in graph.nodes if neighbor_count(graph, node_key) == 0]


def assert_valid(graph: Graph) -> None:
    """Raise ValueError if graph fails any structural invariant.

    Checks, in order, stopping at the first failure: symmetry, valid node
    prefixes, and absence of self-loops (matrix[i][i] == 0.0).

    Args:
        graph: Graph to validate.

    Raises:
        ValueError: If any invariant is violated.
    """
    if not is_symmetric(graph):
        raise ValueError("Graph is not symmetric: matrix[i][j] != matrix[j][i] for some i, j.")

    bad_prefixes = invalid_prefixes(graph)
    if bad_prefixes:
        raise ValueError(f"Graph has node keys with invalid prefixes: {bad_prefixes}.")

    for i in range(len(graph.nodes)):
        if graph.matrix[i][i] != 0.0:
            raise ValueError(f"Graph has a self-loop at node {graph.nodes[i]!r}.")
