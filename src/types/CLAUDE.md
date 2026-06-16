# src/types/ — Context for Claude

> **Tree position:** `/ (root) → src/ → src/types/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for type contracts and import rules.
> Graph internals: see [`../shared/graph/CLAUDE.md`](../shared/graph/CLAUDE.md) for the full `Graph` operation contract.

---

## What this directory is

`src/types/` holds every type alias and dataclass shared across pipeline filters, split into one module per semantic group. No domain logic, no I/O — pure type definitions.

```
src/types/
├── __init__.py     ← re-exports: RawComment, ProcessedComment, Graph, NodeKey, Communities, Metrics
├── comments.py     ← RawComment, ProcessedComment (preprocessing pipeline shapes)
├── graph.py        ← Graph dataclass, NodeKey
├── communities.py  ← Communities (community_detection.py output)
└── metrics.py      ← Metrics (metrics.py output)
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

## Non-negotiable rules

- **No logic here** — no functions beyond dataclass definitions, no validation, no I/O.
- **No imports of concrete filters or `src/shared/`** — this package sits below everything else; nothing here may import from filters or pipeline infrastructure.
- **Docstrings/comments on every type** — describe the shape, since most aliases are plain `dict`/`TypeAlias` with no structural enforcement.
