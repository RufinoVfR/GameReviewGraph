# src/shared/ — Context for Claude

> **Tree position:** `/ (root) → src/ → src/shared/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for module-level rules and I/O contracts.
> Pattern specification: see [`../../docs/padroes_projeto.md`](../../docs/padroes_projeto.md) for full GoF diagrams.

---

## What this directory is

`src/shared/` contains two layers of reusable infrastructure:

1. **Pipeline infrastructure** — GoF patterns, S3/Redis adapters. No domain logic.
2. **Graph utilities** (`graph/`) — primitive operations on `Graph = dict[str, dict[str, float]]` shared across all graph-building filters. No domain logic, no weight formulas.

Every file here is imported by multiple concrete filters. A change here affects the entire pipeline. PRs touching this directory require approval from all team members before merge.

---

## File map

```
src/shared/
├── __init__.py       ← empty; marks the directory as a package
├── filter_base.py    ← Template Method  (AbstractFilter)
├── pipeline.py       ← Chain of Responsibility + Facade  (FilterChain)
├── observers.py      ← Observer  (PipelineObserver, LoggingObserver)
├── strategies.py     ← Strategy  (CommunityDetectionStrategy, ProgressiveEdgeCuttingStrategy)
├── storage.py        ← S3 / MinIO adapter  (S3Storage, get_storage)
├── cache.py          ← Redis cache adapter  (RedisCache, get_cache)
└── graph/            ← graph primitive utilities (see graph/CLAUDE.md)
    ├── __init__.py   ← public re-exports: add_edge, increase_weight, degree, connected_components, …
    ├── ops.py        ← CRUD: add_edge, increase_weight, remove_edge, iter_edges, copy_graph
    ├── metrics.py    ← properties: degree, weighted_degree, density, node_count, edge_count
    ├── traversal.py  ← BFS, DFS, connected_components, count_components, is_connected
    └── validate.py   ← is_symmetric, invalid_prefixes, isolated_nodes, assert_valid
```

---

## `filter_base.py` — Template Method

### Contract

`AbstractFilter` defines `execute()` as the invariant skeleton. Subclasses implement only `process()`.

```python
class AbstractFilter(ABC):
    name: str              # unique slug, e.g. "word_graph"
    input_key: str         # primary key in S3_KEYS from src/config.py
    output_key: str        # key in S3_KEYS for the output artifact
    output_format: str = "json"         # "json" or "text"
    extra_input_keys: list[str] = []    # additional S3_KEYS for multi-input filters

    def execute(self) -> None:
        """Run the full filter lifecycle: load → process → save."""

    @abstractmethod
    def process(self, data: Any) -> Any:
        """Apply the filter's domain transformation.

        Args:
            data: When extra_input_keys is empty — the deserialized primary
                  artifact (plain Python object).
                  When extra_input_keys is non-empty — a dict of the form
                  {"primary": <primary>, "<key>": <artifact>, ...}.

        Returns:
            Transformed result to be written to S3_KEYS[output_key].
        """
```

### Multi-input filters

Filters that need more than one artifact declare `extra_input_keys` at class level. `_load_input()` then returns a dict instead of a plain object:

```python
class SentenceGraphFilter(AbstractFilter):
    name = "sentence_graph"
    input_key = "word_graph"         # primary
    extra_input_keys = ["tree"]      # secondary
    output_key = "sentence_graph"

    def process(self, data: dict) -> Graph:
        word_graph = data["primary"]
        tree = data["tree"]
        ...
