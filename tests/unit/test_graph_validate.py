"""Unit tests for src/shared/graph/validate.py."""

import pytest

from src.shared.graph.ops import add_edge, add_node, new_graph
from src.shared.graph.validate import (
    assert_valid,
    invalid_prefixes,
    is_symmetric,
    isolated_nodes,
)


class TestIsSymmetric:
    def test_true_for_symmetric_graph(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        assert is_symmetric(graph)

    def test_true_for_empty_graph(self):
        assert is_symmetric(new_graph())

    def test_false_when_matrix_is_asymmetric(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        i, j = graph.index["w_a"], graph.index["w_b"]
        graph.matrix[i][j] = 5.0
        assert not is_symmetric(graph)


class TestInvalidPrefixes:
    def test_empty_when_all_prefixes_are_valid(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "s_1")
        add_node(graph, "c_2")
        assert invalid_prefixes(graph) == []

    def test_flags_unknown_prefix(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "x_bad")
        assert invalid_prefixes(graph) == ["x_bad"]

    def test_respects_custom_allowed_set(self):
        graph = new_graph()
        add_node(graph, "z_a")
        assert invalid_prefixes(graph, allowed=("z_",)) == []


class TestIsolatedNodes:
    def test_returns_nodes_with_no_edges(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_node(graph, "w_c")
        assert isolated_nodes(graph) == ["w_c"]

    def test_empty_when_no_isolated_nodes(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        assert isolated_nodes(graph) == []


class TestAssertValid:
    def test_passes_for_valid_graph(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        assert_valid(graph)  # must not raise

    def test_raises_on_asymmetric_matrix(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        i, j = graph.index["w_a"], graph.index["w_b"]
        graph.matrix[i][j] = 5.0
        with pytest.raises(ValueError, match="not symmetric"):
            assert_valid(graph)

    def test_raises_on_invalid_prefix(self):
        graph = new_graph()
        add_node(graph, "x_bad")
        with pytest.raises(ValueError, match="invalid prefixes"):
            assert_valid(graph)

    def test_raises_on_self_loop(self):
        graph = new_graph()
        add_node(graph, "w_a")
        graph.matrix[0][0] = 1.0
        with pytest.raises(ValueError, match="self-loop"):
            assert_valid(graph)
