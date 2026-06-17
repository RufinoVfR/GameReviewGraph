"""Type alias for community detection output."""

from typing import TypeAlias

# Output of community_detection.py: community_id (1-indexed) -> [node_key, ...]
Communities: TypeAlias = dict[int, list[str]]
