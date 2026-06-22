.PHONY: help setup install \
        build docker-up docker-down docker-restart docker-logs docker-status \
        frontend-build frontend frontend-logs frontend-bundle frontend-test \
        gen-data init-data run clean \
        preprocessing tree word-graph sentence-graph \
        comment-graph final-graph community-detection \
        metrics analysis \
        docs docs-build \
        test test-cov env-test

# ── Datasets ───────────────────────────────────────────────────────────────────
# Single source of truth for which corpus feeds the pipeline. `init-data` always
# uploads the resolved file to MinIO as the raw input (S3_KEYS['raw'] =
# comments.json), so the pipeline contract never changes — only the source does.
#
#   make init-data                 # canonical ~200-comment set (20 per topic)
#   make init-data DATASET=large   # 2000-comment stress set
#   make init-data DATASET=data/custom.json   # a raw path also works
#
# Presets (name → file). Add a new corpus by adding one DATASET_<name> line.
DATASET ?= canonical
DATASET_canonical := data/comments_200.json
DATASET_small     := data/comments.json
DATASET_multi     := data/comments_multi.json
DATASET_large     := data/comments_2000.json

# Resolve a preset name to its path; fall back to DATASET itself for raw paths.
DATASET_PATH := $(or $(DATASET_$(DATASET)),$(DATASET))

# Defaults for gen-data (override per invocation, e.g. make gen-data COUNT=2000).
COUNT ?= 200
SEED  ?= 42

# ── Help ───────────────────────────────────────────────────────────────────────

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "First-time setup (fresh machine, Debian/Ubuntu only)"
	@echo "  setup                Install Docker, uv, and Python 3.11 — run once before anything else"
	@echo ""
	@echo "Local tooling"
	@echo "  install              Install all dependencies via uv (for docs/tests outside Docker)"
	@echo ""
	@echo "Infrastructure"
	@echo "  build                Build the app Docker image"
	@echo "  docker-up            Start all services in background (MinIO + Redis + app + frontend)"
	@echo "  docker-down          Stop and remove all containers and networks"
	@echo "  docker-restart       Rebuild image and restart all services"
	@echo "  docker-logs          Follow logs from all services"
	@echo "  docker-status        Show running containers and health"
	@echo "  frontend-build       Build the frontend image"
	@echo "  frontend             Start the frontend service"
	@echo "  frontend-logs        Follow logs from the frontend service"
	@echo "  frontend-bundle      Generate frontend bundles from pipeline artifacts"
	@echo "  frontend-test        Run the frontend test suite (vitest) in the container"
	@echo ""
	@echo "Pipeline"
	@echo "  gen-data             Generate a dataset locally (DATASET=, COUNT=, SEED=; default canonical/200)"
	@echo "  init-data            Upload the selected dataset to MinIO as the raw input"
	@echo "                       (presets: DATASET=canonical|small|multi|large; default canonical/~200)"
	@echo "  run                  Run the full pipeline (all 9 filters) inside Docker"
	@echo "  clean                Flush Redis cache + delete S3 pipeline artifacts (keeps comments.json)"
	@echo ""
	@echo "Individual filters (run inside Docker)"
	@echo "  preprocessing        Filter 1 — tokenization, stopwords, normalization"
	@echo "                       (force rerun: make preprocessing ARGS=--no-cache)"
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
	@echo "  env-test             Run environment integrity tests on the host (setup, build, docker-up)"
	@echo ""
	@echo "Docs"
	@echo "  docs                 Serve documentation locally (localhost:8000)"
	@echo "  docs-build           Build static documentation site"

# ── First-time setup ───────────────────────────────────────────────────────────

setup:
	@echo "==> Installing system packages (requires sudo, Debian/Ubuntu only)"
	sudo apt-get update -qq
	sudo apt-get install -y curl git docker.io docker-compose-v2
	sudo systemctl enable --now docker
	sudo usermod -aG docker $$USER
	@echo "==> Installing uv"
	curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "==> Installing Python 3.11 via uv"
	$$HOME/.local/bin/uv python install 3.11
	@echo ""
	@echo "Setup complete."
	@echo "Reopen the terminal (or run 'newgrp docker') for Docker group changes to take effect."
	@echo "Then run: make install && make docker-up && make init-data"

# ── Local tooling ──────────────────────────────────────────────────────────────

install:
	uv sync --all-groups

# ── Infrastructure ─────────────────────────────────────────────────────────────

build:
	docker compose build

frontend-build:
	docker compose build frontend

docker-up:
	docker compose up -d

frontend:
	docker compose up -d frontend

docker-down:
	docker compose down

docker-restart:
	docker compose down
	docker compose build
	docker compose up -d

frontend-logs:
	docker compose logs -f frontend

frontend-bundle:
	S3_ENDPOINT_URL=$${S3_ENDPOINT_URL:-http://localhost:9000} uv run python -m scripts.build_bundle $(ARGS)

frontend-test:
	docker compose exec -T frontend npm test

docker-logs:
	docker compose logs -f

docker-status:
	docker compose ps

# ── Pipeline ───────────────────────────────────────────────────────────────────

gen-data:
	uv run python -m scripts.generate_comments --count $(COUNT) --seed $(SEED) --out $(DATASET_PATH)

init-data:
	docker compose run --rm app uv run python -m scripts.init_data $(DATASET_PATH)

run:
	docker compose run --rm app uv run python -m src.main

clean:
	docker compose run --rm app uv run python -m scripts.clean

# ── Individual filters ─────────────────────────────────────────────────────────

# Pass extra args via ARGS, e.g.: make preprocessing ARGS=--no-cache
preprocessing:
	docker compose run --rm app uv run python -m src.preprocessing $(ARGS)

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

test: build
	docker compose -f docker-compose.yml -f docker-compose.ci.yml run --rm app uv run pytest

test-cov: build
	docker compose -f docker-compose.yml -f docker-compose.ci.yml run --rm app uv run pytest --cov=src --cov-report=term-missing

env-test:
	uv run pytest -m env -v --tb=short tests/integration/test_environment.py

# ── Docs ───────────────────────────────────────────────────────────────────────

docs:
	uv run mkdocs serve

docs-build:
	uv run mkdocs build
