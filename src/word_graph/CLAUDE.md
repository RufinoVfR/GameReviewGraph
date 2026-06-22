# src/word_graph/ — Context for Claude

> **Tree position:** `/ (root) → src/ → src/word_graph/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for the filter template, `S3_KEYS`, and I/O rules.
> Reads the tree via [`../shared/tree.py`](../shared/tree.py); builds the graph via [`../shared/graph/`](../shared/graph/CLAUDE.md).

---

## What this directory is

The pipeline's **third filter** (Filtro 3, issue #3 / US05) and the first of the
graph track. It turns `tree.json` into the **word co-occurrence graph**: a vertex
per word (`w_<value>`), an edge between words that appear in the same sentence,
weighted by `Σ 1 / (1 + |pos_i - pos_j|)` over every co-occurrence in the corpus.
It is the base of every later graph.

It is a **package** (filter orchestration separate from the domain logic),
mirroring the Filter 1/2 model.

---

## I/O contract

- **Input** `input_key="tree"` → `tree.json` (uniform-node dict), delivered by
  `AbstractFilter.execute()` to `process()`. Read it through the shared readers
  (`src/shared/tree.py`) — never import `src/tree/`.
- **Output** `output_key="word_graph"` → `word_graph.json` = `serialize_graph(graph)`
  (`{"nodes", "index", "matrix"}`).

---

## Module map

```
src/word_graph/
├── __init__.py     ← re-exports WordGraphFilter
├── __main__.py     ← WordGraphFilter().execute()  (target of `make word-graph`); supports --no-cache
├── filter.py       ← WordGraphFilter(AbstractFilter) — process(): build_graph_from_deltas → assert_valid → serialize
└── cooccurrence.py ← word_pair_deltas() — the domain logic (pairing + positional weight)
```

`process()` is thin: `serialize_graph(assert_valid(build_graph_from_deltas(word_pair_deltas(data))))`.

---

## Domain logic — `cooccurrence.py`

`word_pair_deltas(tree)` yields `(w_<value_i>, w_<value_j>, weight)` for every
unordered pair of words **within a sentence**, where
`weight = 1 / (1 + |pos_i - pos_j|)`. `build_graph_from_deltas` accumulates
repeated pairs (the same pair in two sentences sums).

Key rules baked in:

- **Pairing is from scratch** — a `for i: for j in range(i+1, ...)` double loop,
  **not** `itertools.combinations`. Each unordered pair is visited once, so the
  undirected graph is not weighted twice. (The rule that bans libraries targets
  external graph libs and the graded algorithms; `combinations` is stdlib and
  allowed, but hand-rolling removes any ambiguity for the evaluator.)
- **Skip equal values** — a word repeated in a sentence would create a
  `w_x — w_x` self-loop, which `assert_valid` forbids; the `value` guard drops it.
- **Edge-driven nodes** — a word that never co-occurs with a *different* word
  (e.g. a one-word sentence) does not become a node. This is harmless downstream:
  the sentence graph reads `|sa|` from the tree and a missing pair weighs 0 either
  way. No weight threshold is applied here — sparsification happens later in the
  MST / progressive edge cutting (Filter 7).

---

## Non-negotiable rules

- **Domain logic stays in `cooccurrence.py`**, never in `src/shared/graph` (which
  forbids domain logic). The positional weight formula is word-graph-specific.
- **No imports between filters** — only `src/shared/`, `src/config.py`, `src/types/`.
- **No file/S3/Redis I/O in `process()`** — inherited from `AbstractFilter.execute()`.
- **Docstrings + type hints on every function**; code, comments, and commits in English.

---

## Verification

```bash
make word-graph                 # run in Docker → writes word_graph.json to MinIO
make word-graph ARGS=--no-cache # force reprocessing
make test                       # unit tests (tests/unit/test_word_graph.py)
```

Tests cover: positional weights within a sentence, repeated-value skip, isolated
word absent, cross-sentence accumulation, symmetry and `w_` prefixes via
`assert_valid`.
