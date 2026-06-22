"""Entry point for ``python -m src.word_graph`` (target of ``make word-graph``).

Supports ``--no-cache`` to force reprocessing, bypassing the Redis cache read.
"""

import argparse

from src.word_graph import WordGraphFilter


def main() -> None:
    """Parse CLI flags and run the word graph filter."""
    parser = argparse.ArgumentParser(prog="python -m src.word_graph")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force reprocessing, ignoring any cached result in Redis.",
    )
    args = parser.parse_args()
    WordGraphFilter().execute(use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
