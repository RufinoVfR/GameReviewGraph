"""FinalGraphFilter — Filter 6 of the pipeline.

Unifies the three relational graphs (``word_graph``, ``sentence_graph``,
``comment_graph``) and the tree's **hierarchical edges** into a single
``Graph``. Vertices already arrive prefixed from their sub-graphs (``w_``,
``s_``, ``c_``), so the three node sets merge without key conflict.

On top of the merged relational edges, two families of hierarchical edges link
the levels together — one ``Word→Sentence`` edge per word and one
``Sentence→Comment`` edge per sentence (see ``src/shared/tree.py``). Each
hierarchical edge carries a **membership weight**::

    weight(child → parent) = 1 / (number of children of that parent)

i.e. ``Word→Sentence`` weighs ``1 / |words in the sentence|`` and
``Sentence→Comment`` weighs ``1 / |sentences in the comment|``. The weight must
be strictly positive because ``0.0`` is the matrix's "no edge" sentinel; the
membership form mirrors the normalization-by-size convention already used by the
relational weight formulas. See ``docs/decisions.md``.

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()``.
"""

import argparse
from collections import Counter

from src.shared.filter_base import AbstractFilter
from src.shared.graph import (
    add_edge,
    assert_valid,
    deserialize_graph,
    iter_edges,
    new_graph,
    serialize_graph,
)
from src.shared.tree import hierarchical_edges
from src.types import Graph


class FinalGraphFilter(AbstractFilter):
    """Build the unified three-level graph (Filter 6).

    Multi-input filter: the primary artifact is ``comment_graph.json`` and the
    extra artifacts supply the other two relational graphs plus the tree whose
    hierarchical edges link the levels.
    """

    name = "final_graph"
    input_key = "comment_graph"
    extra_input_keys = ["word_graph", "sentence_graph", "tree"]
    output_key = "final_graph"

    def process(self, data: dict) -> dict:
        """Merge the three relational graphs and add the hierarchical edges.

        Unions the word, sentence, and comment graphs into one ``Graph`` (no key
        conflict — vertices are already prefixed and relational edges only link
        same-level nodes), then layers the ``Word→Sentence`` and
        ``Sentence→Comment`` edges from the tree on top, each weighted by the
        membership formula ``1 / (children of parent)``.

        Args:
            data: Multi-input payload ``{"primary": <serialized comment graph>,
                "word_graph": <serialized word graph>, "sentence_graph":
                <serialized sentence graph>, "tree": <tree.json dict>}``.

        Returns:
            Serialized unified graph (``serialize_graph`` output) over
            ``w_``/``s_``/``c_`` nodes — JSON-ready for ``execute()``.
        """
        graph = _merge_graphs(
            deserialize_graph(data["word_graph"]),
            deserialize_graph(data["sentence_graph"]),
            deserialize_graph(data["primary"]),  # comment_graph
        )
        _add_hierarchical_edges(graph, data["tree"])

        assert_valid(graph)
        return serialize_graph(graph)


def _merge_graphs(*graphs: Graph) -> Graph:
    """Union several graphs into one, preserving every edge weight.

    Relational edges only connect same-level nodes (``w↔w``, ``s↔s``, ``c↔c``)
    and the levels use disjoint key prefixes, so no edge of one graph collides
    with an edge of another. The merged node set is collected first and the
    adjacency matrix is allocated once at its final size, then each source's
    edges are copied by mapped index — far cheaper than re-inserting the dense
    word graph one ``add_edge`` (name→index resolution + grow) at a time.

    Args:
        graphs: Graphs to merge, in any order.

    Returns:
        A new ``Graph`` containing every node and edge of the inputs.
    """
    merged = new_graph()
    for graph in graphs:
        for name in graph.nodes:
            if name not in merged.index:
                merged.index[name] = len(merged.nodes)
                merged.nodes.append(name)

    size = len(merged.nodes)
    matrix = [[0.0] * size for _ in range(size)]
    merged.matrix = matrix

    for graph in graphs:
        for node_a, node_b, weight in iter_edges(graph):
            i, j = merged.index[node_a], merged.index[node_b]
            matrix[i][j] = weight
            matrix[j][i] = weight
    return merged


def _add_hierarchical_edges(graph: Graph, tree: dict) -> None:
    """Add the tree's level-linking edges with their membership weights.

    Reads the ``(child, parent)`` hierarchical edges from the tree and weighs
    each by ``1 / (number of children of that parent)``: a ``Word→Sentence``
    edge weighs ``1 / |words in the sentence|`` and a ``Sentence→Comment`` edge
    weighs ``1 / |sentences in the comment|``. Counting raw hierarchical edges
    per parent yields the child count including repeated word values, matching
    how the relational graphs size sentences. ``add_edge`` is idempotent, so a
    repeated word collapses to a single edge with the same deterministic weight;
    a parent always has at least the child producing its edge, so the divisor is
    never zero.

    Args:
        graph: Merged relational graph to mutate in place.
        tree: The deserialized ``tree.json`` dict (the ``dataset`` root).
    """
    edges = hierarchical_edges(tree)
    sizes = Counter(parent for _, parent in edges)
    for child, parent in edges:
        add_edge(graph, child, parent, 1.0 / sizes[parent])


def main() -> None:
    """Parse CLI flags and run the final graph filter."""
    parser = argparse.ArgumentParser(prog="python -m src.final_graph")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force reprocessing, ignoring any cached result in Redis.",
    )
    args = parser.parse_args()
    FinalGraphFilter().execute(use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
