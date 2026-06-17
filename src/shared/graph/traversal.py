"""Graph traversal: BFS, DFS, connected components, and MST (Prim)."""

from src.shared.graph.ops import add_edge, add_node, new_graph
from src.types import Graph, Queue


def _neighbors(graph: Graph, node_index: int) -> list[int]:
    """Return the indices of neighbors of the given node index.

    Args:
        graph: Graph to query.
        node_index: Index of the node whose neighbors are needed.

    Returns:
        Indices j where graph.matrix[node_index][j] != 0.0.
    """
    return [j for j, weight in enumerate(graph.matrix[node_index]) if weight != 0.0]


def bfs(graph: Graph, start_key: str) -> list[str]:
    """Return the node keys reachable from start_key in breadth-first order.

    Args:
        graph: Graph to traverse.
        start_key: Starting node key.

    Returns:
        List of reachable node keys in BFS order. Empty if start_key does not exist.
    """
    if start_key not in graph.index:
        return []
    start_index = graph.index[start_key]
    visited = {start_index}
    order = [start_index]
    queue: Queue[int] = Queue()
    queue.enqueue(start_index)
    while not queue.is_empty():
        current = queue.dequeue()
        for neighbor in _neighbors(graph, current):
            if neighbor not in visited:
                visited.add(neighbor)
                order.append(neighbor)
                queue.enqueue(neighbor)
    return [graph.nodes[i] for i in order]


def dfs(graph: Graph, start_key: str) -> list[str]:
    """Return the node keys reachable from start_key in depth-first order.

    Uses an explicit stack (no recursion). Nodes are marked visited at pop
    time, not push time, and neighbors are pushed in reverse order so the
    visiting order matches a recursive DFS.

    Args:
        graph: Graph to traverse.
        start_key: Starting node key.

    Returns:
        List of reachable node keys in DFS order. Empty if start_key does not exist.
    """
    if start_key not in graph.index:
        return []
    start_index = graph.index[start_key]
    visited: set[int] = set()
    order = []
    stack = [start_index]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        order.append(current)
        for neighbor in reversed(_neighbors(graph, current)):
            if neighbor not in visited:
                stack.append(neighbor)
    return [graph.nodes[i] for i in order]


def reachable(graph: Graph, start_key: str) -> set[str]:
    """Return the set of all node keys reachable from start_key (BFS-based).

    Args:
        graph: Graph to traverse.
        start_key: Starting node key.

    Returns:
        Set of reachable node keys, including start_key itself.
    """
    return set(bfs(graph, start_key))


def connected_components(graph: Graph) -> list[list[str]]:
    """Return all connected components as lists of node keys.

    Components are ordered by first node encountered (insertion order).

    Args:
        graph: Graph to inspect.

    Returns:
        List of components, each a list of node keys.
    """
    visited: set[str] = set()
    components = []
    for node_key in graph.nodes:
        if node_key not in visited:
            component = bfs(graph, node_key)
            visited.update(component)
            components.append(component)
    return components


def count_components(graph: Graph) -> int:
    """Return the number of connected components.

    Args:
        graph: Graph to inspect.

    Returns:
        Number of connected components.
    """
    return len(connected_components(graph))


def is_connected(graph: Graph) -> bool:
    """Return True if the graph has exactly one connected component.

    Args:
        graph: Graph to inspect.

    Returns:
        True if connected (or empty), False otherwise.
    """
    if not graph.nodes:
        return True
    return len(bfs(graph, graph.nodes[0])) == len(graph.nodes)


def minimum_spanning_tree(graph: Graph) -> Graph:
    """Return a new Graph that is a Minimum Spanning Tree of graph (Prim's algorithm, dense variant).

    Builds the MST of the component containing graph.nodes[0] — O(V^2), no
    priority queue, scanning the adjacency matrix directly. Does not mutate
    graph.

    Args:
        graph: Graph to build a spanning tree from. Not mutated.

    Returns:
        A new Graph with the nodes reachable from graph.nodes[0] and
        exactly n-1 weighted edges (n = number of reachable nodes).
    """
    mst = new_graph()
    if not graph.nodes:
        return mst

    n = len(graph.nodes)
    in_tree = [False] * n
    min_weight = [float("inf")] * n
    nearest = [-1] * n

    start = 0
    min_weight[start] = 0.0

    for _ in range(n):
        u = -1
        best = float("inf")
        for candidate in range(n):
            if not in_tree[candidate] and min_weight[candidate] < best:
                best = min_weight[candidate]
                u = candidate
        if u == -1:
            break  # remaining nodes are unreachable from start
        in_tree[u] = True
        if nearest[u] != -1:
            add_edge(mst, graph.nodes[u], graph.nodes[nearest[u]], min_weight[u])
        else:
            add_node(mst, graph.nodes[u])
        for v in range(n):
            weight = graph.matrix[u][v]
            if weight != 0.0 and not in_tree[v] and weight < min_weight[v]:
                min_weight[v] = weight
                nearest[v] = u

    return mst
