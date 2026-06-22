"""SentenceGraphFilter — Filter 4 of the pipeline.

Constructs the sentence-level graph by projecting weights from the word graph.
Connections are based on shared related words, normalized by sentence lengths.
"""

from typing import Any, Iterator

from src.shared.filter_base import AbstractFilter
from src.shared.graph import (
    assert_valid,
    build_graph_from_deltas,
    deserialize_graph,
    serialize_graph,
)
from src.shared.tree import iter_sentences, iter_words
from src.types import Graph


def _sentence_pair_deltas(tree: dict[str, Any], word_graph: Graph) -> Iterator[tuple[str, str, float]]:
    """Yield (sentence_u, sentence_v, normalized_weight) for connected sentences.

    Calculates the relationship intensity between two sentences by summing the
    weights of all pairs of words (one from each sentence) and dividing by the
    product of the sentence lengths: Σ weight(wi, wj) / (|sa| * |sb|).

    Each sentence's words are resolved to their word-graph matrix row indices
    once, so the hot inner loop indexes the adjacency matrix directly instead of
    paying a ``get_edge_weight`` call (plus its redundant dict lookups) per word
    pair. A missing word weighs ``0.0``, so absent entries simply add nothing.

    Args:
        tree: Deserialized N-ary tree dict containing sentence and word nodes.
        word_graph: The word-level Graph instance.

    Yields:
        Tuples of (node_key_1, node_key_2, normalized_weight).
    """
    matrix = word_graph.matrix
    index = word_graph.index

    # Resolve each sentence's words to word-graph row indices once. ``size`` is
    # the full token count (the |sa| denominator); words absent from the graph
    # (isolated, hence edgeless) are dropped from the sum but still counted.
    sentences: list[dict[str, Any]] = []
    for sentence_node in iter_sentences(tree):
        keys = [f"w_{word_node['value']}" for word_node in iter_words(sentence_node)]
        if not keys:
            continue
        rows = [index[key] for key in keys if key in index]
        sentences.append(
            {"id": f"s_{sentence_node['index']}", "rows": rows, "size": len(keys)}
        )

    # Compare every unique pair of sentences.
    for i in range(len(sentences)):
        sa = sentences[i]
        rows_a = sa["rows"]
        for j in range(i + 1, len(sentences)):
            sb = sentences[j]
            rows_b = sb["rows"]

            # Sum the weights of the word pairs connecting the two sentences,
            # reading the matrix directly (0.0 entries contribute nothing).
            raw_sum = 0.0
            for row_index in rows_a:
                row = matrix[row_index]
                raw_sum += sum(row[col_index] for col_index in rows_b)

            # Normalize and emit the edge only when the pair is actually related.
            if raw_sum > 0.0:
                normalized_weight = raw_sum / (sa["size"] * sb["size"])
                yield (sa["id"], sb["id"], normalized_weight)


class SentenceGraphFilter(AbstractFilter):
    """Builds the sentence graph using the word graph and the syntax tree.

    Reads ``word_graph.json`` as primary input and ``tree.json`` as extra input.
    Writes the resulting ``sentence_graph.json``.
    """

    name = "sentence_graph"
    input_key = "word_graph"
    output_key = "sentence_graph"
    extra_input_keys = ["tree"]

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process the inputs to build the sentence-level relationships.

        Args:
            data: A dictionary containing "primary" (serialized word graph) 
                and "tree" (parsed syntax tree).

        Returns:
            A serialized dictionary representation of the new sentence graph.
        """
        word_graph = deserialize_graph(data["primary"])
        tree = data["tree"]

        deltas = _sentence_pair_deltas(tree, word_graph)
        sentence_graph = build_graph_from_deltas(deltas)

        assert_valid(sentence_graph)
        return serialize_graph(sentence_graph)
