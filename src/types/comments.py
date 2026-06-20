"""Type aliases for raw and preprocessed comment data."""

from typing import TypeAlias

# Raw input from data/comments.json. "topic" is the gold label, kept only here
# for final validation (re-joined by "id"); it must not flow down the pipeline.
RawComment: TypeAlias = dict  # {"id": int, "topic": str, "text": str}

# Output of the preprocessing/ package. No "topic": topic detection is
# unsupervised, so the label is dropped from this point on.
ProcessedComment: TypeAlias = dict  # {"id": int, "sentences": list[list[str]]}
