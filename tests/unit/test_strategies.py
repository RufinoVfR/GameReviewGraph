"""Unit tests for src.shared.strategies — community detection strategies.

Covers the level predicate (``_is_relational``) and the default
``ProgressiveEdgeCuttingStrategy`` behavior (baseline / method 1 of the final
report). These exercise, through the strategy's public ``detect`` API, the
cutting guarantees previously tested directly on the filter's private helpers:
target ``k`` reached, 1-indexed ids, full node coverage, graceful stop below
``k``, hierarchical edges never cut, and leaf nodes protected by the degree
guard.
"""

from src.shared.graph import add_edge
from src.shared.strategies import (
    DETECTION_METHODS,
    CommentSubgraphStrategy,
    GreedyModularityStrategy,
    MaxSpanningTreeStrategy,
    ProgressiveEdgeCuttingStrategy,
    RecalibratedHierarchyStrategy,
    _comment_subgraph,
    _is_relational,
)
from src.types import Graph


# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty_graph() -> Graph:
    return Graph(nodes=[], index={}, matrix=[])


def _with_nodes(*names: str) -> Graph:
    """Build an edgeless graph with the given node names."""
    g = _empty_graph()
    for n in names:
        g.nodes.append(n)
        g.index[n] = len(g.nodes) - 1
        for row in g.matrix:
            row.append(0.0)
        g.matrix.append([0.0] * len(g.nodes))
    return g


def _caterpillar_tree() -> Graph:
    """Build a 6-node tree: spine w_a–w_b–w_c with leaves s_1, s_2, s_3.

    Topology (spine weights are low so they are cut first):
        s_1 - w_a - w_b - w_c - s_3
                     |
                    s_2

    Cutting w_a–w_b and w_b–w_c splits the tree into 3 components
    (degree guard passes: all spine nodes have degree ≥ 2).
    """
    g = _with_nodes("w_a", "w_b", "w_c", "s_1", "s_2", "s_3")
    add_edge(g, "w_a", "w_b", 0.1)   # spine — lightest, cut first
    add_edge(g, "w_b", "w_c", 0.2)   # spine — second lightest
    add_edge(g, "w_a", "s_1", 5.0)   # hierarchical — heavy, not cut
    add_edge(g, "w_b", "s_2", 5.0)   # hierarchical — heavy, not cut
    add_edge(g, "w_c", "s_3", 5.0)   # hierarchical — heavy, not cut
    return g


def _community_of(communities: dict[int, list[str]], node: str) -> int:
    """Return the id of the community containing ``node``."""
    for community_id, nodes in communities.items():
        if node in nodes:
            return community_id
    raise AssertionError(f"{node!r} not assigned to any community")


def _three_level_graph() -> Graph:
    """Build a small graph spanning words, sentences and comments.

    Two comment clusters {c_1, c_2} and {c_3, c_4} joined by a weak bridge,
    each backed by a sentence and word, with hierarchical containment edges.
    Used to exercise the full-graph strategies and the comment subgraph.
    """
    g = _with_nodes("w_a", "w_b", "s_1", "s_2", "c_1", "c_2", "c_3", "c_4")
    # relational (same-level)
    add_edge(g, "w_a", "w_b", 0.4)
    add_edge(g, "s_1", "s_2", 0.5)
    add_edge(g, "c_1", "c_2", 2.0)   # cluster A
    add_edge(g, "c_3", "c_4", 2.0)   # cluster B
    add_edge(g, "c_2", "c_3", 0.1)   # weak bridge between clusters
    # hierarchical (cross-level containment)
    add_edge(g, "w_a", "s_1", 1.0)
    add_edge(g, "w_b", "s_2", 1.0)
    add_edge(g, "s_1", "c_1", 1.0)
    add_edge(g, "s_2", "c_3", 1.0)
    return g


def _assert_valid_partition(communities: dict[int, list[str]], expected_nodes: set[str]) -> None:
    """Assert the partition is 1-indexed, disjoint, and covers exactly expected_nodes."""
    assert set(communities.keys()) == set(range(1, len(communities) + 1))
    flat = [node for nodes in communities.values() for node in nodes]
    assert len(flat) == len(set(flat))  # disjoint
    assert set(flat) == expected_nodes


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


# ── TestProgressiveEdgeCutting ────────────────────────────────────────────────

