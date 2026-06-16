# src/shared/graph/ — Context for Claude

> **Tree position:** `/ (root) → src/ → src/shared/ → src/shared/graph/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for shared/ rules and import constraints.
> Project-wide rules: see [`../../../CLAUDE.md`](../../../CLAUDE.md).

---

## What this sub-package is

`src/shared/graph/` provides the primitive graph operations shared across all four graph-building filters (`word_graph.py`, `sentence_graph.py`, `comment_graph.py`, `final_graph.py`) and the analysis filters (`community_detection.py`, `metrics.py`).

It contains **no domain logic** — no weight formulas, no NLP, no community-detection algorithm. It is a pure utility layer over `Graph`, defined in `src/types/graph.py` as:

```python
@dataclass
class Graph:
    nodes: list[str] = field(default_factory=list)        # index -> node name
    index: dict[str, int] = field(default_factory=dict)   # node name -> index
    matrix: list[list[float]] = field(default_factory=list)  # matrix[i][j] = weight
```

`matrix` is a full (symmetric) adjacency matrix: `0.0` means "no edge" — safe because every weight formula in this project produces strictly positive weights. The matrix grows one node at a time (append a column to every existing row, then append a new full row) when a name not yet in `index` is referenced — there is no pre-allocated capacity, since the structure is already O(n²) at any final size and incremental growth costs the same total work as building it upfront.

All functions operate on undirected weighted graphs. Writes always update both `matrix[i][j]` and `matrix[j][i]` with the same weight.

---

## File map

```
src/shared/graph/
├── __init__.py     ← selective re-exports (public API of this sub-package)
├── ops.py          ← new_graph, add_node, add_edge, increase_edge, remove_edge, has_edge, get_edge_weight, iter_edges, copy_graph
├── metrics.py      ← properties: neighbor_count, total_edge_weight, density, node_count, edge_count
├── traversal.py    ← BFS, DFS, connected_components, count_components, is_connected, minimum_spanning_tree
└── validate.py     ← is_symmetric, invalid_prefixes, isolated_nodes, assert_valid
```

Import from the sub-package root — never from individual modules:

```python
# CORRECT
from src.shared.graph import add_edge, increase_edge, neighbor_count, connected_components

# WRONG — exposes internal structure, breaks if files are reorganised
from src.shared.graph.ops import increase_edge
```

---

## `ops.py` — CRUD operations

### Signatures

```python
def new_graph() -> Graph:
    """Return an empty Graph with no nodes and an empty matrix."""

def add_node(graph: Graph, name: str) -> int:
    """Return the index of name, creating it if absent.

    Idempotent: if name is already in graph.index, returns the existing
    index without mutating the graph. Otherwise appends name to
    graph.nodes, registers it in graph.index, appends a 0.0 column to
    every existing row of graph.matrix, and appends a new full row of
    0.0 (length = new size) to graph.matrix.

    Args:
        name: Node key (e.g. "w_travamento").

    Returns:
        The (possibly newly assigned) index of name.
    """

def add_edge(graph: Graph, u: str, v: str, weight: float) -> None:
    """Create or overwrite the undirected edge (u, v) with the given weight.

    Creates u and/or v (via add_node) if either is not yet in the graph.
    """

def increase_edge(graph: Graph, u: str, v: str, delta: float) -> None:
    """Increment the weight of (u, v) by delta; create the edge if absent.

    This is the primary write operation for co-occurrence graphs, where each
    new occurrence of a pair (wi, wj) contributes a delta to the edge weight.
    Creates u and/or v (via add_node) if either is not yet in the graph.
    """

def remove_edge(graph: Graph, u: str, v: str) -> None:
    """Remove the undirected edge (u, v). No-op if either node, or the edge, does not exist.

    Sets matrix[i][j] and matrix[j][i] back to 0.0 — does not remove the
    nodes themselves, so a node can end up isolated (degree 0).
    """

def has_edge(graph: Graph, u: str, v: str) -> bool:
    """Return True if an edge exists between u and v (i.e. matrix[i][j] != 0.0)."""

def get_edge_weight(graph: Graph, u: str, v: str) -> float | None:
    """Return the weight of (u, v), or None if either node or the edge does not exist."""

def iter_edges(graph: Graph) -> Iterator[tuple[str, str, float]]:
    """Yield each undirected edge exactly once as (u, v, weight).

    Walks the upper triangle of the matrix (j > i) — since the matrix is
    always symmetric, this visits every edge exactly once without needing
    a seen-set. Order follows node index order (== insertion order).
    """