```

Filters requiring multiple inputs in the pipeline:

| Filter | `input_key` | `extra_input_keys` |
|--------|-------------|-------------------|
| `sentence_graph` | `"word_graph"` | `["tree"]` |
| `comment_graph` | `"sentence_graph"` | `["preprocessed"]` |
| `final_graph` | `"comment_graph"` | `["word_graph", "sentence_graph"]` |
| `metrics` | `"communities"` | `["final_graph"]` |

### Rules

- **Do** declare `name`, `input_key`, `output_key` as class-level attributes (not in `__init__`).
- **Do** declare `extra_input_keys` when the filter needs more than one artifact.
- **Do not** override `execute()`, `_load_input()`, `_write_output()`, `_load_cache()`, or `_save_cache()` in concrete filters — those methods are the Template Method's invariant steps.
- **Do not** perform any JSON reads or writes inside `process()` — that is `execute()`'s responsibility.
- **Do** call `super().__init__()` if you add a custom `__init__` to a concrete filter.

### Cache behaviour

`execute()` calls `get_cache().get(self.name)` (Redis) before calling `process()`. On a hit the cached result is written back to S3 and `process()` is skipped. `make clean` flushes all `filter:*` Redis keys; use it whenever you change a filter's logic and need to force reprocessing.

---

## `pipeline.py` — Chain of Responsibility + Facade

### Contract

```python
class FilterChain:
    def __init__(
        self,
        filters: list[AbstractFilter],
        observers: list[PipelineObserver] | None = None,
    ) -> None: ...

    def run(self, from_filter: str | None = None) -> None:
        """Execute filters in order, optionally starting from `from_filter`.

        Args:
            from_filter: Value of AbstractFilter.name to start from.
                         All preceding filters are skipped (on_skip is fired).
                         None means run all filters.
        """

    def add_filter(self, f: AbstractFilter) -> None: ...
    def add_observer(self, o: PipelineObserver) -> None: ...
```

### Rules

- **Only `src/main.py`** instantiates `FilterChain`. Never instantiate it inside a filter or test helper.
- Filters are executed in the **exact order** of the `filters` list — do not rely on any other ordering guarantee.
- `run()` is fail-fast: any uncaught exception in `filter.execute()` propagates immediately and aborts the pipeline. Do not catch exceptions inside `process()` to suppress them.
- The `from_filter` value must match `AbstractFilter.name` exactly (case-sensitive). An unrecognized name raises `ValueError`.

### Adding a new filter to the chain

Register the new concrete filter instance in `src/main.py`. Position in the list determines execution order.

```python
# src/main.py  (excerpt)
chain = FilterChain(
    filters=[
        PreprocessingFilter(),
        TreeFilter(),
        WordGraphFilter(),       # ← insert new filters here, in pipeline order
        SentenceGraphFilter(),
        ...
    ],
    observers=[LoggingObserver()],
)
```

---

## `observers.py` — Observer

### Contract

```python
class PipelineObserver(ABC):
    @abstractmethod
    def on_start(self, filter_name: str) -> None: ...

    @abstractmethod
    def on_complete(self, filter_name: str, elapsed: float) -> None: ...

    @abstractmethod
    def on_skip(self, filter_name: str) -> None: ...


class LoggingObserver(PipelineObserver):
    """Default observer: prints timestamped status lines to stdout."""
```

### Rules

- Add new observers **only** by subclassing `PipelineObserver` — never modify `FilterChain._notify_*` methods.
- Register observers via `FilterChain.__init__(observers=[...])` or `FilterChain.add_observer()` in `main.py`.
- Observers must be **side-effect only** — they must not modify filter inputs, outputs, or pipeline state.
- `on_complete` receives `elapsed` in seconds (float); use it for timing, not for correctness checks.
- Exceptions raised inside an observer do not propagate — they are logged and swallowed so they never abort the pipeline.

### When to add a new observer

Only when you need to react to pipeline events without coupling the logic to the filters themselves. Examples: progress bars, benchmark recorders, audit logs. Do **not** use observers to implement retry logic or conditional branching — that belongs in `FilterChain`.

---

## `strategies.py` — Strategy

### Contract

```python
class CommunityDetectionStrategy(ABC):
    @abstractmethod
    def detect(self, graph: Graph, k: int) -> Communities:
        """Partition graph nodes into k communities.

        Args:
            graph: Unified graph from final_graph.json.
            k: Target number of communities (K=10 by default).

        Returns:
            Mapping community_id → [node_key, ...].
        """


class ProgressiveEdgeCuttingStrategy(CommunityDetectionStrategy):
    """Default strategy: sort edges by weight, cut lowest-weight edges
    while degree > 1, stop when k components are reached."""
