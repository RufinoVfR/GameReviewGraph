"""Flush Redis filter cache and delete S3 pipeline artifacts.

Preserves pipeline/comments.json (raw input). Run via: make clean
"""

from src.shared.cache import get_cache
from src.shared.storage import get_storage
from src.config import S3_KEYS

_PRESERVE = {"raw"}


def main() -> None:
    """Flush Redis cache and remove all pipeline artifacts from S3."""
    get_cache().flush()
    print("[clean] Redis cache flushed.")

    storage = get_storage()
    for key, name in S3_KEYS.items():
        if key in _PRESERVE:
            continue
        storage.delete(name)
        print(f"[clean] Deleted s3://.../{name}")

    print("[clean] Done.")


if __name__ == "__main__":
    main()
