"""Entry point for ``python -m src.tree`` (target of ``make tree``).

Supports ``--no-cache`` to force reprocessing, bypassing the Redis cache read.
"""

import argparse

from src.tree import TreeFilter


def main() -> None:
    """Parse CLI flags and run the tree filter."""
    parser = argparse.ArgumentParser(prog="python -m src.tree")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force reprocessing, ignoring any cached result in Redis.",
    )
    args = parser.parse_args()
    TreeFilter().execute(use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