```

### Rules

- `Strategy` is scoped exclusively to community detection. Do **not** use this pattern for other algorithmic variations in the project.
- **All traversal is delegated to `src.shared.graph`** — `ProgressiveEdgeCuttingStrategy` uses `copy_graph`, `iter_edges`, `has_edge`, `degree`, `remove_edge`, `count_components`, and `connected_components` from that sub-package. Never reimplement BFS/DFS inside a strategy.
- Inject a non-default strategy via `CommunityDetectionFilter.__init__(strategy=...)` in `main.py`, not by modifying the filter class itself.
- `detect()` must not mutate the `graph` argument — call `copy_graph()` from `src.shared.graph`.

---

## Import rules

```
src/shared/  →  may be imported by any filter or main.py
src/*.py     →  must NOT import from each other
src/config.py and src/types.py  →  allowed everywhere
```

Concretely:

```python
# CORRECT — any concrete filter
from src.shared.filter_base import AbstractFilter
from src.shared.graph import add_edge, increase_weight, degree
from src.types import Graph
from src.config import S3_KEYS

# WRONG — filter importing another filter
from src.word_graph import build_word_graph  # forbidden
```

---

## `storage.py` — S3 Storage Adapter

### Contract

```python
def get_storage() -> S3Storage: ...  # singleton factory

class S3Storage:
    def read_json(self, name: str) -> Any: ...
    def write_json(self, name: str, data: Any) -> None: ...
    def write_text(self, name: str, text: str) -> None: ...
    def exists(self, name: str) -> bool: ...
    def delete(self, name: str) -> None: ...
```

`name` is the artifact filename from `S3_KEYS` (e.g. `"word_graph.json"`). The `pipeline/` prefix is added internally — callers never include it.

### Rules

- Call `get_storage()` instead of instantiating `S3Storage` directly.
- `read_json` / `write_json` handle UTF-8 serialization; callers pass Python objects, not raw strings.
- `write_text` is for `output_format == "text"` (currently only `analysis.py`).
- Do not add retry logic inside `S3Storage` — let boto3 exceptions propagate to `FilterChain` (fail-fast).

---

## `cache.py` — Redis Cache Adapter

### Contract

```python
def get_cache() -> RedisCache: ...  # singleton factory

class RedisCache:
    def get(self, name: str) -> Any | None: ...
    def set(self, name: str, obj: Any) -> None: ...
    def delete(self, name: str) -> None: ...
    def flush(self) -> None: ...
```

`name` is `AbstractFilter.name` (e.g. `"word_graph"`). The `filter:` prefix is added internally.

### Rules

- Call `get_cache()` instead of instantiating `RedisCache` directly.
- `flush()` deletes only keys matching `filter:*` — it does not flush the entire Redis database.
- Results are serialized with `pickle` — only store objects that are safely picklable.
- Do not set TTL on cache entries — cache lifetime is managed via `make clean` / `RedisCache.flush()`.

---

## `graph/` — Graph Utility Sub-package

See [`graph/CLAUDE.md`](graph/CLAUDE.md) for the full contract of each module. Summary:

| Module | Responsibility |
|--------|----------------|
| `ops.py` | `add_edge`, `increase_weight`, `remove_edge`, `iter_edges`, `copy_graph` |
| `metrics.py` | `degree`, `weighted_degree`, `node_count`, `edge_count`, `density`, `average_weight` |
| `traversal.py` | `bfs`, `dfs`, `reachable`, `connected_components`, `count_components`, `is_connected` |
| `validate.py` | `is_symmetric`, `invalid_prefixes`, `isolated_nodes`, `assert_valid` |

**Key rule:** `increase_weight` is the primary write operation for co-occurrence graphs — use it instead of `add_edge` whenever a pair can appear more than once. `merge_graphs` is **not** in `graph/`; it is a private helper inside `final_graph.py`.

---

## Non-negotiable rules

- **No domain logic in `src/shared/`** — no graph algorithms, no NLP, no weight formulas.
- **No imports of concrete filters** — `src/shared/*.py` must never import from `src/preprocessing.py`, `src/tree.py`, etc.
- **No external graph libraries** — even here, NetworkX and equivalents are forbidden.
- **Docstrings on every public class and method** — format: one-line summary, blank line, `Args:` and `Returns:` sections.
- **Type hints on every signature** — no `Any` unless truly unavoidable (document why when used).
