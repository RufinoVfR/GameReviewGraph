# GameReviewGraph — Claude Code Context

> **Context tree root.** Each subdirectory with a `CLAUDE.md` carries deeper, scope-specific guidance.
> Navigate down for more detail:
>
> ```
> / (root)  ← you are here: project-wide rules, architecture, algorithms
> ├── docs/CLAUDE.md           — MkDocs pages, nav map, content ownership
> ├── src/CLAUDE.md            — filter contracts, S3/Redis I/O, implementation rules
> ├── src/preprocessing/CLAUDE.md — Filtro 1 package: NLP, normalization A1', I/O contract
> └── src/shared/CLAUDE.md     — GoF infrastructure: AbstractFilter, FilterChain, Observer, Strategy, storage, cache
> ```
>
> When working inside a subdirectory, read its `CLAUDE.md` first, then this file for project-wide constraints.

---

## Project Overview

Academic project for FGA0030 (Data Structures 2, UnB 2026/1). Transforms a corpus of ~200 fictional game reviews in Portuguese into a three-level hierarchical graph structure and detects semantic communities (topics) via progressive edge cutting. Pure Python implementation — no external graph libraries. Deadline: **22/06/2026 (last GitHub commit)**.

---

## Architecture

```
comments (text) [MinIO: pipeline/comments.json]
    → preprocessing/         # package: tokenization, stopwords, normalization (decision A1')
    → tree.py                # N-ary Tree: Dataset → Comment → Sentence → Word
    → word_graph.py          # word co-occurrence graph (positional weight)
    → sentence_graph.py      # sentence graph (derived from word graph)
    → comment_graph.py       # comment graph (derived from sentence graph)
    → final_graph.py         # unified graph: all 3 levels + hierarchical edges
    → community_detection.py # progressive edge cutting + BFS/DFS
    → metrics.py             # weighted degree centrality + modularity Q
    → analysis.py            # report generation and interpretation
    → main.py                # entry point — instantiates FilterChain
```

Filters communicate via **MinIO S3** (JSON artifacts under `pipeline/` prefix).
Filter results are cached in **Redis** (`filter:<name>` keys) to skip reprocessing.
All pipeline infrastructure lives in `src/shared/` — see `src/shared/CLAUDE.md`.

