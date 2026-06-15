# src/ — Context for Claude

> **Tree position:** `/ (root) → src/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for project-wide rules and algorithms.
> Architecture: see [`../docs/arquitetura.md`](../docs/arquitetura.md) for the full pipe-and-filter diagram and design decisions.

---

## Environment

Dependencies are managed via **uv** (`pyproject.toml` at the repo root).

```bash
make install   # uv sync --all-groups → installs deps into .venv/
make run       # uv run python src/main.py
make <filter>  # uv run python -m src.<filter>  (e.g. make word-graph)
make test      # uv run pytest
make test-cov  # uv run pytest --cov=src --cov-report=term-missing
make clean     # removes all data/ intermediaries and cache/
```

Never call `python`/`python3` directly. All execution goes through `make`.

---

## What this directory is

`src/` contains all Python source code. Each file is one **filter** in the pipeline.
No filter imports internal functions from another filter — communication happens exclusively through `data/` files.

---

## Module map

```
src/
├── main.py                  ← orchestrator: runs all 9 filters end-to-end
├── config.py                ← global constants (K=10, MIN_FREQ, CACHE_DIR, etc.)
├── types.py                 ← type aliases shared across modules
├── preprocessing.py         ← Filter 1: tokenization, stopwords, normalization
├── tree.py                  ← Filter 2: N-ary tree (Dataset → Comment → Sentence → Word)
├── word_graph.py            ← Filter 3: word co-occurrence graph (positional weight)
├── sentence_graph.py        ← Filter 4: sentence graph (derived from word graph)
├── comment_graph.py         ← Filter 5: comment graph (derived from sentence graph)
├── final_graph.py           ← Filter 6: unified graph (3 levels + hierarchical edges)
├── community_detection.py   ← Filter 7: progressive edge cutting + BFS/DFS
├── metrics.py               ← Filter 8: weighted degree centrality + modularity Q
└── analysis.py              ← Filter 9: report generation
```

---

## Type contracts

Defined in `src/types.py` — import from there, do not redefine locally.

```python
# Primitive types
RawComment       = dict   # {"id": int, "topic": str, "text": str}
ProcessedComment = dict   # {"id": int, "topic": str, "sentences": list[list[str]]}

# Core data structures
Graph       = dict[str, dict[str, float]]  # adjacency list; keys prefixed w_, s_, c_
NaryTree    = ...                          # defined in tree.py; serializable to/from JSON
Communities = dict[int, list[str]]         # community_id → [node_key, ...]
Metrics     = dict                         # see metrics.py for full schema
```

**Node key convention:**

| Prefix | Level | Example |
|--------|-------|---------|
| `w_` | Word | `w_travamento` |
| `s_` | Sentence | `s_12` (sentence index in dataset) |
| `c_` | Comment | `c_3` (comment id) |

---

## I/O file paths

Every filter reads and writes via `pathlib.Path` relative to the project root.
Constants are defined in `config.py` — never hardcode paths inside filter modules.

```python
# config.py (excerpt)
from pathlib import Path

DATA_DIR   = Path("data")
CACHE_DIR  = DATA_DIR / "cache"

PATHS = {
    "raw":              DATA_DIR / "comments.json",
    "preprocessed":     DATA_DIR / "preprocessed.json",
    "tree":             DATA_DIR / "tree.json",
    "word_graph":       DATA_DIR / "word_graph.json",
    "sentence_graph":   DATA_DIR / "sentence_graph.json",
    "comment_graph":    DATA_DIR / "comment_graph.json",
    "final_graph":      DATA_DIR / "final_graph.json",
    "communities":      DATA_DIR / "communities.json",
    "metrics":          DATA_DIR / "metrics.json",
    "report":           DATA_DIR / "report.txt",
}
```

---

## Cache convention (JSON + Pickle)

Each filter must implement this loading pattern before processing:

```python
import pickle
from pathlib import Path
from src.config import CACHE_DIR

def _load_cache(name: str) -> object | None:
    """Return cached pickle if it exists and is newer than the source JSON, else None."""
    cache_path = CACHE_DIR / f"{name}.pkl"
    if not cache_path.exists():
        return None
    return pickle.loads(cache_path.read_bytes())

def _save_cache(name: str, obj: object) -> None:
    """Persist object as pickle for fast reload."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{name}.pkl").write_bytes(pickle.dumps(obj))
```

---

## Standalone execution template

Every filter **must** include this block so it can run in isolation:

```python
if __name__ == "__main__":
    import json
    from pathlib import Path
    from src.config import PATHS

    # --- load inputs ---
    data = json.loads(PATHS["<input>"].read_text(encoding="utf-8"))

    # --- run filter ---
    result = main_function(data)

    # --- write output ---
    PATHS["<output>"].write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[<module>] Written → {PATHS['<output>']}")
```

Run with: `make <filter-name>` from the project root (e.g. `make word-graph`).
Never call `python`/`python3` directly — always go through `make`, which delegates to `uv run`.

---

## Non-negotiable implementation rules

- **No external graph libraries** — NetworkX, igraph, graph-tool, and equivalents are forbidden. −5.0 points penalty.
- **No imports between filters** — `word_graph.py` must not import from `sentence_graph.py`, and vice versa. Only `config.py` and `types.py` are shared.
- **Docstrings on every public function** — format: one-line summary, blank line, `Args:` and `Returns:` sections.
- **Type hints on every function signature** — no `Any` unless truly unavoidable.
- **Graph representation** — always `dict[str, dict[str, float]]`; no classes, no adjacency matrices.
- **BFS/DFS, edge cutting, centrality, and modularity** — implemented from scratch in their respective modules.
- **NLP libraries** — NLTK/spaCy allowed only in `preprocessing.py`.
