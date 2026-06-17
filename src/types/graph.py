"""Graph type: adjacency matrix backed by a node name-to-index mapping."""

from dataclasses import dataclass, field
from typing import TypeAlias

# Node key convention: "w_word" (word), "s_12" (sentence), "c_3" (comment).
NodeKey: TypeAlias = str


@dataclass
class Graph:
    """Undirected weighted graph stored as an adjacency matrix.

    The matrix grows one node at a time: registering a name not yet in
    `index` appends a 0.0 column to every existing row, then appends a new
    full row of 0.0 to `matrix`. There is no pre-allocated capacity — the
    structure is already O(n^2) at any final size, so incremental growth
    costs the same total work as allocating it upfront.

    Attributes:
        nodes: Index -> node name, in insertion order.
        index: Node name -> index; the inverse mapping of `nodes`.
        matrix: matrix[i][j] is the weight between nodes[i] and nodes[j].
            0.0 means "no edge" — safe because every weight formula in this
            project produces strictly positive weights. Always symmetric:
            matrix[i][j] == matrix[j][i].
    """

    nodes: list[NodeKey] = field(default_factory=list)
    index: dict[NodeKey, int] = field(default_factory=dict)
    matrix: list[list[float]] = field(default_factory=list)
