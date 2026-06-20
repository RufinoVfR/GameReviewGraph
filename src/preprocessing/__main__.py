"""Entry point for ``python -m src.preprocessing`` (target of ``make preprocessing``).

Supports ``--no-cache`` to force reprocessing, bypassing the Redis cache read.
"""

import argparse

from src.preprocessing import PreprocessingFilter


def main() -> None:
    """Parse CLI flags and run the preprocessing filter."""
    parser = argparse.ArgumentParser(prog="python -m src.preprocessing")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force reprocessing, ignoring any cached result in Redis.",
    )
    args = parser.parse_args()
    PreprocessingFilter().execute(use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
