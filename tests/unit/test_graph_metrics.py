"""Unit tests for src/shared/graph/metrics.py."""

from src.shared.graph.metrics import (
    average_edge_weight,
    density,
    edge_count,
    neighbor_count,
    node_count,
    total_edge_weight,
)
from src.shared.graph.ops import add_edge, add_node, new_graph


class TestNeighborCount:
    def test_counts_non_zero_neighbours(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 2.0)
        assert neighbor_count(graph, "w_a") == 2
        assert neighbor_count(graph, "w_b") == 1

    def test_zero_for_isolated_node(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert neighbor_count(graph, "w_a") == 0


class TestTotalEdgeWeight:
    def test_sums_incident_weights(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_a", "w_c", 2.5)
        assert total_edge_weight(graph, "w_a") == 3.5

    def test_zero_for_isolated_node(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert total_edge_weight(graph, "w_a") == 0.0


class TestNodeCount:
    def test_counts_nodes(self):
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        assert node_count(graph) == 2

    def test_zero_for_empty_graph(self):
        assert node_count(new_graph()) == 0


class TestEdgeCount:
    def test_counts_unique_edges(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_b", "w_c", 2.0)
        assert edge_count(graph) == 2

    def test_zero_for_edgeless_graph(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert edge_count(graph) == 0


class TestDensity:
    def test_complete_triangle_has_density_one(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_b", "w_c", 1.0)
        add_edge(graph, "w_a", "w_c", 1.0)
        assert density(graph) == 1.0

    def test_partial_graph(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_node(graph, "w_c")
        assert density(graph) == 1 / 3  # 1 edge out of 3 possible pairs

    def test_zero_for_fewer_than_two_nodes(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert density(graph) == 0.0
        assert density(new_graph()) == 0.0


class TestAverageEdgeWeight:
    def test_averages_unique_edge_weights(self):
        graph = new_graph()
        add_edge(graph, "w_a", "w_b", 1.0)
        add_edge(graph, "w_b", "w_c", 3.0)
        assert average_edge_weight(graph) == 2.0

    def test_zero_for_empty_graph(self):
        assert average_edge_weight(new_graph()) == 0.0
