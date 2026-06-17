"""Global constants, environment variables, and key mappings for the pipeline."""

import os

# ── Community detection ─────────────────────────────────────────────────────────

K: int = 10
MIN_FREQ: int = 2

# ── S3 / MinIO ─────────────────────────────────────────────────────────────────

S3_BUCKET: str = os.environ.get("S3_BUCKET", "game-review-graph")
S3_ENDPOINT_URL: str = os.environ.get("S3_ENDPOINT_URL", "http://minio:9000")
AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "minioadmin")

# ── Redis ──────────────────────────────────────────────────────────────────────

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# ── S3 object key registry ─────────────────────────────────────────────────────
# Maps the logical artifact name (used as AbstractFilter.input_key / output_key)
# to the S3 object key under the pipeline/ prefix.

S3_KEYS: dict[str, str] = {
    "raw":            "comments.json",
    "preprocessed":   "preprocessed.json",
    "tree":           "tree.json",
    "word_graph":     "word_graph.json",
    "sentence_graph": "sentence_graph.json",
    "comment_graph":  "comment_graph.json",
    "final_graph":    "final_graph.json",
    "communities":    "communities.json",
    "metrics":        "metrics.json",
    "report":         "report.txt",
}
