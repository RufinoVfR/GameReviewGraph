"""Type aliases for raw and preprocessed comment data."""

from typing import TypeAlias

# Raw input from data/comments.json
RawComment: TypeAlias = dict  # {"id": int, "topic": str, "text": str}

# Output of preprocessing.py
ProcessedComment: TypeAlias = dict  # {"id": int, "topic": str, "sentences": list[list[str]]}