def copy_graph(graph: Graph) -> Graph:
    """Return a deep copy: new nodes list, new index dict, and a new matrix
    with every row copied — mutating the copy never affects the original."""
```

### Usage per graph level

**`word_graph.py`** — positional co-occurrence weight:
```python
delta = 1.0 / (1.0 + abs(pos_i - pos_j))
increase_edge(graph, f"w_{wi}", f"w_{wj}", delta)
```

**`sentence_graph.py`** — accumulated word-pair contributions before normalisation:
```python
increase_edge(graph, f"s_{a}", f"s_{b}", word_graph_weight(wi, wj))
# caller normalises afterwards: weight(sa, sb) /= len(sa) * len(sb)
```

**`comment_graph.py`** — same pattern using sentence-pair weights.

### What does NOT belong here

- `merge_graphs` — used exclusively by `final_graph.py`; implement as a private helper there.
- Weight normalisation formulas — those are domain logic; implement inside each filter's `process()`.

---

## `metrics.py` — graph properties

Implementation note: `neighbor_count`/`total_edge_weight` resolve `node` to an index via `graph.index[node]`, then scan `graph.matrix[i]` counting/summing entries `!= 0.0`. `node_count` is `len(graph.nodes)`; `edge_count` and `average_edge_weight` iterate `iter_edges` rather than re-walking the matrix.

### Signatures

```python
def neighbor_count(graph: Graph, node: str) -> int:
    """Return the number of neighbours of node (unweighted degree)."""

def total_edge_weight(graph: Graph, node: str) -> float:
    """Return the sum of edge weights incident to node (weighted degree)."""

def node_count(graph: Graph) -> int:
    """Return the total number of nodes in the graph."""

def edge_count(graph: Graph) -> int:
    """Return the number of unique undirected edges."""

def density(graph: Graph) -> float:
    """Return the ratio of actual edges to the maximum possible edges.

    density = 2 * edge_count / (n * (n - 1))  where n = node_count.
    Returns 0.0 for graphs with fewer than 2 nodes.
    """

def average_edge_weight(graph: Graph) -> float:
    """Return the mean edge weight across all unique edges.

    Returns 0.0 for empty graphs.
    """
```

### Usage

`metrics.py` (Filter 8) uses `total_edge_weight` for centrality:
```python
centrality[node] = total_edge_weight(graph, node) / (2 * sum_of_all_weights)
```

`community_detection.py` uses `neighbor_count` to check the removal condition:
```python
if neighbor_count(graph, u) > 1 and neighbor_count(graph, v) > 1:
    remove_edge(graph, u, v)
```

---

## `traversal.py` — graph traversal

Implementation note: traversal still operates on node **names** at the public API boundary (`start: str`, returned lists of `str`) — internally, resolve `start` to an index, walk neighbours by scanning the corresponding `graph.matrix` row for entries `!= 0.0`, and translate indices back to names via `graph.nodes[i]` before returning. `bfs` uses `Queue` from `src/types/queue.py` (a from-scratch FIFO queue — singly linked list, O(1) `enqueue`/`dequeue` — used instead of `collections.deque`); `dfs` uses an explicit stack (a plain `list`, no recursion, to avoid Python's recursion limit on larger graphs), marking nodes visited at pop time (not push time) so the visiting order matches a recursive DFS.

### Signatures

```python
def bfs(graph: Graph, start: str) -> list[str]:
    """Return nodes reachable from start in breadth-first order."""

def dfs(graph: Graph, start: str) -> list[str]:
    """Return nodes reachable from start in depth-first order."""

def reachable(graph: Graph, start: str) -> set[str]:
    """Return the set of all nodes reachable from start (BFS-based)."""

def connected_components(graph: Graph) -> list[list[str]]:
    """Return all connected components as lists of node keys.

    Components are ordered by first node encountered (insertion order).
    Used by ProgressiveEdgeCuttingStrategy after each edge removal.
    """

def count_components(graph: Graph) -> int:
    """Return the number of connected components."""

def is_connected(graph: Graph) -> bool:
    """Return True if the graph has exactly one connected component."""

