"""Unit tests for metrics.py (Filter 8) — weighted degree centrality and term extraction."""

import pytest

from src.metrics import (
    MetricsFilter,
    calculate_modularity,
    get_top_terms,
    weighted_degree_centrality,
)
from src.shared.graph.ops import add_edge, add_node, new_graph, serialize_graph
from tests.conftest import make_graph


class TestWeightedDegreeCentrality:
    """Test the weighted_degree_centrality function."""

    def test_single_node_zero_centrality(self):
        """A node with no edges has centrality 0.0."""
        graph = new_graph()
        from src.shared.graph.ops import add_node
        add_node(graph, "w_isolated")
        centrality = weighted_degree_centrality(graph)
        assert centrality["w_isolated"] == 0.0

    def test_two_nodes_connected(self):
        """Two connected nodes have matching edge weight as centrality."""
        graph = make_graph([("w_a", "w_b", 0.5)])
        centrality = weighted_degree_centrality(graph)
        assert centrality["w_a"] == 0.5
        assert centrality["w_b"] == 0.5

    def test_known_values(self):
        """Three neighbors with weights 0.5, 0.3, 0.8 → centrality 1.6."""
        # Create a node v connected to three neighbors.
        graph = new_graph()
        add_edge(graph, "w_v", "w_u1", 0.5)
        add_edge(graph, "w_v", "w_u2", 0.3)
        add_edge(graph, "w_v", "w_u3", 0.8)

        centrality = weighted_degree_centrality(graph)
        assert centrality["w_v"] == pytest.approx(1.6)
        assert centrality["w_u1"] == pytest.approx(0.5)
        assert centrality["w_u2"] == pytest.approx(0.3)
        assert centrality["w_u3"] == pytest.approx(0.8)

    def test_clustered_graph_centralities(self, clustered_graph):
        """In a clustered graph, nodes in dense clusters have higher centrality."""
        centrality = weighted_degree_centrality(clustered_graph)

        # Nodes in cluster A have high centrality (dense connections).
        assert centrality["w_a1"] > 3.0  # connected to a2, a3, b1
        assert centrality["w_a2"] > 3.0
        assert centrality["w_a3"] > 3.0

        # Nodes in cluster B have high centrality.
        assert centrality["w_b1"] > 3.0
        assert centrality["w_b2"] > 3.0
        assert centrality["w_b3"] > 3.0

        # The bridge edge (w_a1 — w_b1) is weak, so centralities are lower
        # than in an all-dense graph, but still present.
        assert centrality["w_a1"] < centrality["w_a2"] + 1.0


class TestGetTopTerms:
    """Test the get_top_terms function."""

    def test_single_community_single_word(self):
        """Single community with one word node yields that word."""
        graph = new_graph()
        from src.shared.graph.ops import add_node
        add_node(graph, "w_word1")

        centrality = {"w_word1": 1.0}
        communities = {1: ["w_word1", "s_0", "c_1"]}

        top_terms = get_top_terms(communities, graph, centrality, n=5)
        assert top_terms[1] == ["w_word1"]

    def test_filters_non_word_nodes(self):
        """Only w_* prefixed nodes are included; s_* and c_* are excluded."""
        graph = new_graph()
        from src.shared.graph.ops import add_node
        for node in ["w_word1", "w_word2", "s_0", "c_1"]:
            add_node(graph, node)

        centrality = {
            "w_word1": 1.0,
            "w_word2": 2.0,
            "s_0": 5.0,  # high centrality but wrong type
            "c_1": 10.0,  # even higher but wrong type
        }
        communities = {1: ["w_word1", "w_word2", "s_0", "c_1"]}

        top_terms = get_top_terms(communities, graph, centrality, n=5)
        assert top_terms[1] == ["w_word2", "w_word1"]  # only w_*, sorted by centrality desc

    def test_returns_top_n_only(self):
        """When n < num_words, only top n are returned."""
        graph = new_graph()
        from src.shared.graph.ops import add_node
        for node in ["w_a", "w_b", "w_c", "w_d"]:
            add_node(graph, node)

        centrality = {
            "w_a": 1.0,
            "w_b": 4.0,
            "w_c": 2.0,
            "w_d": 3.0,
        }
        communities = {1: ["w_a", "w_b", "w_c", "w_d"]}

        top_terms = get_top_terms(communities, graph, centrality, n=2)
        assert top_terms[1] == ["w_b", "w_d"]  # top 2 by centrality

    def test_multiple_communities(self):
        """Multiple communities are processed independently."""
        graph = new_graph()
        from src.shared.graph.ops import add_node
        for node in ["w_a1", "w_a2", "w_b1", "w_b2"]:
            add_node(graph, node)

        centrality = {
            "w_a1": 1.0,
            "w_a2": 2.0,
            "w_b1": 3.0,
            "w_b2": 4.0,
        }
        communities = {
            1: ["w_a1", "w_a2"],
            2: ["w_b1", "w_b2"],
        }

        top_terms = get_top_terms(communities, graph, centrality, n=1)
        assert top_terms[1] == ["w_a2"]
        assert top_terms[2] == ["w_b2"]

    def test_ties_use_stable_order(self):
        """Ties are broken alphabetically for deterministic output."""
        graph = new_graph()
        from src.shared.graph.ops import add_node

        for node in ["w_b", "w_a"]:
            add_node(graph, node)

        centrality = {"w_b": 2.0, "w_a": 2.0}
        communities = {1: ["w_b", "w_a"]}

        top_terms = get_top_terms(communities, graph, centrality, n=2)
        assert top_terms[1] == ["w_a", "w_b"]

    def test_empty_community(self):
        """Community with no word nodes yields empty list."""
        graph = new_graph()
        from src.shared.graph.ops import add_node
        add_node(graph, "s_0")
        add_node(graph, "c_1")

        centrality = {"s_0": 5.0, "c_1": 10.0}
        communities = {1: ["s_0", "c_1"]}

        top_terms = get_top_terms(communities, graph, centrality, n=5)
        assert top_terms[1] == []


