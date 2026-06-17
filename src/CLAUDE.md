# src/ — Context for Claude

> **Tree position:** `/ (root) → src/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for project-wide rules and algorithms.
> Architecture: see [`../docs/arquitetura.md`](../docs/arquitetura.md) for the full pipe-and-filter diagram and design decisions.
> GoF infrastructure: see [`shared/CLAUDE.md`](shared/CLAUDE.md) for AbstractFilter, FilterChain, Observer, Strategy, storage, and cache contracts.

---

## Environment

All execution goes through Docker via `make`. Never call `python`/`python3` directly.

```bash
make install        # install deps locally (uv sync --all-groups) — for docs/linting only
make docker-up      # start MinIO + Redis + app containers
make init-data      # upload data/comments.json to MinIO (first time only)
make run            # run full pipeline inside Docker
make <filter>       # run a single filter inside Docker (e.g. make word-graph)
make test           # run test suite inside Docker
make test-cov       # run tests with coverage report
make docker-status  # show container health
make clean          # flush Redis cache + delete S3 pipeline artifacts
```

---

## What this directory is

`src/` contains all Python source code. Each file is one **filter** in the pipeline.
No filter imports internal functions from another filter — communication happens via **MinIO S3** artifacts and **Redis** cache. Only `src/shared/`, `src/config.py`, and `src/types/` may be imported by multiple filters.

---

## Module map

```
src/
├── shared/                  ← pipeline infrastructure + graph utilities (see shared/CLAUDE.md)
│   ├── filter_base.py       ← Template Method  (AbstractFilter)
│   ├── pipeline.py          ← Chain of Responsibility + Facade  (FilterChain)
│   ├── observers.py         ← Observer  (PipelineObserver, LoggingObserver)
│   ├── strategies.py        ← Strategy  (CommunityDetectionStrategy)
│   ├── storage.py           ← S3/MinIO adapter  (S3Storage, get_storage)
│   ├── cache.py             ← Redis cache adapter  (RedisCache, get_cache)
│   └── graph/               ← graph primitive utilities (see shared/graph/CLAUDE.md)
│       ├── ops.py           ← add_edge, increase_edge, remove_edge, iter_edges, copy_graph, build_graph_from_deltas, serialize_graph
│       ├── metrics.py       ← neighbor_count, total_edge_weight, density, node_count, edge_count
│       ├── traversal.py     ← BFS, DFS, connected_components, count_components, minimum_spanning_tree
│       └── validate.py      ← is_symmetric, invalid_prefixes, isolated_nodes, assert_valid
│
├── main.py                  ← orchestrator: instantiates FilterChain + all filters
├── config.py                ← env vars, S3_KEYS, K=10, MIN_FREQ
├── types/                   ← type aliases/dataclasses, split by semantics (see types/CLAUDE.md)
│   ├── __init__.py          ← re-exports: RawComment, ProcessedComment, Graph, NodeKey, Communities, Metrics
│   ├── comments.py          ← RawComment, ProcessedComment
│   ├── graph.py             ← Graph dataclass, NodeKey
│   ├── communities.py       ← Communities
│   └── metrics.py           ← Metrics
├── preprocessing/           ← ConcreteFilter 1 (package): tokenization, stopwords, normalization
│   ├── __init__.py          ← re-exports PreprocessingFilter
│   ├── __main__.py          ← PreprocessingFilter().execute()  (target of `make preprocessing`)
│   ├── filter.py            ← PreprocessingFilter(AbstractFilter) — orchestrates process()
│   ├── clean.py             ← pure text/token helpers (lowercase, punctuation, segment, tokenize, noise, stopwords)
│   └── normalize.py         ← RSLP grouping key + surface-form representative (decision A1')
├── tree.py                  ← ConcreteFilter 2: N-ary tree (Dataset → Comment → Sentence → Word)
├── word_graph.py            ← ConcreteFilter 3: word co-occurrence graph (positional weight)
├── sentence_graph.py        ← ConcreteFilter 4: sentence graph (derived from word graph)
├── comment_graph.py         ← ConcreteFilter 5: comment graph (derived from sentence graph)
├── final_graph.py           ← ConcreteFilter 6: unified graph (3 levels + hierarchical edges)
├── community_detection.py   ← ConcreteFilter 7: progressive edge cutting + BFS/DFS
├── metrics.py               ← ConcreteFilter 8: weighted degree centrality + modularity Q
└── analysis.py              ← ConcreteFilter 9: report generation
```

---

## Type contracts

Defined in `src/types/` (one module per semantic group — see [`types/CLAUDE.md`](types/CLAUDE.md)) — always import from the package root, never from a submodule:

```python
# CORRECT
from src.types import Graph, NodeKey

# WRONG — exposes internal structure
from src.types.graph import Graph
```

```python
RawComment       = dict   # {"id": int, "topic": str, "text": str}
ProcessedComment = dict   # {"id": int, "topic": str, "sentences": list[list[str]]}
NodeKey          = str    # "w_word", "s_12", "c_3"
Graph            = dataclass(nodes: list[NodeKey], index: dict[NodeKey, int], matrix: list[list[float]])
                             # adjacency matrix + name→index mapping; node names prefixed w_, s_, c_
                             # matrix[i][j] == 0.0 means no edge (weights are always > 0)
Communities      = dict[int, list[str]]         # community_id → [node_key, ...]
Metrics          = dict                         # see metrics.py for full schema
```

**Node key convention:**

| Prefix | Level | Example |
|--------|-------|---------|
| `w_` | Word | `w_travamento` |
| `s_` | Sentence | `s_12` (sentence index in dataset) |
| `c_` | Comment | `c_3` (comment id) |

---

## S3 key registry

Artifact names are defined in `src/config.py` (`S3_KEYS`). Every filter declares `input_key` and `output_key` as class-level attributes that reference keys in this dict — never hardcode artifact names.

```python
# src/config.py (excerpt)
S3_KEYS: dict[str, str] = {
    "raw":            "comments.json",
    "preprocessed":   "preprocessed.json",
    "tree":           "tree.json",
    "word_graph":     "word_graph.json",
    "sentence_graph": "sentence_graph.json",
    "comment_graph":  "comment_graph.json",
    "final_graph":    "final_graph.json",
    "communities":    "communities.json",
    "metrics":        "metrics.json",
    "report":         "report.txt",
}
```

All objects are stored in MinIO under `s3://game-review-graph/pipeline/<name>`. The `pipeline/` prefix is managed internally by `S3Storage` — filters never include it.

---

## How I/O and cache work

`AbstractFilter.execute()` handles all I/O automatically:

```
execute()
  ├── get_cache().get(self.name)          → Redis hit? return cached result → write to S3
  ├── [miss] get_storage().read_json(     → download from MinIO
  │           S3_KEYS[self.input_key])
  ├── self.process(data)                  ← only method subclasses implement
  ├── get_storage().write_json(           → upload to MinIO
  │           S3_KEYS[self.output_key])
  └── get_cache().set(self.name, result)  → cache in Redis
```

Concrete filters must **never** call `get_storage()` or `get_cache()` directly — only `AbstractFilter` does.

---

## Concrete filter template

```python
from src.shared.filter_base import AbstractFilter
from src.types import Graph

class WordGraphFilter(AbstractFilter):
    """Build word co-occurrence graph from the N-ary tree."""

    name = "word_graph"
    input_key = "tree"
    output_key = "word_graph"

    def process(self, data: dict) -> Graph:
        """Transform N-ary tree into word co-occurrence graph.

        Args:
            data: Serialized NaryTree downloaded from MinIO.

        Returns:
            Graph (adjacency matrix + name→index mapping) over word nodes.
        """
        ...


if __name__ == "__main__":
    WordGraphFilter().execute()
```

The `if __name__ == "__main__"` block reduces to a single `execute()` call — all I/O is inherited.
Run with: `make word-graph` (delegates to `docker compose run --rm app uv run python -m src.word_graph`).

---

## Non-negotiable implementation rules

- **No external graph libraries** — NetworkX, igraph, graph-tool, and equivalents are forbidden. −5.0 points penalty.
- **No imports between filters** — `word_graph.py` must not import from `sentence_graph.py`, and vice versa. Only `src/shared/`, `src/config.py`, and `src/types/` are shared.
- **No direct S3/Redis calls in filters** — use `AbstractFilter.execute()` for all I/O; never call `get_storage()` or `get_cache()` inside `process()`.
- **Docstrings on every public function** — format: one-line summary, blank line, `Args:` and `Returns:` sections.
- **Type hints on every function signature** — no `Any` unless truly unavoidable.
- **Graph representation** — always the `Graph` dataclass (`nodes`, `index`, `matrix`) defined in `src/types/graph.py`; never reintroduce a nested-dict adjacency list, and never reach for an external graph library.
- **BFS/DFS, edge cutting, centrality, and modularity** — implemented from scratch in their respective modules.
- **NLP libraries** — NLTK allowed only in the `preprocessing/` package (spaCy not used).
