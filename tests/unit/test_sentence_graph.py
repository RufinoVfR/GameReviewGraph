"""Unit tests for sentence_graph.py (Filter 4)."""

import pytest

from src.sentence_graph import SentenceGraphFilter
from src.shared.graph.ops import deserialize_graph
from src.shared.graph.validate import is_symmetric


def test_sentence_graph_is_symmetric_and_has_correct_prefixes(small_word_graph, tree_fixture):
    """Ensure the sentence graph is symmetric and uses the 's_' prefix."""
    filt = SentenceGraphFilter()
    
    # Mock do formato de entrada esperado por filtros multi-input
    data = {
        "primary": small_word_graph,
        "tree": tree_fixture
    }
    
    result = filt.process(data)
    graph = deserialize_graph(result)
    
    assert all(n.startswith("s_") for n in graph.nodes), "Nodes must have the 's_' prefix."
    assert is_symmetric(graph), "Sentence graph matrix must be symmetric."