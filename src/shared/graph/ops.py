"""CRUD operations on Graph (adjacency matrix + name-to-index mapping)."""

from typing import Iterable, Iterator

from src.types import Graph


def new_graph() -> Graph:
    """Return an empty Graph with no nodes and an empty matrix.

    Returns:
        A fresh Graph instance.
    """
    return Graph()


def add_node(graph: Graph, node_key: str) -> int:
    """Return the index of node_key, registering it in graph if absent.

    Idempotent: if node_key is already known, returns its existing index
    without mutating graph. Otherwise grows nodes/index/matrix by one.

    Args:
        graph: Graph to mutate.
        node_key: Node key (e.g. "w_travamento").

    Returns:
        The index of node_key in graph.nodes.
    """
    if node_key in graph.index:
        return graph.index[node_key]
    new_index = len(graph.nodes)
    graph.index[node_key] = new_index
    graph.nodes.append(node_key)
    for row in graph.matrix:
        row.append(0.0)
    graph.matrix.append([0.0] * (new_index + 1))
    return new_index


def add_edge(graph: Graph, node_key1: str, node_key2: str, weight: float) -> None:
    """Create or overwrite the undirected edge (node_key1, node_key2) with the given weight.

    Args:
        graph: Graph to mutate. Both nodes are created via add_node if absent.
        node_key1: First node key.
        node_key2: Second node key.
        weight: Weight to assign to the edge.
    """
    i, j = add_node(graph, node_key1), add_node(graph, node_key2)
    graph.matrix[i][j] = weight
    graph.matrix[j][i] = weight


def increase_edge(graph: Graph, node_key1: str, node_key2: str, delta: float) -> None:
    """Increment the weight of (node_key1, node_key2) by delta; create the edge if absent.

    Primary write operation for co-occurrence graphs, where each new
    occurrence of a pair contributes a delta to the accumulated weight.

    Args:
        graph: Graph to mutate. Both nodes are created via add_node if absent.
        node_key1: First node key.
        node_key2: Second node key.
        delta: Amount to add to the current weight (0.0 if no edge yet).
    """
    i, j = add_node(graph, node_key1), add_node(graph, node_key2)
    new_weight = graph.matrix[i][j] + delta
    graph.matrix[i][j] = new_weight
    graph.matrix[j][i] = new_weight


def has_edge(graph: Graph, node_key1: str, node_key2: str) -> bool:
    """Return True if an edge exists between node_key1 and node_key2.

    Args:
        graph: Graph to query.
        node_key1: First node key.
        node_key2: Second node key.

    Returns:
        True if both nodes exist and matrix[i][j] != 0.0.
    """
    if node_key1 not in graph.index or node_key2 not in graph.index:
        return False
    i, j = graph.index[node_key1], graph.index[node_key2]
    return graph.matrix[i][j] != 0.0


def remove_edge(graph: Graph, node_key1: str, node_key2: str) -> None:
    """Remove the undirected edge (node_key1, node_key2). No-op if either node, or the edge, does not exist.

    Args:
        graph: Graph to mutate.
        node_key1: First node key.
        node_key2: Second node key.
    """
    if not has_edge(graph, node_key1, node_key2):
        return
    i, j = graph.index[node_key1], graph.index[node_key2]
    graph.matrix[i][j] = 0.0
    graph.matrix[j][i] = 0.0


def get_edge_weight(graph: Graph, node_key1: str, node_key2: str) -> float | None:
    """Return the weight of (node_key1, node_key2), or None if either node or the edge does not exist.

    Args:
        graph: Graph to query.
        node_key1: First node key.
        node_key2: Second node key.

    Returns:
        The edge weight, or None.
    """
    if not has_edge(graph, node_key1, node_key2):
        return None
    i, j = graph.index[node_key1], graph.index[node_key2]
    return graph.matrix[i][j]


def iter_edges(graph: Graph) -> Iterator[tuple[str, str, float]]:
    """Yield each undirected edge exactly once as (node_key1, node_key2, weight).

    Walks the upper triangle of the matrix (j > i) — safe because the
    matrix is always symmetric, so no pair is ever yielded twice.

    Args:
        graph: Graph to iterate.

    Yields:
        (node_key1, node_key2, weight) tuples, ordered by node index.
    """
    for i, node_key1 in enumerate(graph.nodes):
        for j in range(i + 1, len(graph.nodes)):
            node_key2 = graph.nodes[j]
            weight = graph.matrix[i][j]
            if weight != 0.0:
                yield (node_key1, node_key2, weight)


def copy_graph(graph: Graph) -> Graph:
    """Return a deep copy of graph; mutating the copy never affects the original.

    Args:
        graph: Graph to copy.

    Returns:
        A new Graph with copied nodes, index, and matrix.
    """
    return Graph(
        nodes=list(graph.nodes),
        index=dict(graph.index),
        matrix=[list(row) for row in graph.matrix],
    )


def build_graph_from_deltas(deltas: Iterable[tuple[str, str, float]]) -> Graph:
    """Build a new Graph by accumulating (node_key1, node_key2, delta) triples.

    Common envelope for the three co-occurrence graph levels (word, sentence,
    comment): each filter supplies its own delta-generating logic (e.g. the
    positional weight formula, or a pre-normalized pair weight) and this
    function only handles the accumulation into a Graph via increase_edge.

    Args:
        deltas: Iterable of (node_key1, node_key2, delta) triples. The same
            pair may appear multiple times — each occurrence's delta is
            accumulated via increase_edge.

    Returns:
        A new Graph with every node touched by deltas and accumulated weights.
    """
    graph = new_graph()
    for node_key1, node_key2, delta in deltas:
        increase_edge(graph, node_key1, node_key2, delta)
    return graph


def serialize_graph(graph: Graph) -> dict:
    """Return a JSON-serializable dict representation of graph.

    The Graph dataclass is not directly JSON-serializable; every filter that
    outputs a graph must call this in process() so AbstractFilter.execute()
    can write_json the result (and cache it). The inverse is deserialize_graph.

    Args:
        graph: Graph to serialize.

    Returns:
        Dict with keys "nodes" (list[str]), "index" (dict[str, int]), and
        "matrix" (list[list[float]]) — all JSON-native.
    """
    return {
        "nodes": list(graph.nodes),
        "index": dict(graph.index),
        "matrix": [list(row) for row in graph.matrix],
    }


def deserialize_graph(data: dict) -> Graph:
    """Reconstruct a Graph from the dict produced by serialize_graph.

    Every filter that consumes a graph artifact loaded from S3 must call this
    on the raw dict before using any graph utility, since execute() hands
    process() the parsed JSON (a plain dict), not a Graph instance.

    Args:
        data: Dict with "nodes", "index", and "matrix" keys (the output of
            serialize_graph, round-tripped through JSON).

    Returns:
        A Graph instance equivalent to the one originally serialized.
    """
    return Graph(
        nodes=list(data["nodes"]),
        index={name: int(i) for name, i in data["index"].items()},
        matrix=[[float(w) for w in row] for row in data["matrix"]],
    )
