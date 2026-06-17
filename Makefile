.PHONY: help install \
        build docker-up docker-down docker-restart docker-logs docker-status \
        init-data run clean \
        preprocessing tree word-graph sentence-graph \
        comment-graph final-graph community-detection \
        metrics analysis \
        docs docs-build \
        test test-cov

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Local tooling"
	@echo "  install              Install all dependencies via uv (for docs/tests outside Docker)"
	@echo ""
	@echo "Infrastructure"
	@echo "  build                Build the app Docker image"
	@echo "  docker-up            Start all services in background (MinIO + Redis + app)"
	@echo "  docker-down          Stop and remove all containers and networks"
	@echo "  docker-restart       Rebuild image and restart all services"
	@echo "  docker-logs          Follow logs from all services"
	@echo "  docker-status        Show running containers and health"
	@echo ""
	@echo "Pipeline"
	@echo "  init-data            Upload data/comments.json to MinIO (run once before first pipeline run)"
	@echo "  run                  Run the full pipeline (all 9 filters) inside Docker"
	@echo "  clean                Flush Redis cache + delete S3 pipeline artifacts (keeps comments.json)"
	@echo ""
	@echo "Individual filters (run inside Docker)"
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
	@echo "Tests"
	@echo "  test                 Run test suite inside Docker"
	@echo "  test-cov             Run tests with coverage report inside Docker"
	@echo ""
	@echo "Docs"
	@echo "  docs                 Serve documentation locally (localhost:8000)"
	@echo "  docs-build           Build static documentation site"

# ── Local tooling ──────────────────────────────────────────────────────────────

install:
	uv sync --all-groups

# ── Infrastructure ─────────────────────────────────────────────────────────────

build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-restart:
	docker compose down
	docker compose build
	docker compose up -d

docker-logs:
	docker compose logs -f

docker-status:
	docker compose ps

# ── Pipeline ───────────────────────────────────────────────────────────────────

init-data:
	docker compose run --rm app uv run python scripts/init_data.py

run:
	docker compose run --rm app uv run python -m src.main

clean:
	docker compose run --rm app uv run python scripts/clean.py

# ── Individual filters ─────────────────────────────────────────────────────────

preprocessing:
	docker compose run --rm app uv run python -m src.preprocessing

tree:
	docker compose run --rm app uv run python -m src.tree

word-graph:
	docker compose run --rm app uv run python -m src.word_graph

sentence-graph:
	docker compose run --rm app uv run python -m src.sentence_graph

comment-graph:
	docker compose run --rm app uv run python -m src.comment_graph

final-graph:
	docker compose run --rm app uv run python -m src.final_graph

community-detection:
	docker compose run --rm app uv run python -m src.community_detection

metrics:
	docker compose run --rm app uv run python -m src.metrics

analysis:
	docker compose run --rm app uv run python -m src.analysis

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	docker compose -f docker-compose.yml -f docker-compose.ci.yml run --rm app uv run pytest

test-cov:
	docker compose -f docker-compose.yml -f docker-compose.ci.yml run --rm app uv run pytest --cov=src --cov-report=term-missing

# ── Docs ───────────────────────────────────────────────────────────────────────

docs:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build