class TestProgressiveEdgeCutting:
    def _detect(self, graph: Graph, k: int) -> dict[int, list[str]]:
        return ProgressiveEdgeCuttingStrategy().detect(graph, k)

    def test_k_communities_reached(self):
        communities = self._detect(_caterpillar_tree(), k=3)
        assert len(communities) == 3

    def test_community_ids_are_1_indexed(self):
        communities = self._detect(_caterpillar_tree(), k=3)
        assert set(communities.keys()) == {1, 2, 3}

    def test_all_nodes_assigned_to_communities(self):
        g = _caterpillar_tree()
        communities = self._detect(g, k=3)
        all_nodes = {n for nodes in communities.values() for n in nodes}
        assert all_nodes == set(g.nodes)

    def test_below_k_stops_gracefully(self):
        """Only 2 cuttable relational edges exist — cannot reach k=10."""
        communities = self._detect(_caterpillar_tree(), k=10)
        assert len(communities) == 3  # best achievable

    def test_input_graph_not_mutated(self):
        """detect() must copy — the caller's graph keeps its edges."""
        g = _caterpillar_tree()
        edges_before = sum(1 for row in g.matrix for w in row if w > 0.0)
        self._detect(g, k=3)
        edges_after = sum(1 for row in g.matrix for w in row if w > 0.0)
        assert edges_after == edges_before

    def test_hierarchical_edges_never_cut(self):
        """A low-weight hierarchical edge must never separate its endpoints."""
        g = _with_nodes("w_x", "w_y", "s_1", "s_2")
        add_edge(g, "w_x", "s_1", 0.001)   # hierarchical — lowest weight
        add_edge(g, "w_y", "s_2", 0.001)   # hierarchical — lowest weight
        add_edge(g, "w_x", "w_y", 1.0)     # relational  — higher weight
        add_edge(g, "s_1", "s_2", 1.0)     # relational  — higher weight

        communities = self._detect(g, k=2)

        # Each word stays with the sentence it is contained in.
        assert _community_of(communities, "w_x") == _community_of(communities, "s_1")
        assert _community_of(communities, "w_y") == _community_of(communities, "s_2")

    def test_leaf_nodes_protected_by_degree_guard(self):
        """Leaf nodes (degree 1) must never be isolated by the cut.

        Chain: w_x - w_a - w_b - w_y. Only w_a–w_b (both degree 2) is cuttable;
        leaves w_x and w_y stay attached → exactly 2 communities.
        """
        g = _with_nodes("w_x", "w_a", "w_b", "w_y")
        add_edge(g, "w_x", "w_a", 0.1)  # w_x is a leaf — edge protected
        add_edge(g, "w_a", "w_b", 0.2)  # both have degree 2 — cuttable
        add_edge(g, "w_b", "w_y", 0.3)  # w_y is a leaf — edge protected

        communities = self._detect(g, k=3)
        assert len(communities) == 2


# ── TestCommentSubgraph (method 4) ────────────────────────────────────────────

class TestCommentSubgraph:
    def test_subgraph_keeps_only_comment_nodes(self):
        sub = _comment_subgraph(_three_level_graph())
        assert set(sub.nodes) == {"c_1", "c_2", "c_3", "c_4"}

    def test_subgraph_drops_cross_level_edges(self):
        """Only c_↔c_ edges survive; hierarchical edges are gone."""
        sub = _comment_subgraph(_three_level_graph())
        # s_1–c_1 was hierarchical and s_1 is absent from the subgraph entirely.
        assert "s_1" not in sub.index

    def test_partition_covers_all_comments(self):
        communities = CommentSubgraphStrategy().detect(_three_level_graph(), k=2)
        _assert_valid_partition(communities, {"c_1", "c_2", "c_3", "c_4"})

    def test_splits_the_two_comment_clusters(self):
        """The weak bridge c_2–c_3 is cut, separating the two clusters."""
        communities = CommentSubgraphStrategy().detect(_three_level_graph(), k=2)
        assert _community_of(communities, "c_1") == _community_of(communities, "c_2")
        assert _community_of(communities, "c_3") == _community_of(communities, "c_4")
        assert _community_of(communities, "c_1") != _community_of(communities, "c_3")


# ── TestGreedyModularity (method 5) ───────────────────────────────────────────

class TestGreedyModularity:
    def test_recovers_two_clusters(self, clustered_graph):
        communities = GreedyModularityStrategy().detect(clustered_graph, k=2)
        assert len(communities) == 2
        assert _community_of(communities, "w_a1") == _community_of(communities, "w_a2")
        assert _community_of(communities, "w_b1") == _community_of(communities, "w_b2")
        assert _community_of(communities, "w_a1") != _community_of(communities, "w_b1")

    def test_partition_covers_all_nodes(self, clustered_graph):
        communities = GreedyModularityStrategy().detect(clustered_graph, k=2)
        _assert_valid_partition(communities, set(clustered_graph.nodes))

    def test_edgeless_graph_returns_singletons(self):
        g = _with_nodes("w_a", "w_b")
        communities = GreedyModularityStrategy().detect(g, k=1)
        _assert_valid_partition(communities, {"w_a", "w_b"})


# ── TestFullGraphStrategiesValid (methods 2 & 3) ──────────────────────────────

class TestFullGraphStrategiesValid:
    def test_recalibrated_hierarchy_valid_partition(self):
        g = _three_level_graph()
        communities = RecalibratedHierarchyStrategy().detect(g, k=3)
        _assert_valid_partition(communities, set(g.nodes))

    def test_max_spanning_tree_valid_partition(self):
        g = _three_level_graph()
        communities = MaxSpanningTreeStrategy().detect(g, k=3)
        _assert_valid_partition(communities, set(g.nodes))

    def test_input_graph_not_mutated(self):
        g = _three_level_graph()
        before = sum(1 for row in g.matrix for w in row if w > 0.0)
        RecalibratedHierarchyStrategy().detect(g, k=3)
        MaxSpanningTreeStrategy().detect(g, k=3)
        after = sum(1 for row in g.matrix for w in row if w > 0.0)
        assert after == before


# ── TestDetectionMethodsRegistry ──────────────────────────────────────────────

class TestDetectionMethodsRegistry:
    def test_five_methods_with_sequential_ids(self):
        assert [m["id"] for m in DETECTION_METHODS] == [1, 2, 3, 4, 5]

    def test_every_entry_has_label_and_strategy(self):
        for method in DETECTION_METHODS:
            assert isinstance(method["label"], str) and method["label"]
            assert hasattr(method["strategy"], "detect")

    def test_all_strategies_produce_valid_partition(self):
        g = _three_level_graph()
        comments = {"c_1", "c_2", "c_3", "c_4"}
        for method in DETECTION_METHODS:
            communities = method["strategy"].detect(g, k=3)
            flat = [n for nodes in communities.values() for n in nodes]
            assert len(flat) == len(set(flat))           # disjoint
            assert comments.issubset(set(flat))           # every comment covered
