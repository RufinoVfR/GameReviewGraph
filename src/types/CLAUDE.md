# src/types/ — Context for Claude

> **Tree position:** `/ (root) → src/ → src/types/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for type contracts and import rules.
> Graph internals: see [`../shared/graph/CLAUDE.md`](../shared/graph/CLAUDE.md) for the full `Graph` operation contract.

---

## What this directory is

`src/types/` holds every type alias and dataclass shared across pipeline filters, split into one module per semantic group, plus the small from-scratch data structures used to back them (e.g. `Queue`). No domain logic (no graph algorithms, no weight formulas, no NLP), no I/O — only data shapes and the generic structures used to hold them.

```
src/types/
├── __init__.py     ← re-exports: RawComment, ProcessedComment, Graph, NodeKey, Queue, Communities, Metrics, Report
├── comments.py     ← RawComment, ProcessedComment (preprocessing pipeline shapes)
├── graph.py        ← Graph dataclass, NodeKey
├── queue.py        ← Queue (singly linked list, O(1) enqueue/dequeue) — used by traversal.py's bfs()
├── communities.py  ← Communities (community_detection.py output)
├── metrics.py      ← Metrics (metrics.py output)
└── report.py       ← Report (analysis.py output — report.json schema)
```

## Import rule

Always import from the package root, never from a submodule:

```python
# CORRECT
from src.types import Graph, NodeKey

# WRONG — exposes internal structure, breaks if files are reorganised
from src.types.graph import Graph
```

## Adding a new type

1. Decide which existing module it belongs to semantically (e.g. another comment-shaped type goes in `comments.py`). Create a new module only if it doesn't fit any existing semantic group.
2. Define it with a docstring/comment describing its shape (these are `dict`/`TypeAlias`-heavy, not validated at runtime — the comment is the contract).
3. Re-export it from `__init__.py` and add it to `__all__`.

## `Queue` — why a data structure lives here, not in `shared/graph/`

`Queue` (in `queue.py`) is a singly linked list with head/tail pointers, giving O(1) `enqueue`/`dequeue`, used by `traversal.py`'s `bfs()` instead of `collections.deque`. It lives in `src/types/` (not `src/shared/graph/`) because it is a **generic** structure with no graph semantics — it doesn't know about nodes, edges, or weights, so it belongs with the other generic types this package defines, not with graph-specific operations.

## Non-negotiable rules

- **No domain logic here** — no graph algorithms, no weight formulas, no NLP, no I/O. Generic data structures (like `Queue`) are fine; anything that knows about `Graph`'s semantics is not and belongs in `src/shared/graph/`.
- **No imports of concrete filters or `src/shared/`** — this package sits below everything else; nothing here may import from filters or pipeline infrastructure.
- **Docstrings on every public type/method** — for plain aliases, describe the shape; for structures like `Queue`, follow the project's docstring format (one-line summary + `Args:`/`Returns:`/`Raises:`).
