"""Unit tests for comment_graph.py (Filter 5)."""

import pytest

from src.comment_graph import CommentGraphFilter, _comment_membership
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
def preprocessed() -> list[dict]:
    """Processed comments whose sentence counts drive the global ``s_<index>`` walk.

    Only the sentence *count* per comment matters for membership (the tokens are
    irrelevant here). Membership therefore is:
    ``c_1 → s_0, s_1`` (2 sentences), ``c_2 → s_2``, ``c_3 → s_3`` (isolated).
    """
    return [
        {"id": 1, "sentences": [["jogo", "trava"], ["fps", "caiu"]]},
        {"id": 2, "sentences": [["historia", "boa"]]},
        {"id": 3, "sentences": [["suporte", "lento"]]},
    ]


@pytest.fixture
def sentence_graph() -> dict:
    """Serialized sentence graph for the three-comment fixture.

    Edges: ``s_0–s_1`` lives inside ``c_1`` (must never cross into a comment
    edge); ``s_0–s_2`` and ``s_1–s_2`` bridge ``c_1`` to ``c_2``; ``s_3``
    (``c_3``) has no edge at all.
    """
    graph = new_graph()
    add_edge(graph, "s_0", "s_1", 0.9)  # within c_1 — never crossed
    add_edge(graph, "s_0", "s_2", 0.6)
    add_edge(graph, "s_1", "s_2", 0.4)
    return serialize_graph(graph)


def _run(sentence_graph: dict, preprocessed: list[dict]):
    """Run the filter and return the deserialized comment graph."""
    result = CommentGraphFilter().process(
        {"primary": sentence_graph, "preprocessed": preprocessed}
    )
    return deserialize_graph(result)


class TestCommentMembership:
    def test_sentence_indices_follow_global_tree_order(self, preprocessed):
        """Membership numbers sentences globally and contiguously per comment."""
        assert _comment_membership(preprocessed) == [
            ("c_1", ["s_0", "s_1"]),
            ("c_2", ["s_2"]),
            ("c_3", ["s_3"]),
        ]

    def test_empty_comment_owns_no_sentences(self):
        """A comment with no sentences keeps its slot but owns an empty run."""
        membership = _comment_membership(
            [
                {"id": 1, "sentences": [["a", "b"]]},
                {"id": 2, "sentences": []},
                {"id": 3, "sentences": [["c", "d"]]},
            ]
        )
        # The empty comment consumes no global index: c_3 still starts at s_1.
        assert membership == [("c_1", ["s_0"]), ("c_2", []), ("c_3", ["s_1"])]


class TestCommentGraph:
    def test_normalized_weight_between_two_comments(self, sentence_graph, preprocessed):
        """weight(c_1, c_2) = (w(s_0,s_2) + w(s_1,s_2)) / (|c_1|·|c_2|) = (0.6+0.4)/(2·1)."""
        graph = _run(sentence_graph, preprocessed)
        assert get_edge_weight(graph, "c_1", "c_2") == pytest.approx(0.5)

    def test_edge_is_symmetric(self, sentence_graph, preprocessed):
        """The comment graph is undirected: weight(c_1, c_2) == weight(c_2, c_1)."""
        graph = _run(sentence_graph, preprocessed)
        assert is_symmetric(graph)
        assert get_edge_weight(graph, "c_1", "c_2") == get_edge_weight(graph, "c_2", "c_1")

    def test_nodes_use_comment_prefix(self, sentence_graph, preprocessed):
        """Every surviving node is a ``c_<id>`` comment node."""
        graph = _run(sentence_graph, preprocessed)
        assert invalid_prefixes(graph) == []
        assert graph.nodes  # not empty
        assert all(node.startswith("c_") for node in graph.nodes)

    def test_unrelated_comment_has_no_node(self, sentence_graph, preprocessed):
        """c_3's only sentence (s_3) has no sentence-graph edge → no c_3 node."""
        graph = _run(sentence_graph, preprocessed)
        assert "c_3" not in graph.index

    def test_within_comment_pair_creates_no_self_loop(self, sentence_graph, preprocessed):
        """The s_0–s_1 edge lives inside c_1 and must not weight a c_1 self-edge."""
        graph = _run(sentence_graph, preprocessed)
        assert get_edge_weight(graph, "c_1", "c_1") is None
