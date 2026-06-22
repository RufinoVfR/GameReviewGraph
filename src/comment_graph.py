"""CommentGraphFilter — Filter 5 of the pipeline.

Builds the comment graph from the sentence graph, one level above
``sentence_graph``: two comments ``c_<id>`` are linked when they own at least
one related sentence pair, weighted by the normalized sum of those sentence-pair
weights::

    weight(ca, cb) = Σ weight(si, sj) / (|ca| × |cb|)   for si ∈ ca, sj ∈ cb

where ``weight(si, sj)`` is the sentence-graph edge weight and ``|ca|`` is the
number of sentences in comment ``a``. The membership ``comment → sentences`` is
not stored in the sentence graph, so it is reconstructed from ``preprocessed``
by replaying the **same sequential walk** the ``tree`` filter used to assign the
global ``s_<index>`` counter (see ``src/tree/build.py``).

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()``. The weight formula and
its normalization are domain logic and live here, not in ``src/shared``.
"""

import argparse
from collections.abc import Iterator

from src.shared.filter_base import AbstractFilter
from src.shared.graph import (
    add_edge,
    assert_valid,
    build_graph_from_deltas,
    deserialize_graph,
    iter_edges,
    new_graph,
    serialize_graph,
)
from src.shared.tree import COMMENT_PREFIX, SENTENCE_PREFIX
from src.types import Graph, ProcessedComment


class CommentGraphFilter(AbstractFilter):
    """Build the comment graph from the sentence graph (Filter 5).

    Multi-input filter: the primary artifact is ``sentence_graph.json`` and the
    extra artifact ``preprocessed.json`` supplies the ``comment → sentences``
    membership needed to normalize each edge.
    """

    name = "comment_graph"
    input_key = "sentence_graph"
    extra_input_keys = ["preprocessed"]
    output_key = "comment_graph"

    def process(self, data: dict) -> dict:
        """Derive the comment graph from the sentence graph.

        Reconstructs which global sentences belong to each comment, accumulates
        the raw numerator ``Σ weight(si, sj)`` per comment pair, then normalizes
        each edge by ``|ca| × |cb|``. Only strictly positive results become
        edges, so two comments are linked iff they share at least one related
        sentence pair.

        Args:
            data: Multi-input payload ``{"primary": <serialized sentence
                graph>, "preprocessed": list[{"id", "sentences"}]}``.

        Returns:
            Serialized comment graph (``serialize_graph`` output) over
            ``c_<id>`` nodes — JSON-ready for ``execute()`` to write to S3.
        """
        sentence_graph = deserialize_graph(data["primary"])
        preprocessed: list[ProcessedComment] = data["preprocessed"]

        membership = _comment_membership(preprocessed)
        sizes = {comment: len(sentences) for comment, sentences in membership}

        raw = build_graph_from_deltas(_pair_deltas(sentence_graph, membership))
        graph = _normalize(raw, sizes)

        assert_valid(graph)
        return serialize_graph(graph)


def _comment_membership(
    preprocessed: list[ProcessedComment],
) -> list[tuple[str, list[str]]]:
    """Reconstruct each comment's sentence nodes in tree-numbering order.

    Walks ``preprocessed`` in the exact sequence ``tree``'s
    ``build_from_corpus`` used to assign the global sentence index, so the
    ``k``-th sentence of the walk maps to the ``s_<k>`` node in the sentence
    graph. Each comment owns a contiguous run of indices equal to its sentence
    count (a comment with no sentences owns an empty run and forms no edges).

    Args:
        preprocessed: The ``preprocessed.json`` contract — a list of
            ``{"id": int, "sentences": list[list[str]]}`` in corpus order.

    Returns:
        ``(comment_key, sentence_keys)`` pairs, where ``comment_key`` is
        ``c_<id>`` and ``sentence_keys`` are the ``s_<index>`` nodes owned by
        that comment, in order.
    """
    membership: list[tuple[str, list[str]]] = []
    sentence_index = 0
    for comment in preprocessed:
        sentence_keys = [
            f"{SENTENCE_PREFIX}{sentence_index + offset}"
            for offset in range(len(comment["sentences"]))
        ]
        sentence_index += len(comment["sentences"])
        membership.append((f"{COMMENT_PREFIX}{comment['id']}", sentence_keys))
    return membership


def _pair_deltas(
    sentence_graph: Graph,
    membership: list[tuple[str, list[str]]],
) -> Iterator[tuple[str, str, float]]:
    """Yield one delta per related sentence pair across distinct comments.

    For every unordered comment pair ``(ca, cb)``, emits a
    ``(comment_a, comment_b, weight(si, sj))`` triple for each ``si ∈ ca``,
    ``sj ∈ cb`` connected in the sentence graph; unconnected sentence pairs
    contribute nothing. Accumulating these triples (via
    ``build_graph_from_deltas``) produces the unnormalized numerator
    ``Σ weight(si, sj)`` for each comment edge. Sentence pairs within the same
    comment are never crossed, so no self-loop can arise.

    Each comment's sentences are resolved to their sentence-graph matrix row
    indices once, so the hot inner loop indexes the adjacency matrix directly
    instead of paying a ``get_edge_weight`` call (plus its redundant dict
    lookups) per sentence pair. A ``0.0`` matrix entry means no edge, so absent
    pairs are skipped exactly as before. Sentences missing from the graph
    (isolated, hence edgeless) drop out during resolution.

    Args:
        sentence_graph: The deserialized sentence graph (``s_<index>`` nodes).
        membership: ``(comment_key, sentence_keys)`` pairs from
            ``_comment_membership``.

    Yields:
        ``(comment_a, comment_b, weight)`` triples for connected sentence pairs.
    """
    matrix = sentence_graph.matrix
    index = sentence_graph.index

    # Resolve each comment's sentences to sentence-graph row indices once.
    resolved = [
        (comment, [index[key] for key in sentence_keys if key in index])
        for comment, sentence_keys in membership
    ]

    for a, (comment_a, rows_a) in enumerate(resolved):
        for comment_b, rows_b in resolved[a + 1:]:
            for si in rows_a:
                row = matrix[si]
                for sj in rows_b:
                    weight = row[sj]
                    if weight != 0.0:
                        yield (comment_a, comment_b, weight)


def _normalize(raw: Graph, sizes: dict[str, int]) -> Graph:
    """Normalize each accumulated comment edge by ``|ca| × |cb|``.

    Divides every edge of the unnormalized graph (whose weights are the raw
    sums ``Σ weight(si, sj)``) by the product of the two comments' sentence
    counts, completing ``weight(ca, cb) = Σ weight(si, sj) / (|ca| × |cb|)``.
    Only strictly positive results become edges, so no isolated node is added.

    Args:
        raw: Graph of accumulated numerators, keyed by ``c_<id>`` nodes.
        sizes: ``c_<id>`` → number of sentences in that comment (``|ca|``).

    Returns:
        A new normalized comment graph (dataclass ``Graph``).
    """
    graph = new_graph()
    for comment_a, comment_b, raw_weight in iter_edges(raw):
        normalized = raw_weight / (sizes[comment_a] * sizes[comment_b])
        if normalized > 0.0:
            add_edge(graph, comment_a, comment_b, normalized)
    return graph


def main() -> None:
    """Parse CLI flags and run the comment graph filter."""
    parser = argparse.ArgumentParser(prog="python -m src.comment_graph")
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force reprocessing, ignoring any cached result in Redis.",
    )
    args = parser.parse_args()
    CommentGraphFilter().execute(use_cache=not args.no_cache)


if __name__ == "__main__":
    main()
