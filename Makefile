.PHONY: help install run clean \
        preprocessing tree word-graph sentence-graph \
        comment-graph final-graph community-detection \
        metrics analysis \
        docs docs-build \
        test test-cov

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Environment"
	@echo "  install              Install all dependencies via uv"
	@echo ""
	@echo "Pipeline"
	@echo "  run                  Run the full pipeline (all 9 filters)"
	@echo ""
	@echo "Individual filters"
	@echo "  preprocessing        Filter 1 — tokenization, stopwords, normalization"
	@echo "  tree                 Filter 2 — N-ary tree construction"
	@echo "  word-graph           Filter 3 — word co-occurrence graph"
	@echo "  sentence-graph       Filter 4 — sentence graph"
	@echo "  comment-graph        Filter 5 — comment graph"
	@echo "  final-graph          Filter 6 — unified graph"
	@echo "  community-detection  Filter 7 — progressive edge cutting + BFS/DFS"
	@echo "  metrics              Filter 8 — centrality + modularity Q"
	@echo "  analysis             Filter 9 — report generation"
	@echo ""
	@echo "Docs"
	@echo "  docs                 Serve documentation locally (localhost:8000)"
	@echo "  docs-build           Build static documentation site"
	@echo ""
	@echo "Tests"
	@echo "  test                 Run test suite"
	@echo "  test-cov             Run tests with coverage report"
	@echo ""
	@echo "Cleanup"
	@echo "  clean                Remove all intermediate data files and cache"

# ── Environment ────────────────────────────────────────────────────────────────

install:
	uv sync --all-groups

# ── Pipeline ───────────────────────────────────────────────────────────────────

run:
	uv run python src/main.py

# ── Individual filters ─────────────────────────────────────────────────────────

preprocessing:
	uv run python -m src.preprocessing

tree:
	uv run python -m src.tree

word-graph:
	uv run python -m src.word_graph

sentence-graph:
	uv run python -m src.sentence_graph

comment-graph:
	uv run python -m src.comment_graph

final-graph:
	uv run python -m src.final_graph

community-detection:
	uv run python -m src.community_detection

metrics:
	uv run python -m src.metrics

analysis:
	uv run python -m src.analysis

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	uv run pytest

test-cov:
	uv run pytest --cov=src --cov-report=term-missing

# ── Docs ───────────────────────────────────────────────────────────────────────

docs:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build

# ── Cleanup ────────────────────────────────────────────────────────────────────

clean:
	rm -f data/preprocessed.json \
	      data/tree.json \
	      data/word_graph.json \
	      data/sentence_graph.json \
	      data/comment_graph.json \
	      data/final_graph.json \
	      data/communities.json \
	      data/metrics.json \
	      data/report.txt
	rm -rf data/cache/
