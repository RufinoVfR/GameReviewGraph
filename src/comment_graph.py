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

from src.shared.filter_base import AbstractFilter
from src.shared.tree import COMMENT_PREFIX, SENTENCE_PREFIX
from src.types import ProcessedComment


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

        Args:
            data: Multi-input payload ``{"primary": <serialized sentence
                graph>, "preprocessed": list[{"id", "sentences"}]}``.

        Returns:
            Serialized comment graph (``serialize_graph`` output) over
            ``c_<id>`` nodes — JSON-ready for ``execute()`` to write to S3.
        """
        _comment_membership(data["preprocessed"])
        raise NotImplementedError("edge weight aggregation not implemented yet")


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
