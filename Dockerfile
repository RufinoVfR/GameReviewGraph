FROM python:3.11-slim

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/comments.json ./data/comments.json

CMD ["uv", "run", "python", "-m", "src.main"]
