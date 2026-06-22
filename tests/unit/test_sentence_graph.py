"""Unit tests for sentence_graph.py (Filter 4)."""

import pytest

from src.sentence_graph import SentenceGraphFilter
from src.shared.graph.ops import deserialize_graph, serialize_graph
from src.shared.graph.validate import is_symmetric

@pytest.fixture
def mock_tree():
    """Simula a estrutura de árvore entregue pelo Filtro 2."""
    return {
        "children": [
            {
                "index": 0,
                "children": [{"value": "jogo"}, {"value": "trav"}]
            },
            {
                "index": 1,
                "children": [{"value": "fps"}, {"value": "cai"}]
            }
        ]
    }

def test_sentence_graph_is_symmetric_and_has_correct_prefixes(small_word_graph, mock_tree):
    """Ensure the sentence graph is symmetric and uses the 's_' prefix."""
    filt = SentenceGraphFilter()
    
    # Mock do formato de entrada esperado por filtros multi-input
    data = {
        "primary": serialize_graph(small_word_graph),
        "tree": mock_tree
    }
    
    result = filt.process(data)
    graph = deserialize_graph(result)
    
    assert all(n.startswith("s_") for n in graph.nodes), "Nodes must have the 's_' prefix."
    assert is_symmetric(graph), "Sentence graph matrix must be symmetric."