class TestCalculateModularity:
    """Test the calculate_modularity function against known values."""

    def test_two_separated_edges_two_communities(self):
        """Two disjoint unit edges, each its own community → Q = 0.5.

        Edges (a-b, 1) and (c-d, 1): 2m = 4, each community has W_in = 1 and
        Σ_tot = 2, so Q = 2·[2·1/4 − (2/4)²] = 2·(0.5 − 0.25) = 0.5.
        """
        graph = make_graph([("w_a", "w_b", 1.0), ("w_c", "w_d", 1.0)])
        communities = {1: ["w_a", "w_b"], 2: ["w_c", "w_d"]}
        assert calculate_modularity(graph, communities) == pytest.approx(0.5)

    def test_single_community_all_internal_is_zero(self):
        """The same graph with every node in one community → Q = 0.0.

        W_in = 2 (both edges internal), Σ_tot = 4: Q = 2·2/4 − (4/4)² = 0.
        """
        graph = make_graph([("w_a", "w_b", 1.0), ("w_c", "w_d", 1.0)])
        communities = {1: ["w_a", "w_b", "w_c", "w_d"]}
        assert calculate_modularity(graph, communities) == pytest.approx(0.0)

    def test_singleton_communities_are_negative(self):
        """Every node alone has no internal edges → Q < 0 (and ≥ −1).

        Four singleton communities, each k_i = 1, 2m = 4:
        Q = Σ −(k_i/2m)² = 4·−(1/4)² = −0.25.
        """
        graph = make_graph([("w_a", "w_b", 1.0), ("w_c", "w_d", 1.0)])
        communities = {1: ["w_a"], 2: ["w_b"], 3: ["w_c"], 4: ["w_d"]}
        q = calculate_modularity(graph, communities)
        assert q == pytest.approx(-0.25)
        assert -1.0 <= q <= 1.0

    def test_edgeless_graph_returns_zero(self):
        """A graph with no edges (2m == 0) yields Q = 0.0, not a division error."""
        graph = new_graph()
        add_node(graph, "w_a")
        add_node(graph, "w_b")
        assert calculate_modularity(graph, {1: ["w_a"], 2: ["w_b"]}) == 0.0

    def test_clustered_graph_partition_beats_merged(self, clustered_graph):
        """The natural 2-cluster split scores higher than lumping all together."""
        split = {
            1: ["w_a1", "w_a2", "w_a3"],
            2: ["w_b1", "w_b2", "w_b3"],
        }
        merged = {1: ["w_a1", "w_a2", "w_a3", "w_b1", "w_b2", "w_b3"]}
        q_split = calculate_modularity(clustered_graph, split)
        q_merged = calculate_modularity(clustered_graph, merged)
        assert q_split > q_merged
        assert -1.0 <= q_split <= 1.0


class TestMetricsFilter:
    """Test the MetricsFilter class (Filter 8)."""

    def test_filter_attributes(self):
        """MetricsFilter has correct name and I/O keys."""
        filt = MetricsFilter()
        assert filt.name == "metrics"
        assert filt.input_key == "communities"
        assert filt.extra_input_keys == ["final_graph"]
        assert filt.output_key == "metrics"

    def test_process_minimal(self, clustered_graph):
        """Process a minimal communities dict and final graph."""

        serialized_graph = serialize_graph(clustered_graph)
        communities = {
            1: ["w_a1", "w_a2", "w_a3"],
            2: ["w_b1", "w_b2", "w_b3"],
        }

        filt = MetricsFilter()
        result = filt.process({"primary": communities, "final_graph": serialized_graph})

        assert "centrality" in result
        assert "top_terms" in result
        assert "modularity" in result
        assert isinstance(result["centrality"], dict)
        assert isinstance(result["top_terms"], dict)
        assert isinstance(result["modularity"], float)
        assert -1.0 <= result["modularity"] <= 1.0

        # Top terms should be present for both communities.
        assert 1 in result["top_terms"]
        assert 2 in result["top_terms"]

        assert result["centrality"]["w_a1"] == pytest.approx(3.8)
        assert result["centrality"]["w_b1"] == pytest.approx(3.8)

    def test_process_ignores_external_edges(self):
        """Centrality is computed only inside each community subgraph."""
        graph = make_graph([
            ("w_a1", "w_a2", 2.0),
            ("w_a1", "w_a3", 1.8),
            ("w_a2", "w_a3", 1.9),
            ("w_b1", "w_b2", 2.1),
            ("w_b1", "w_b3", 1.7),
            ("w_b2", "w_b3", 2.0),
            ("w_a1", "w_b1", 0.1),
        ])

        serialized_graph = serialize_graph(graph)
        communities = {1: ["w_a1", "w_a2", "w_a3"], 2: ["w_b1", "w_b2", "w_b3"]}

        filt = MetricsFilter()
        result = filt.process({"primary": communities, "final_graph": serialized_graph})

        assert result["centrality"]["w_a1"] == pytest.approx(3.8)
        assert result["centrality"]["w_b1"] == pytest.approx(3.8)
        assert result["centrality"]["w_a1"] != pytest.approx(3.9)

