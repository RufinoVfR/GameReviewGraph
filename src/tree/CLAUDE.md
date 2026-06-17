# src/tree/ — Context for Claude

> **Tree position:** `/ (root) → src/ → src/tree/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for the filter template, `S3_KEYS`, and I/O rules.
> GoF infrastructure: see [`../shared/CLAUDE.md`](../shared/CLAUDE.md) for `AbstractFilter` and the Template Method contract.
> Upstream contract: see [`../preprocessing/CLAUDE.md`](../preprocessing/CLAUDE.md) for the shape of the input it consumes.

---

## What this directory is

The pipeline's **second filter** (Filtro 2, issue #2 / US03 & US04). It turns the
normalized token hierarchy into the **N-ary tree** Dataset → Comment → Sentence →
Word, the project's mandatory from-scratch data structure. Its artifact
(`tree.json`) feeds the whole graph track: `word_graph` reads it directly, and
`sentence_graph` / `comment_graph` / `final_graph` consume it as a secondary input.

It is a **package**, not a single file — mirroring the Filter 1 model — because
the structure, the construction pass, and the serialization are distinct concerns
kept in separate modules from the filter orchestration. The tree itself uses
**only native Python** (classes, lists, dicts): no external graph or tree library.

---

## I/O contract (authoritative — do not change)

- **Input** `input_key="preprocessed"` → `preprocessed.json`:
  `list[{"id": int, "sentences": list[list[str]]}]`.
  Delivered by `AbstractFilter.execute()` to `process()` — **never open a file inside the filter.**
- **Output** `output_key="tree"` → `tree.json`: a **uniform-node nested JSON**
  (`{"type", "children", ...}`), serializable (no cycles). The live tree uses
  `parent` back-references; serialization emits only the nested hierarchy and the
  `parent` links are **rebuilt on load** (`from_dict`).
- `topic` is **forbidden** in `tree.json` (unsupervised detection) — the input
  already omits it; never reintroduce it.

### `tree.json` shape (closed contract — `docs/guia_implementacao.md` C.1)

```json
{
  "type": "dataset",
  "children": [
    {"type": "comment", "id": 3, "children": [
      {"type": "sentence", "index": 12, "children": [
        {"type": "word", "value": "jogo",  "position": 0},
        {"type": "word", "value": "trava", "position": 1}
      ]}
    ]}
  ]
}
```

- `comment.id` → the comment id (becomes `c_<id>` downstream).
- `sentence.index` → **global** sentence counter across the whole dataset (becomes `s_<index>`).
- `word.value` → the normalized surface token (becomes `w_<value>`).
- `word.position` → the token's position **within its sentence** (input to the
  positional co-occurrence weight in `word_graph`).
- **No `w_`/`s_`/`c_` prefixes are stored** in `tree.json` — the graph filters
  apply the prefixes when they read the artifact (see "Downstream read path").

### Downstream read path (no cross-filter imports)

Downstream graph filters **never import this package** and never rebuild a
`NaryTree`. They receive `tree.json` as a plain nested dict and walk it through
the shared readers in [`../shared/tree.py`](../shared/tree.py) —
`iter_comments` / `iter_sentences` / `iter_words` / `hierarchical_edges` — exactly
as graph (de)serialization lives in `src/shared/graph` rather than in each graph
filter. The prefix derivation (`w_`/`s_`/`c_`) and the `(w_key, s_key)` /
`(s_key, c_key)` hierarchical edges live in that shared module, **not here**, so
they are defined once and reused by `word_graph`, `sentence_graph`, `final_graph`.

This package owns only the **producer** side: build the tree from the corpus and
`serialize()` it. The structural weight formulas stay in the graph filters; the
shared readers carry no domain logic.

---

## Module map

```
src/tree/
├── __init__.py    ← re-exports TreeFilter
├── __main__.py    ← TreeFilter().execute()  (target of `make tree` → python -m src.tree); supports --no-cache
├── filter.py      ← TreeFilter(AbstractFilter) — orchestrates process()
├── structure.py   ← TreeNode + NaryTree (data structure + bidirectional navigation, US04)
├── build.py       ← build_from_corpus() — pure construction pass
└── serialize.py   ← serialize() (producer) + from_dict() (test-only round-trip)
```

`filter.py` inherits `AbstractFilter` and implements only `process()`; it declares
`name="tree"`, `input_key="preprocessed"`, `output_key="tree"` as class attributes.
`process(data)` is a thin orchestration: `build_from_corpus(data)` → `serialize(tree)`.

---

## What each module does

- **`structure.py`** — `TreeNode(data, parent, children)` and `NaryTree(root)`.
  `add_child(parent, child_data)` wires the bidirectional link (child → parent and
  parent → child). Navigation accessors (`get_words_of_sentence`,
  `get_sentences_of_comment`, `get_all_word_nodes`) are the **US04 deliverable** —
  they operate on the live `NaryTree` and are exercised by this package's own unit
  tests; access is O(d), d ≤ 3. They are **not** a cross-filter API: downstream
  reads the dict via `src/shared/tree.py`. Hierarchical-edge extraction and the
  `w_`/`s_`/`c_` prefixing live in that shared module, not here.
- **`build.py`** — `build_from_corpus(corpus) -> NaryTree`. Walks
  `list[{"id","sentences"}]`, building the four levels; assigns the **global**
  sentence index and each word's **per-sentence** position. Empty input comments
  are still represented (their `c_<id>` node must survive downstream).
- **`serialize.py`** — `serialize(tree) -> dict` (uniform-node nested form above;
  this is the filter's production output). `from_dict(data) -> NaryTree` (re-links
  every `parent` while descending) is **test-only**: nothing on the production path
  rebuilds a `NaryTree` from the dict — downstream filters walk the dict via
  `src/shared/tree.py`. It is kept for the serialize/deserialize round-trip test.

---

## Non-negotiable rules

- **No external libraries** — the tree is built only with native Python structures.
- **No NLP here** — normalization already happened in `preprocessing/`; this filter
  only structures the already-normalized tokens.
- **No file/S3/Redis I/O in `process()`** — all I/O is inherited from `AbstractFilter.execute()`.
- **No coupling to other filters** — only `src/shared/`, `src/config.py`, `src/types/` may be imported.
- **`topic` never appears** in `tree.json`.
- **Serializable output** — `tree.json` is acyclic; `parent` is reconstructed on load, never serialized.
- **Docstrings + type hints on every function**; code, comments, and commits in English.

---

## Verification

```bash
make tree                 # run the filter in Docker → writes pipeline/tree.json to MinIO
make tree ARGS=--no-cache # force reprocessing, bypassing the Redis cache read
make test                 # unit tests (tests/unit/test_tree.py — use the processed_comments fixture)
```

Register `TreeFilter()` in `src/main.py`'s `FILTERS` list (after `PreprocessingFilter`)
once implemented, so it runs as part of `make run`.
