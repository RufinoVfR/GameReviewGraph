"""Unit tests for community_detection.py (Filter 7)."""

import pytest

from src.community_detection import CommunityDetectionFilter, _cut_edges, _is_relational
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


# ── TestIsRelational ──────────────────────────────────────────────────────────

class TestIsRelational:
    def test_word_word_is_relational(self):
        assert _is_relational("w_fps", "w_lag") is True

    def test_sentence_sentence_is_relational(self):
        assert _is_relational("s_1", "s_42") is True

    def test_comment_comment_is_relational(self):
        assert _is_relational("c_3", "c_17") is True

    def test_word_sentence_is_hierarchical(self):
        assert _is_relational("w_fps", "s_1") is False

    def test_sentence_comment_is_hierarchical(self):
        assert _is_relational("s_1", "c_3") is False

    def test_word_comment_is_hierarchical(self):
        assert _is_relational("w_fps", "c_3") is False


# ── TestCutEdges ──────────────────────────────────────────────────────────────

class TestCutEdges:
    def test_k_communities_reached(self):
        g = _caterpillar_tree()
        communities = _cut_edges(g, k=3)
        assert len(communities) == 3

    def test_community_ids_are_1_indexed(self):
        g = _caterpillar_tree()
        communities = _cut_edges(g, k=3)
        assert set(communities.keys()) == {1, 2, 3}

    def test_all_nodes_assigned_to_communities(self):
        g = _caterpillar_tree()
        communities = _cut_edges(g, k=3)
        all_nodes = {n for nodes in communities.values() for n in nodes}
        assert all_nodes == set(g.nodes)

    def test_below_k_stops_gracefully(self):
        """Graph with only 2 cuttable edges cannot reach k=10 — stops at k=3."""
        g = _caterpillar_tree()
        communities = _cut_edges(g, k=10)
        assert len(communities) == 3  # best achievable

    def test_hierarchical_edges_never_cut(self):
        """A hierarchical edge with the lowest weight must never be removed."""
        g = _empty_graph()
        for n in ("w_x", "w_y", "s_1", "s_2"):
            g.nodes.append(n)
            g.index[n] = len(g.nodes) - 1
            for row in g.matrix:
                row.append(0.0)
            g.matrix.append([0.0] * len(g.nodes))

        add_edge(g, "w_x", "s_1", 0.001)   # hierarchical — lowest weight
        add_edge(g, "w_y", "s_2", 0.001)   # hierarchical — lowest weight
        add_edge(g, "w_x", "w_y", 1.0)     # relational  — higher weight
        add_edge(g, "s_1", "s_2", 1.0)     # relational  — higher weight

        _cut_edges(g, k=2)

        # Both hierarchical edges must survive the cut.
        assert g.matrix[g.index["w_x"]][g.index["s_1"]] > 0.0
        assert g.matrix[g.index["w_y"]][g.index["s_2"]] > 0.0

    def test_leaf_nodes_protected_by_degree_guard(self):
        """Leaf nodes (degree 1) must never be isolated by the cut.

        Chain: w_x - w_a - w_b - w_y
        w_x and w_y are leaves (degree 1); only w_a–w_b can be cut.
        Result: 2 components {w_x, w_a} and {w_b, w_y} — leaves stay attached.
        """
        g = _empty_graph()
        for n in ("w_x", "w_a", "w_b", "w_y"):
            g.nodes.append(n)
            g.index[n] = len(g.nodes) - 1
            for row in g.matrix:
                row.append(0.0)
            g.matrix.append([0.0] * len(g.nodes))

        add_edge(g, "w_x", "w_a", 0.1)  # w_x is a leaf — edge protected
        add_edge(g, "w_a", "w_b", 0.2)  # both have degree 2 — cuttable
        add_edge(g, "w_b", "w_y", 0.3)  # w_y is a leaf — edge protected

        communities = _cut_edges(g, k=3)
        # Only w_a–w_b can be cut; leaves w_x and w_y stay in their components.
        assert len(communities) == 2


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


# ── TestProcess ───────────────────────────────────────────────────────────────

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
