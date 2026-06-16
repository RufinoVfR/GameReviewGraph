"""Unit tests for src/shared/graph/traversal.py."""

from src.shared.graph.ops import add_edge, add_node, iter_edges, new_graph
from src.shared.graph.traversal import (
    bfs,
    connected_components,
    count_components,
    dfs,
    is_connected,
    minimum_spanning_tree,
    reachable,
)


class TestBfs:
    def test_visits_all_reachable_nodes(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 1.0)
        add_edge(graph, "w_b", "w_d", 1.0)
        order = bfs(graph, "w_a")
        assert order[0] == "w_a"
        assert set(order) == {"w_a", "w_b", "w_c", "w_d"}

    def test_breadth_first_order(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 1.0)
        add_edge(graph, "w_b", "w_d", 1.0)
        order = bfs(graph, "w_a")
        # w_b and w_c (distance 1) must come before w_d (distance 2)
        assert order.index("w_d") > order.index("w_b")
        assert order.index("w_d") > order.index("w_c")

    def test_does_not_cross_components(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_x", "w_y", 1.0)
        assert set(bfs(graph, "w_a")) == {"w_a", "w_b"}

    def test_isolated_node_returns_itself(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert bfs(graph, "w_a") == ["w_a"]

    def test_unknown_start_returns_empty(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        assert bfs(graph, "w_never_added") == []


class TestDfs:
    def test_visits_all_reachable_nodes(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 1.0)
        add_edge(graph, "w_b", "w_d", 1.0)
        order = dfs(graph, "w_a")
        assert order[0] == "w_a"
        assert set(order) == {"w_a", "w_b", "w_c", "w_d"}

    def test_matches_recursive_dfs_order(self):
        # w_a's neighbors in insertion order: w_b, w_c.
        # True recursive DFS from w_a: a -> b -> d (b's only other neighbor) -> backtrack -> c.
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 1.0)
        add_edge(graph, "w_b", "w_d", 1.0)
        assert dfs(graph, "w_a") == ["w_a", "w_b", "w_d", "w_c"]

    def test_does_not_cross_components(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_x", "w_y", 1.0)
        assert set(dfs(graph, "w_a")) == {"w_a", "w_b"}

    def test_unknown_start_returns_empty(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        assert dfs(graph, "w_never_added") == []


class TestReachable:
    def test_returns_set_including_start(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        assert reachable(graph, "w_a") == {"w_a", "w_b"}

    def test_excludes_other_components(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_x", "w_y", 1.0)
        assert "w_x" not in reachable(graph, "w_a")


class TestConnectedComponents:
    def test_single_component(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_b", "w_c", 1.0)
        assert connected_components(graph) == [["w_a", "w_b", "w_c"]]

    def test_multiple_components(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_x", "w_y", 1.0)
        components = connected_components(graph)
        assert len(components) == 2
        assert {"w_a", "w_b"} in (set(c) for c in components)
        assert {"w_x", "w_y"} in (set(c) for c in components)

    def test_isolated_nodes_are_singleton_components(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        components = connected_components(graph)
        assert sorted(map(sorted, components)) == [["w_a"], ["w_b"]]

    def test_empty_graph(self):
        assert connected_components(new_graph()) == []


class TestCountComponents:
    def test_counts_components(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_x", "w_y", 1.0)
        add_node(graph, "w_z")
        assert count_components(graph) == 3

    def test_empty_graph_has_zero_components(self):
        assert count_components(new_graph()) == 0


class TestIsConnected:
    def test_true_for_single_component(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_b", "w_c", 1.0)
        assert is_connected(graph)

    def test_false_for_multiple_components(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_x", "w_y", 1.0)
        assert not is_connected(graph)

    def test_true_for_empty_graph(self):
        assert is_connected(new_graph())


class TestMinimumSpanningTree:
    def test_has_n_minus_one_edges(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 2.0)
        add_edge(graph, "w_b", "w_c", 0.5)
        mst = minimum_spanning_tree(graph)
        assert len(mst.nodes) == 3
        assert len(list(iter_edges(mst))) == 2

    def test_picks_minimum_total_weight(self):
        # Triangle: a-b=1.0, b-c=1.0, a-c=5.0 -> MST must skip the a-c edge,
        # total weight = 2.0 (not 5.0+ from any tree that includes a-c twice).
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_b", "w_c", 1.0)
        add_edge(graph, "w_a", "w_c", 5.0)
        mst = minimum_spanning_tree(graph)
        total_weight = sum(w for _, _, w in iter_edges(mst))
        assert total_weight == 2.0

    def test_result_is_connected(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 2.0)
        add_edge(graph, "w_a", "w_d", 3.0)
        add_edge(graph, "w_b", "w_c", 1.5)
        mst = minimum_spanning_tree(graph)
        assert is_connected(mst)

    def test_does_not_mutate_original_graph(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 2.0)
        add_edge(graph, "w_b", "w_c", 0.5)
        original_edges = set(iter_edges(graph))
        minimum_spanning_tree(graph)
        assert set(iter_edges(graph)) == original_edges

    def test_only_reaches_nodes_in_start_component(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_x", "w_y", 1.0)
        mst = minimum_spanning_tree(graph)
        assert set(mst.nodes) == {"w_a", "w_b"}

    def test_empty_graph(self):
        mst = minimum_spanning_tree(new_graph())
        assert mst.nodes == []

    def test_single_node_graph(self):
        graph = new_graph()
        add_node(graph, "w_a")
        mst = minimum_spanning_tree(graph)
        assert mst.nodes == ["w_a"]
        assert list(iter_edges(mst)) == []
