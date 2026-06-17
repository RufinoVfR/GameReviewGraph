# src/preprocessing/ — Context for Claude

> **Tree position:** `/ (root) → src/ → src/preprocessing/`
> Parent context: see [`../CLAUDE.md`](../CLAUDE.md) for the filter template, `S3_KEYS`, and I/O rules.
> GoF infrastructure: see [`../shared/CLAUDE.md`](../shared/CLAUDE.md) for `AbstractFilter` and the Template Method contract.

---

## What this directory is

The pipeline's **first filter** (Filtro 1, issue #1 / US01 & US02). It turns raw
Portuguese comments into normalized, structured tokens that feed the N-ary tree
and, in cascade, every graph. It blocks all downstream filters — nothing else in
`src/` runs until `preprocessed.json` exists.

It is the **only** place NLP is allowed in the project (NLTK; spaCy is not used).
It is a **package**, not a single file, because it concentrates the densest logic
in the pipeline — text cleaning and corpus-wide normalization are kept in separate
modules from the filter orchestration.

---

## I/O contract (authoritative — do not change)

- **Input** `input_key="raw"` → `comments.json`: `list[{"id": int, "topic": str, "text": str}]`.
  Delivered by `AbstractFilter.execute()` to `process()` — **never open a file inside the filter.**
- **Output** `output_key="preprocessed"` → `preprocessed.json`:
  `list[{"id": int, "topic": str, "sentences": list[list[str]]}]` (comment → sentences → tokens).
- `id` and `topic` are **preserved** on every comment — `tree.py`, `comment_graph.py`, and
  `metrics.py` depend on them (`c_<id>` nodes and topic labels). Never return a bare `list[list[list[str]]]`.

---

## Module map

```
src/preprocessing/
├── __init__.py    ← re-exports PreprocessingFilter
├── __main__.py    ← PreprocessingFilter().execute()  (target of `make preprocessing` → python -m src.preprocessing)
├── filter.py      ← PreprocessingFilter(AbstractFilter) — orchestrates process()
├── clean.py       ← pure text/token helpers (no NLP state)
└── normalize.py   ← RSLP grouping key + surface-form representative + stopwords
```

`filter.py` inherits `AbstractFilter` and implements only `process()`; it declares
`name="preprocessing"`, `input_key="raw"`, `output_key="preprocessed"` as class
attributes. `MIN_FREQ` comes from `src/config.py` — never hardcode the threshold.

---

## Pipeline inside `process(data)`

1. **Pass 1 — clean, keeping the comment→sentences→tokens hierarchy:** per comment,
   `to_lowercase` → `remove_punctuation` → `segment_sentences`; per sentence
   `tokenize` → `drop_noise` → `remove_stopwords`. Surface tokens (with accents) are kept.
2. **Corpus pass:** flatten all surviving tokens and call `build_representatives(flat, MIN_FREQ)`.
3. **Pass 2 — apply:** re-walk the hierarchy; each token becomes
   `representatives[group_key(tok)]` if its group survived, otherwise it is dropped.
   Empty sentences are discarded; **the comment is kept** (with `id`/`topic`) even if `sentences` ends up `[]`.
4. Return `list[{"id","topic","sentences"}]`. Token order is preserved (it becomes `position` in `tree`).

---

## Key decision — normalization A1' (no inter-layer coupling)

The RSLP stem is **only an internal grouping key**. The emitted token (which becomes
the `w_<token>` node) is the **most frequent surface form of the group, with its accent**.
This keeps the grouping benefit of stemming without polluting the report with non-words,
and **without any coupling between layers** — the `group_key → representative` map is
built and consumed entirely inside `process()` and never leaves this package.

Other settled decisions (see [`../../docs/decisions.md`](../../docs/decisions.md) §Pré-processamento):
- **Segmentation/tokenization:** pure regex (`re.split(r"[.!?]+", ...)`, `re.findall(r"\w+", ...)`) — no extra NLTK data.
- **Noise:** drop purely numeric tokens and tokens with `len < 3`.
- **Frequency cut:** per group (stem), across the whole corpus, using `MIN_FREQ`.
- **Accent preserved** on the emitted token; accents are folded only to compute the grouping key.

---

## Runtime requirement — NLTK data in Docker

NLTK ships no corpora. The `stopwords` and `rslp` datasets must be downloaded in the
`Dockerfile` (`python -m nltk.downloader -d /usr/local/nltk_data stopwords rslp`, with
`ENV NLTK_DATA=/usr/local/nltk_data`), or the filter crashes at runtime in the container.

---

## Non-negotiable rules

- **NLP stays here** — NLTK may be imported only in this package.
- **No file/S3/Redis I/O in `process()`** — all I/O is inherited from `AbstractFilter.execute()`.
- **No coupling** — the stem→surface map never leaves `process()`; do not expose it via artifacts or to other filters.
- **Docstrings + type hints on every function**; code, comments, and commits in English.
