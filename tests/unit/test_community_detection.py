"""Unit tests for community_detection.py (Filter 7)."""

import pytest

from src.community_detection import CommunityDetectionFilter
from src.shared.graph import add_edge, serialize_graph
from src.types import Graph


# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty_graph() -> Graph:
    return Graph(nodes=[], index={}, matrix=[])


def _caterpillar_tree() -> Graph:
    """Build a 6-node tree: spine w_a–w_b–w_c with leaves s_1, s_2, s_3.

    Topology (weights on spine are low so they are cut first):
        s_1 - w_a - w_b - w_c - s_3
                     |
                    s_2

    Cutting w_a–w_b and w_b–w_c splits the tree into 3 components
    (degree guard passes: all spine nodes have degree ≥ 2).
    """
    g = _empty_graph()
    for n in ("w_a", "w_b", "w_c", "s_1", "s_2", "s_3"):
        g.nodes.append(n)
        g.index[n] = len(g.nodes) - 1
        for row in g.matrix:
            row.append(0.0)
        g.matrix.append([0.0] * len(g.nodes))

    add_edge(g, "w_a", "w_b", 0.1)   # spine — lightest, cut first
    add_edge(g, "w_b", "w_c", 0.2)   # spine — second lightest
    add_edge(g, "w_a", "s_1", 5.0)   # hierarchical — heavy, not cut
    add_edge(g, "w_b", "s_2", 5.0)   # hierarchical — heavy, not cut
    add_edge(g, "w_c", "s_3", 5.0)   # hierarchical — heavy, not cut
    return g


# ── TestFilterContract ────────────────────────────────────────────────────────

class TestFilterContract:
    def test_declared_name(self):
        assert CommunityDetectionFilter.name == "community_detection"

    def test_declared_input_key(self):
        assert CommunityDetectionFilter.input_key == "final_graph"

    def test_declared_output_key(self):
        assert CommunityDetectionFilter.output_key == "communities"

    def test_no_extra_input_keys(self):
        assert not getattr(CommunityDetectionFilter, "extra_input_keys", [])

# ── TestProcess e Integração ──────────────────────────────────────────────────

class TestProcess:
    def _small_graph_data(self) -> dict:
        g = _caterpillar_tree()
        return serialize_graph(g)

    def test_returns_dict(self):
        data = self._small_graph_data()
        result = CommunityDetectionFilter().process(data)
        assert isinstance(result, dict)

    def test_keys_are_strings(self):
        data = self._small_graph_data()
        result = CommunityDetectionFilter().process(data)
        assert all(isinstance(k, str) for k in result)

    def test_values_are_lists_of_strings(self):
        data = self._small_graph_data()
        result = CommunityDetectionFilter().process(data)
        for nodes in result.values():
            assert isinstance(nodes, list)
            assert all(isinstance(n, str) for n in nodes)

    def test_all_nodes_covered(self):
        g = _caterpillar_tree()
        data = serialize_graph(g)
        result = CommunityDetectionFilter().process(data)
        all_assigned = {n for nodes in result.values() for n in nodes}
        assert all_assigned == set(g.nodes)

    def test_communities_are_disjoint(self):
        data = self._small_graph_data()
        result = CommunityDetectionFilter().process(data)
        all_nodes: list[str] = [n for nodes in result.values() for n in nodes]
        assert len(all_nodes) == len(set(all_nodes))

    # Testes usando a fixture clustered_graph
    def test_community_detection_filter_splits_clusters(self, clustered_graph):
        """Test community detection using a graph with two dense clusters and a weak bridge."""
        filt = CommunityDetectionFilter()
        data_dict = serialize_graph(clustered_graph)
        result = filt.process(data_dict)
        assert len(result) == 2

    def test_community_detection_filter_preserves_nodes(self, clustered_graph):
        """Ensure no nodes from the original graph were lost during partitioning."""
        filt = CommunityDetectionFilter()
        data_dict = serialize_graph(clustered_graph)
        result = filt.process(data_dict)
        all_nodes_in_result = [node for nodes in result.values() for node in nodes]
        assert len(all_nodes_in_result) == len(clustered_graph.nodes)
        assert set(all_nodes_in_result) == set(clustered_graph.nodes)