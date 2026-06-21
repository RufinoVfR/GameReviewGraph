"""Unit tests for src/shared/tree.py (tree.json readers)."""

import pytest

from src.shared.tree import (
    hierarchical_edges,
    iter_comments,
    iter_sentences,
    iter_words,
)


@pytest.fixture
def tree_dict() -> dict:
    """A small serialized tree with two comments, one of them empty."""
    return {
        "type": "dataset",
        "children": [
            {
                "type": "comment",
                "id": 3,
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
            {"type": "comment", "id": 7, "children": []},
        ],
    }


class TestIterators:
    def test_iter_comments(self, tree_dict):
        """Yields every comment node, including the empty one."""
        assert [c["id"] for c in iter_comments(tree_dict)] == [3, 7]

    def test_iter_sentences_spans_comments_and_skips_empty(self, tree_dict):
        """Yields every sentence across comments; empty comment contributes none."""
        assert [s["index"] for s in iter_sentences(tree_dict)] == [0, 1]

    def test_iter_words(self, tree_dict):
        """Yields the word leaves of a sentence with value and position."""
        first_sentence = next(iter_sentences(tree_dict))
        words = list(iter_words(first_sentence))
        assert [(w["value"], w["position"]) for w in words] == [
            ("jogo", 0),
            ("trava", 1),
        ]

    def test_iterators_tolerate_missing_children(self):
        """Readers do not crash on nodes without a children key."""
        assert list(iter_comments({"type": "dataset"})) == []
        assert list(iter_words({"type": "sentence"})) == []


class TestHierarchicalEdges:
    def test_word_sentence_and_sentence_comment_edges(self, tree_dict):
        """Produces (w_,s_) and (s_,c_) edges in document order."""
        assert hierarchical_edges(tree_dict) == [
            ("s_0", "c_3"),
            ("w_jogo", "s_0"),
            ("w_trava", "s_0"),
            ("s_1", "c_3"),
            ("w_fps", "s_1"),
        ]

    def test_empty_comment_contributes_no_edges(self):
        """A comment with no sentences yields no hierarchical edges."""
        tree = {"type": "dataset", "children": [{"type": "comment", "id": 9, "children": []}]}
        assert hierarchical_edges(tree) == []
