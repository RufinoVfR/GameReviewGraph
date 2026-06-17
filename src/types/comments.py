"""Type aliases for raw and preprocessed comment data."""

from typing import TypeAlias

# Raw input from data/comments.json
RawComment: TypeAlias = dict  # {"id": int, "topic": str, "text": str}

# Output of the preprocessing/ package
ProcessedComment: TypeAlias = dict  # {"id": int, "topic": str, "sentences": list[list[str]]}