**Internal graph representation:** adjacency matrix backed by a name→index mapping, not an adjacency dict. `Graph` (see `src/types.py`) is a dataclass with `nodes: list[str]` (index → name), `index: dict[str, int]` (name → index), and `matrix: list[list[float]]` (`matrix[i][j] == 0.0` means no edge — weights are always positive in this project's formulas, so `0.0` is a safe sentinel). The matrix grows one node at a time (append a column to every row + append a new row) — no pre-allocated capacity, since the structure is already O(n²) at any final size. Node prefixes: `w_word`, `s_12`, `c_3`.

---

## Non-Negotiable Rules

- **Never use external graph libraries** (NetworkX, igraph, graph-tool, etc.) — this is a strict academic requirement worth -5.0 points if violated
- **Never use libraries for the main algorithms** — BFS, DFS, minimum spanning tree (Prim), edge cutting, centrality, and modularity must be implemented from scratch by the team
- **NLP libraries ARE allowed** (NLTK, spaCy) — only for preprocessing
- **Never commit directly to main** — use branches and PRs
- **Never skip docstrings** — every function must have one; it is part of the evaluation criteria
- **Never hardcode S3 keys or Redis keys** — use `S3_KEYS` from `src/config.py` and let `AbstractFilter` handle I/O
- **Never add Claude as co-author** — omit `Co-Authored-By: Claude` from every commit message, without exception
- **Language:** all code, comments, docstrings, and commit messages in **English**; input data and output reports in **Portuguese**

---

## Key Algorithms (Implement From Scratch)

### Edge Weight Formulas

```python
# Word graph — positional co-occurrence weight
weight(wi, wj) = Σ 1 / (1 + |pos(wi) - pos(wj)|)  # sum over all sentences

# Sentence graph — normalized word relation average
weight(sa, sb) = Σ weight(wi, wj) / (|sa| × |sb|)  # wi ∈ sa, wj ∈ sb

# Comment graph — normalized sentence relation average
weight(ca, cb) = Σ weight(si, sj) / (|ca| × |cb|)  # si ∈ ca, sj ∈ cb
```

### Community Detection (MST + Progressive Edge Cutting)

The final graph is reduced to a Minimum Spanning Tree before cutting — this keeps the edge-cutting step's input sparse (V−1 edges instead of the full dense graph) while still respecting all original weights.

```
1. Build a Minimum Spanning Tree (MST) of the final graph via Prim's algorithm
   (dense/array variant, O(V²) — no priority queue needed, since the graph
   is already an adjacency matrix)
2. Sort the MST's edges ascending by weight
3. For each edge (u, v): if degree(u) > 1 AND degree(v) > 1 → remove it
4. After each removal → run BFS/DFS to count connected components
5. Stop when components == K (K=10) or no more edges can be removed
```

Why Prim over Kruskal here: the project's graphs are dense and already stored as adjacency matrices, so dense Prim is O(V²) with no extra data structures, versus Kruskal's O(E log E) (≈ O(V² log V) on a dense graph) which would require extracting and sorting all edges plus a Union-Find structure. The `degree(u) > 1 AND degree(v) > 1` guard is kept even though every MST cut splits the tree into exactly two components — it protects leaf nodes (degree 1) from being isolated as singleton communities prematurely.

### Modularity Q

```
Q = (1/2m) × Σ [Aij - (ki × kj / 2m)] × δ(ci, cj)
# m = total edges, ki = weighted degree of i, δ = 1 if same community
```

---

## Data

- **Source:** ~200 fictional comments in Portuguese, AI-generated via structured prompts
- **Topics (10):** desempenho, narrativa, multiplayer, interface, progressão, áudio, gráficos, controles, conteúdo pós-lançamento, suporte técnico
- **Distribution:** 20 comments per topic
- **Location:** `data/comments.json` locally; uploaded to MinIO as `pipeline/comments.json` via `make init-data`
- **Format example:**
  ```json
  {"id": 1, "topic": "desempenho", "text": "O jogo trava muito depois da atualização."}
  ```

---

## Development Conventions

```python
# Imports: stdlib → third-party → local
import nltk
from src.shared.filter_base import AbstractFilter
from src.types import Graph

# Every concrete filter: inherit AbstractFilter, implement only process()
class WordGraphFilter(AbstractFilter):
    name = "word_graph"
    input_key = "tree"
    output_key = "word_graph"

    def process(self, data: dict) -> Graph:
        """Build word co-occurrence graph from the N-ary tree.

        Args:
            data: Serialized NaryTree from MinIO.

        Returns:
            Adjacency dict mapping word node → {neighbor: weight}.
        """
```

- Python 3.11+
- Dependencies managed via **uv** (`pyproject.toml`) — no `requirements.txt`
- One module per graph level — do not mix responsibilities across files
- All execution goes through Docker via `make` — never call `python`/`python3` directly

---

## Verification Commands

All execution goes through `make`. Never call `python`/`python3` directly.

```bash
# First-time setup
make install       # install deps locally (for docs/tests tooling)
make docker-up     # start MinIO + Redis + app in background
make init-data     # upload data/comments.json to MinIO

# Run full pipeline
make run

# Run a specific filter in isolation (inside Docker)
make preprocessing
make tree
make word-graph

# Infrastructure
make docker-status  # check running containers
make docker-logs    # follow all service logs
make docker-restart # rebuild + restart

# Cleanup
make clean          # flush Redis cache + delete S3 pipeline artifacts
make docker-down    # stop all containers
```

After implementing any module, run it via `make` and confirm the output artifact appears in MinIO before proceeding to the next.

---

## Expected Output Format

```
=== Comunidade 1 — Tópico: Desempenho ===
Termos centrais: fps, travamento, lag, otimizacao, queda
Comentários associados: c_3, c_17, c_42
Modularidade Q: 0.74

=== Comunidade 2 — Tópico: Narrativa ===
Termos centrais: historia, personagem, campanha, missao, enredo
...
```

---

## Academic Evaluation Criteria (for awareness)

| Criterion | Weight | Key Risk |
|-----------|--------|----------|
| Problem definition | 0.5 | — |
| Data quality | 1.0 | LLM-generated data must be coherent |
| Implementation | 3.5 | Modularity, legibility, correct graph modeling |
| Graph algorithms | 2.0 | Must be implemented from scratch — highest penalty risk |
| Result analysis | 2.0 | Semantic interpretation of communities |
| Final presentation | 1.0 | All required slides must be present |

**Zero-score penalties:** no graphs used, code doesn't run, no GitHub, no presentation, project unrelated to NLP.
