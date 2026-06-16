"""Unit tests for src/shared/graph/ops.py."""

from src.shared.graph.ops import (
    add_edge,
    add_node,
    copy_graph,
    get_edge_weight,
    has_edge,
    increase_edge,
    iter_edges,
    new_graph,
    remove_edge,
)


class TestNewGraph:
    def test_returns_empty_graph(self):
        graph = new_graph()
        assert graph.nodes == []
        assert graph.index == {}
        assert graph.matrix == []


class TestAddNode:
    def test_first_node_gets_index_zero(self):
        graph = new_graph()
        assert add_node(graph, "w_a") == 0
        assert graph.nodes == ["w_a"]
        assert graph.index == {"w_a": 0}
        assert graph.matrix == [[0.0]]

    def test_second_node_grows_matrix_symmetrically(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        assert graph.nodes == ["w_a", "w_b"]
        assert graph.matrix == [[0.0, 0.0], [0.0, 0.0]]

    def test_existing_node_is_idempotent(self):
        graph = new_graph()
        first_index = add_node(graph, "w_a")
        add_node(graph, "w_b")
        second_index = add_node(graph, "w_a")
        assert first_index == second_index == 0
        assert graph.nodes == ["w_a", "w_b"]
        assert len(graph.matrix) == 2


class TestAddEdge:
    def test_creates_nodes_and_sets_symmetric_weight(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.5)
        i, j = graph.index["w_a"], graph.index["w_b"]
        assert graph.matrix[i][j] == 1.5
        assert graph.matrix[j][i] == 1.5

    def test_overwrites_existing_weight(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_b", 5.0)
        assert get_edge_weight(graph, "w_a", "w_b") == 5.0


class TestIncreaseEdge:
    def test_creates_edge_when_absent(self):
        graph = new_graph()
        increase_edge(graph, "w_a", "w_b", 0.5)
        assert get_edge_weight(graph, "w_a", "w_b") == 0.5

    def test_accumulates_delta_across_calls(self):
        graph = new_graph()
        increase_edge(graph, "w_a", "w_b", 0.5)
        increase_edge(graph, "w_a", "w_b", 0.25)
        increase_edge(graph, "w_b", "w_a", 0.25)
        assert get_edge_weight(graph, "w_a", "w_b") == 1.0

    def test_stays_symmetric(self):
        graph = new_graph()
        increase_edge(graph, "w_a", "w_b", 1.0)
        i, j = graph.index["w_a"], graph.index["w_b"]
        assert graph.matrix[i][j] == graph.matrix[j][i]


class TestHasEdge:
    def test_true_when_edge_exists(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        assert has_edge(graph, "w_a", "w_b")
        assert has_edge(graph, "w_b", "w_a")

    def test_false_when_nodes_exist_but_no_edge(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        assert not has_edge(graph, "w_a", "w_b")

    def test_false_when_node_missing(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert not has_edge(graph, "w_a", "w_never_added")


class TestRemoveEdge:
    def test_removes_edge_in_both_directions(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        remove_edge(graph, "w_a", "w_b")
        assert not has_edge(graph, "w_a", "w_b")
        i, j = graph.index["w_a"], graph.index["w_b"]
        assert graph.matrix[i][j] == 0.0
        assert graph.matrix[j][i] == 0.0

    def test_does_not_remove_the_nodes(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        remove_edge(graph, "w_a", "w_b")
        assert "w_a" in graph.index
        assert "w_b" in graph.index

    def test_noop_when_edge_absent(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        remove_edge(graph, "w_a", "w_b")  # must not raise
        assert not has_edge(graph, "w_a", "w_b")

    def test_noop_when_node_absent(self):
        graph = new_graph()
        add_node(graph, "w_a")
        remove_edge(graph, "w_a", "w_never_added")  # must not raise


class TestGetEdgeWeight:
    def test_returns_weight_when_edge_exists(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 2.5)
        assert get_edge_weight(graph, "w_a", "w_b") == 2.5

    def test_returns_none_when_edge_absent(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        assert get_edge_weight(graph, "w_a", "w_b") is None

    def test_returns_none_when_node_absent(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert get_edge_weight(graph, "w_a", "w_never_added") is None


class TestIterEdges:
    def test_yields_each_edge_exactly_once(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_b", "w_c", 2.0)
        edges = list(iter_edges(graph))
        assert len(edges) == 2
        pairs = {frozenset((u, v)) for u, v, _ in edges}
        assert pairs == {frozenset(("w_a", "w_b")), frozenset(("w_b", "w_c"))}

    def test_skips_zero_weight_cells(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        assert list(iter_edges(graph)) == []

    def test_empty_graph_yields_nothing(self):
        assert list(iter_edges(new_graph())) == []


class TestCopyGraph:
    def test_copy_has_equal_contents(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        copy = copy_graph(graph)
        assert copy.nodes == graph.nodes
        assert copy.index == graph.index
        assert copy.matrix == graph.matrix

    def test_mutating_copy_does_not_affect_original(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        copy = copy_graph(graph)

        remove_edge(copy, "w_a", "w_b")
        add_node(copy, "w_c")

        assert has_edge(graph, "w_a", "w_b")
        assert "w_c" not in graph.index

    def test_mutating_original_does_not_affect_copy(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        copy = copy_graph(graph)

        remove_edge(graph, "w_a", "w_b")

        assert has_edge(copy, "w_a", "w_b")
