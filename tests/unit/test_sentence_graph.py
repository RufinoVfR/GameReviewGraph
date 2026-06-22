"""Unit tests for sentence_graph.py (Filter 4)."""

import pytest

from src.sentence_graph import SentenceGraphFilter
from src.shared.graph.ops import deserialize_graph, serialize_graph
from src.shared.graph.validate import is_symmetric


@pytest.fixture
def mock_tree():
    """Simulate the tree.json structure produced by Filter 2 (dataset -> comment -> sentence -> word)."""
    return {
        "children": [
            {
                "id": 1,
                "children": [
                    {
                        "index": 0,
                        "children": [{"value": "jogo"}, {"value": "trav"}],
                    },
                    {
                        "index": 1,
                        "children": [{"value": "fps"}, {"value": "cai"}],
                    },
                ],
            }
        ]
    }


def test_sentence_graph_is_symmetric_and_has_correct_prefixes(small_word_graph, mock_tree):
    """Ensure the sentence graph is symmetric and uses the 's_' prefix."""
    filt = SentenceGraphFilter()

    # Expected input shape for multi-input filters.
    data = {
        "primary": serialize_graph(small_word_graph),
        "tree": mock_tree,
    }

    result = filt.process(data)
    graph = deserialize_graph(result)

    assert all(n.startswith("s_") for n in graph.nodes), "Nodes must have the 's_' prefix."
    assert is_symmetric(graph), "Sentence graph matrix must be symmetric."


def test_sentence_graph_weight_matches_hand_calculated_normalization(small_word_graph, mock_tree):
    """Verify the normalized weight Σ weight(wi, wj) / (|sa| * |sb|) against a hand-computed value.

    `small_word_graph` only has edges between "jogo"/"trav" and "fps"/"cai" within
    each cluster, with no edges across clusters, so s_0 and s_1 (one sentence per
    cluster) must come out with zero connection. Adding a single cross-cluster edge
    w_jogo<->w_fps = 2.0 makes the two sentences related, with raw_sum = 2.0 over
    sizes |s_0| = |s_1| = 2, so the expected normalized weight is 2.0 / (2 * 2) = 0.5.
    """
    from src.shared.graph.ops import add_edge

    add_edge(small_word_graph, "w_jogo", "w_fps", 2.0)

    filt = SentenceGraphFilter()
    data = {
        "primary": serialize_graph(small_word_graph),
        "tree": mock_tree,
    }

    result = filt.process(data)
    graph = deserialize_graph(result)

    i, j = graph.index["s_0"], graph.index["s_1"]
    assert graph.matrix[i][j] == pytest.approx(0.5)
    assert graph.matrix[j][i] == pytest.approx(0.5)
