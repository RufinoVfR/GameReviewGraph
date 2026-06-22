FROM python:3.11-slim

# Trust PyPI hosts when behind a corporate SSL-intercepting proxy.
RUN pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

# Create the virtualenv via the stdlib venv module (no network needed) and
# install all production dependencies using pip with --trusted-host so the
# download goes through the corporate proxy without certificate errors.
# uv's own TLS stack (rustls) cannot be configured with trusted hosts, so
# we fall back to pip for the actual package downloads.
RUN python -m venv .venv && \
    uv export --no-dev --no-hashes -o /tmp/requirements.txt && \
    .venv/bin/pip install \
        --trusted-host pypi.org \
        --trusted-host files.pythonhosted.org \
        --trusted-host pypi.python.org \
        -r /tmp/requirements.txt

# Make the venv the active Python environment for all subsequent build steps
# and at runtime. UV_NO_SYNC prevents uv run from re-resolving packages when
# the venv is already complete.
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_NO_SYNC=1

# NLTK ships no corpora; download the ones used by the preprocessing filter
# (Portuguese stopwords + RSLP stemmer) at build time. NLTK_DATA points the
# runtime at this directory so no network access is needed during execution.
# PYTHONHTTPSVERIFY=0 is required because NLTK downloads from GitHub raw
# content, which is also intercepted by the corporate SSL proxy.
ENV NLTK_DATA=/usr/local/nltk_data
# Patch ssl before importing NLTK so the corporate proxy's self-signed cert is accepted.
RUN python -c "\
import ssl; \
ssl._create_default_https_context = ssl._create_unverified_context; \
import nltk; \
nltk.download('stopwords', download_dir='/usr/local/nltk_data', quiet=True); \
nltk.download('rslp', download_dir='/usr/local/nltk_data', quiet=True)"

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY data/ ./data/

CMD ["uv", "run", "python", "-m", "src.main"]
