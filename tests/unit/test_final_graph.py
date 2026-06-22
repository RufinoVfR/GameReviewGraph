"""Unit tests for final_graph.py (Filter 6)."""

import pytest

from src.final_graph import FinalGraphFilter
from src.shared.graph import (
    add_edge,
    deserialize_graph,
    get_edge_weight,
    invalid_prefixes,
    is_symmetric,
    new_graph,
    serialize_graph,
)


@pytest.fixture
def word_graph() -> dict:
    """Serialized word graph: a single relational edge ``w_jogo–w_trava``."""
    graph = new_graph()
    add_edge(graph, "w_jogo", "w_trava", 0.7)
    return serialize_graph(graph)


@pytest.fixture
def sentence_graph() -> dict:
    """Serialized sentence graph: one relational edge ``s_0–s_1``."""
    graph = new_graph()
    add_edge(graph, "s_0", "s_1", 0.5)
    return serialize_graph(graph)


@pytest.fixture
def comment_graph() -> dict:
    """Serialized comment graph: one relational edge ``c_1–c_2``."""
    graph = new_graph()
    add_edge(graph, "c_1", "c_2", 0.3)
    return serialize_graph(graph)


@pytest.fixture
def tree() -> dict:
    """Tiny ``tree.json`` dict spanning the three fixture comments.

    ``c_1`` owns two sentences (``s_0`` with words ``jogo``/``trava``, ``s_1``
    with one word ``fps``); ``c_2`` owns one sentence (``s_2`` with two words).
    So ``|c_1| = 2`` sentences, ``|s_0| = 2`` words, ``|s_1| = 1`` word.
    """
    return {
        "type": "dataset",
        "children": [
            {
                "type": "comment",
                "id": 1,
                "children": [
                    {
                        "type": "sentence",
                        "index": 0,
                        "children": [
                            {"type": "word", "value": "jogo", "position": 0},
                            {"type": "word", "value": "trava", "position": 1},
                        ],
                    },
                    {
                        "type": "sentence",
                        "index": 1,
                        "children": [
                            {"type": "word", "value": "fps", "position": 0},
                        ],
                    },
                ],
            },
            {
                "type": "comment",
                "id": 2,
                "children": [
                    {
                        "type": "sentence",
                        "index": 2,
                        "children": [
                            {"type": "word", "value": "historia", "position": 0},
                            {"type": "word", "value": "boa", "position": 1},
                        ],
                    },
                ],
            },
        ],
    }


def _run(word_graph, sentence_graph, comment_graph, tree):
    """Run the filter and return the deserialized final graph."""
    result = FinalGraphFilter().process(
        {
            "primary": comment_graph,
            "word_graph": word_graph,
            "sentence_graph": sentence_graph,
            "tree": tree,
        }
    )
    return deserialize_graph(result)


class TestFilterContract:
    def test_declared_keys(self):
        """The filter declares the multi-input keys US08/US09 require."""
        assert FinalGraphFilter.name == "final_graph"
        assert FinalGraphFilter.input_key == "comment_graph"
        assert FinalGraphFilter.extra_input_keys == [
            "word_graph",
            "sentence_graph",
            "tree",
        ]
        assert FinalGraphFilter.output_key == "final_graph"


class TestFinalGraph:
    def test_all_three_prefixes_present(
        self, word_graph, sentence_graph, comment_graph, tree
    ):
        """The unified graph carries ``w_``/``s_``/``c_`` nodes with valid prefixes."""
        graph = _run(word_graph, sentence_graph, comment_graph, tree)
        assert invalid_prefixes(graph) == []
        assert any(n.startswith("w_") for n in graph.nodes)
        assert any(n.startswith("s_") for n in graph.nodes)
        assert any(n.startswith("c_") for n in graph.nodes)

    def test_relational_edges_survive_merge(
        self, word_graph, sentence_graph, comment_graph, tree
    ):
        """Every relational edge keeps its original weight after the merge."""
        graph = _run(word_graph, sentence_graph, comment_graph, tree)
        assert get_edge_weight(graph, "w_jogo", "w_trava") == pytest.approx(0.7)
        assert get_edge_weight(graph, "s_0", "s_1") == pytest.approx(0.5)
        assert get_edge_weight(graph, "c_1", "c_2") == pytest.approx(0.3)

    def test_word_sentence_edge_weight_is_membership(
        self, word_graph, sentence_graph, comment_graph, tree
    ):
        """``Word→Sentence`` weighs ``1 / |words in the sentence|``."""
        graph = _run(word_graph, sentence_graph, comment_graph, tree)
        # s_0 has two words → 0.5; s_1 has one word → 1.0.
        assert get_edge_weight(graph, "w_jogo", "s_0") == pytest.approx(0.5)
        assert get_edge_weight(graph, "w_trava", "s_0") == pytest.approx(0.5)
        assert get_edge_weight(graph, "w_fps", "s_1") == pytest.approx(1.0)

    def test_sentence_comment_edge_weight_is_membership(
        self, word_graph, sentence_graph, comment_graph, tree
    ):
        """``Sentence→Comment`` weighs ``1 / |sentences in the comment|``."""
        graph = _run(word_graph, sentence_graph, comment_graph, tree)
        # c_1 owns two sentences → 0.5; c_2 owns one → 1.0.
        assert get_edge_weight(graph, "s_0", "c_1") == pytest.approx(0.5)
        assert get_edge_weight(graph, "s_1", "c_1") == pytest.approx(0.5)
        assert get_edge_weight(graph, "s_2", "c_2") == pytest.approx(1.0)

    def test_is_symmetric(self, word_graph, sentence_graph, comment_graph, tree):
        """The unified graph stays undirected (symmetric matrix)."""
        graph = _run(word_graph, sentence_graph, comment_graph, tree)
        assert is_symmetric(graph)

    def test_relational_and_hierarchical_edges_coexist(
        self, word_graph, sentence_graph, comment_graph, tree
    ):
        """A relational ``s_0–s_1`` edge and a hierarchical ``s_0–c_1`` edge both stand."""
        graph = _run(word_graph, sentence_graph, comment_graph, tree)
        assert get_edge_weight(graph, "s_0", "s_1") == pytest.approx(0.5)
        assert get_edge_weight(graph, "s_0", "c_1") == pytest.approx(0.5)

    def test_no_zero_weight_edges(
        self, word_graph, sentence_graph, comment_graph, tree
    ):
        """No surviving edge weighs ``0.0`` — that value is the no-edge sentinel."""
        graph = _run(word_graph, sentence_graph, comment_graph, tree)
        for i in range(len(graph.nodes)):
            for j in range(i + 1, len(graph.nodes)):
                assert graph.matrix[i][j] >= 0.0
