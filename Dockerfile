FROM python:3.11-slim

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# NLTK ships no corpora; download the ones used by the preprocessing filter
# (Portuguese stopwords + RSLP stemmer) at build time. NLTK_DATA points the
# runtime at this directory so no network access is needed during execution.
ENV NLTK_DATA=/usr/local/nltk_data
RUN uv run python -m nltk.downloader -d /usr/local/nltk_data stopwords rslp

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY data/ ./data/

CMD ["uv", "run", "python", "-m", "src.main"]