def minimum_spanning_tree(graph: Graph) -> Graph:
    """Return a new Graph that is a Minimum Spanning Tree of graph, built via
    Prim's algorithm (dense/array variant — O(V^2), no priority queue).

    Used by ProgressiveEdgeCuttingStrategy to reduce the dense final graph
    to V-1 edges before running progressive edge cutting on it. Does not
    mutate graph. If graph is disconnected, returns the MST of the
    component containing graph.nodes[0] only (community detection always
    receives a connected final graph in this project, so this case is not
    expected to be exercised in practice, but should not silently return a
    partial result without it being obvious from node_count).

    Args:
        graph: Graph to build a spanning tree from. Not mutated.

    Returns:
        A new Graph with the same node set (or the connected subset
        reached, see above) and exactly n-1 weighted edges.
    """
```

### Relation to `strategies.py`

`ProgressiveEdgeCuttingStrategy` delegates all MST construction and traversal to this module:

```python
from src.shared.graph import minimum_spanning_tree, count_components, connected_components

# inside detect():
working = minimum_spanning_tree(copy_graph(graph))
# ... progressive cutting loop runs on `working` from here ...
if count_components(working) >= k:
    break
# ...
return {i + 1: component for i, component in enumerate(connected_components(working))}
```

The private helpers `_bfs`, `_bfs_collect`, `_count_components`, `_label_components` that were inline in `strategies.py` are replaced by these public functions.

---

## `validate.py` — graph validation

Implementation note: `invalid_prefixes` and `isolated_nodes` iterate `graph.nodes` (and use `neighbor_count`/`graph.index` for the latter). `is_symmetric` and the self-loop check in `assert_valid` walk `graph.matrix` directly (`matrix[i][j] == matrix[j][i]` for all `i, j`; `matrix[i][i] == 0.0` for all `i`).

### Signatures

```python
def is_symmetric(graph: Graph) -> bool:
    """Return True if matrix[i][j] == matrix[j][i] for every i, j.

    All graph-building filters must produce symmetric graphs. Use this in
    unit tests to assert correctness of the output graph.
    """

def invalid_prefixes(
    graph: Graph,
    allowed: tuple[str, ...] = ("w_", "s_", "c_"),
) -> list[str]:
    """Return node keys whose prefix is not in the allowed set.

    An empty list means every node follows the w_/s_/c_ convention.
    """

def isolated_nodes(graph: Graph) -> list[str]:
    """Return nodes with degree 0 (no edges)."""

def assert_valid(graph: Graph) -> None:
    """Raise ValueError if the graph fails any structural invariant.

    Checks: symmetry, valid node prefixes, no self-loops (matrix[i][i] == 0.0).
    """
```

### When to call `assert_valid`

Call it at the end of each filter's `process()` during development and in unit tests. Remove the call from production code only if profiling shows it is a bottleneck.

---

## `__init__.py` — public API

Imports all functions that filters are expected to use directly. Adding a function to a module without re-exporting it here makes it internal.

```python
from src.shared.graph.ops import (
    new_graph, add_node, add_edge, increase_edge, remove_edge,
    has_edge, get_edge_weight, iter_edges, copy_graph,
)
from src.shared.graph.metrics import (
    neighbor_count, total_edge_weight,
    node_count, edge_count, density, average_edge_weight,
)
from src.shared.graph.traversal import (
    bfs, dfs, reachable,
    connected_components, count_components, is_connected,
    minimum_spanning_tree,
)
from src.shared.graph.validate import (
    is_symmetric, invalid_prefixes, isolated_nodes, assert_valid,
)
```

---

## Non-negotiable rules

- **No weight formulas** — `increase_edge` applies a caller-supplied delta; the formula `1 / (1 + |pos_i - pos_j|)` lives in `word_graph.py`, not here.
- **No graph libraries** — NetworkX and equivalents are forbidden everywhere, including here.
- **No domain constants** — do not import `K`, `MIN_FREQ`, or any filter-specific value.
- **Always undirected** — every function that writes edges must write both `matrix[i][j]` and `matrix[j][i]`.
- **Never index `graph.matrix` with a raw name** — always resolve through `graph.index` (or `add_node`) first; the matrix is index-addressed, not name-addressed.
- **`0.0` means "no edge"** — never store a real `0.0` weight; if a formula could legitimately produce `0.0`, that filter must not call `add_edge`/`increase_edge` for that pair (this holds for all current weight formulas, which are strictly positive).
- **Docstrings on every public function** — one-line summary, blank line, `Args:` and `Returns:`.
- **Import from `src.shared.graph`**, never from sub-modules directly.
