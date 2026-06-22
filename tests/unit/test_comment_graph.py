"""Unit tests for comment_graph.py (Filter 5)."""

import pytest

from src.comment_graph import _comment_membership


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
