"""Public API of the graph utility sub-package.

Always import from this package root, never from individual modules
(e.g. ``src.shared.graph.ops``) — the split across files is an internal
implementation detail.
"""

from src.shared.graph.metrics import (
    average_edge_weight,
    density,
    edge_count,
    neighbor_count,
    node_count,
    total_edge_weight,
)
from src.shared.graph.ops import (
    add_edge,
    add_node,
    copy_graph,
    get_edge_weight,
    has_edge,
    increase_edge,
    iter_edges,
    new_graph,
    remove_edge,
)
from src.shared.graph.traversal import (
    bfs,
    connected_components,
    count_components,
    dfs,
    is_connected,
    minimum_spanning_tree,
    reachable,
)

__all__ = [
    "add_edge",
    "add_node",
    "average_edge_weight",
    "bfs",
    "connected_components",
    "copy_graph",
    "count_components",
    "density",
    "dfs",
    "edge_count",
    "get_edge_weight",
    "has_edge",
    "increase_edge",
    "is_connected",
    "iter_edges",
    "minimum_spanning_tree",
    "neighbor_count",
    "new_graph",
    "node_count",
    "reachable",
    "remove_edge",
    "total_edge_weight",
]
