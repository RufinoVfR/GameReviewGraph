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
    build_graph_from_deltas,
    copy_graph,
    deserialize_graph,
    get_edge_weight,
    has_edge,
    increase_edge,
    iter_edges,
    new_graph,
    remove_edge,
    serialize_graph,
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
from src.shared.graph.validate import (
    assert_valid,
    invalid_prefixes,
    is_symmetric,
    isolated_nodes,
)

__all__ = [
    "add_edge",
    "add_node",
    "assert_valid",
    "average_edge_weight",
    "bfs",
    "build_graph_from_deltas",
    "connected_components",
    "copy_graph",
    "count_components",
    "density",
    "deserialize_graph",
    "dfs",
    "edge_count",
    "get_edge_weight",
    "has_edge",
    "increase_edge",
    "invalid_prefixes",
    "is_connected",
    "is_symmetric",
    "isolated_nodes",
    "iter_edges",
    "minimum_spanning_tree",
    "neighbor_count",
    "new_graph",
    "node_count",
    "reachable",
    "remove_edge",
    "serialize_graph",
    "total_edge_weight",
]
