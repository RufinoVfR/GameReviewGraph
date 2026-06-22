"""SentenceGraphFilter — Filter 4 of the pipeline.

Constructs the sentence-level graph by projecting weights from the word graph.
Connections are based on shared related words, normalized by sentence lengths.
"""

from typing import Any, Iterator

from src.shared.filter_base import AbstractFilter
from src.shared.graph.ops import (
    build_graph_from_deltas,
    deserialize_graph,
    get_edge_weight,
    serialize_graph,
)
from src.shared.graph.validate import assert_valid
from src.shared.tree import iter_sentences, iter_words


def _sentence_pair_deltas(tree: dict[str, Any], word_graph: Any) -> Iterator[tuple[str, str, float]]:
    """Yield (sentence_u, sentence_v, normalized_weight) for connected sentences.

    Calculates the relationship intensity between two sentences by summing the
    weights of all pairs of words (one from each sentence) and dividing by the
    product of the sentence lengths: Σ weight(wi, wj) / (|sa| * |sb|).

    Args:
        tree: Deserialized N-ary tree dict containing sentence and word nodes.
        word_graph: The word-level Graph instance.

    Yields:
        Tuples of (node_key_1, node_key_2, normalized_weight).
    """
    # 1. Extrair as frases e suas respectivas palavras válidas
    sentences: list[dict[str, Any]] = []
    for sentence_node in iter_sentences(tree):
        idx = sentence_node.get("index", len(sentences))
        s_id = f"s_{idx}"
        words = [f"w_{word_node['value']}" for word_node in iter_words(sentence_node)]
        if words:
            sentences.append({"id": s_id, "words": words, "size": len(words)})

    # 2. Comparar todos os pares únicos de frases
    for i in range(len(sentences)):
        sa = sentences[i]
        for j in range(i + 1, len(sentences)):
            sb = sentences[j]

            # Somar os pesos das palavras que conectam as duas frases
            raw_sum = 0.0
            for wi in sa["words"]:
                for wj in sb["words"]:
                    weight = get_edge_weight(word_graph, wi, wj)
                    if weight is not None:
                        raw_sum += weight

            # 3. Aplicar normalização e gerar a aresta (apenas se > 0)
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