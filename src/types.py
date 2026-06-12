"""Canonical type aliases shared across all pipeline filters."""

from typing import TypeAlias

# Raw input from data/comments.json
RawComment: TypeAlias = dict  # {"id": int, "topic": str, "text": str}

# Output of preprocessing.py
ProcessedComment: TypeAlias = dict  # {"id": int, "topic": str, "sentences": list[list[str]]}

# Adjacency list used by all three graph levels.
# Keys are prefixed: w_ (word), s_ (sentence), c_ (comment).
Graph: TypeAlias = dict[str, dict[str, float]]

# Output of community_detection.py: community_id (1-indexed) → [node_key, ...]
Communities: TypeAlias = dict[int, list[str]]

# Output of metrics.py — see metrics.py for the full schema
Metrics: TypeAlias = dict
