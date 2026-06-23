"""Unit tests for src.shared.scoring — community scoring metrics.

Covers the functions extracted from metrics.py and shared between Filter 8
(metrics) and Filter 9 (analysis): weighted degree centrality, Newman modularity
Q, intra-community centrality, top-term extraction, id normalization, and
partition balance statistics.
"""

from src.shared.graph import add_node, new_graph
from src.shared.scoring import (
    calculate_modularity,
    community_centrality,
    get_top_terms,
    normalize_communities,
    partition_stats,
    weighted_degree_centrality,
)
from tests.conftest import make_graph


class TestWeightedDegreeCentrality:
    def test_isolated_node_is_zero(self):
        graph = new_graph()
        add_node(graph, "w_isolated")
        assert weighted_degree_centrality(graph)["w_isolated"] == 0.0

    def test_sum_of_incident_weights(self):
        graph = make_graph([("w_a", "w_b", 0.5), ("w_a", "w_c", 1.5)])
        centrality = weighted_degree_centrality(graph)
        assert centrality["w_a"] == 2.0
        assert centrality["w_b"] == 0.5


class TestCalculateModularity:
    def test_no_edges_returns_zero(self):
        graph = new_graph()
        add_node(graph, "w_a")
        assert calculate_modularity(graph, {1: ["w_a"]}) == 0.0

    def test_two_clusters_positive_modularity(self, clustered_graph):
        """A partition matching two dense clusters has positive Q."""
        partition = {
            1: ["w_a1", "w_a2", "w_a3"],
            2: ["w_b1", "w_b2", "w_b3"],
        }
        assert calculate_modularity(clustered_graph, partition) > 0.0

    def test_single_community_modularity_non_positive(self, clustered_graph):
        """Lumping everything into one community gives Q <= 0."""
        partition = {1: ["w_a1", "w_a2", "w_a3", "w_b1", "w_b2", "w_b3"]}
        assert calculate_modularity(clustered_graph, partition) <= 0.0

    def test_accepts_string_keys_after_normalization(self, clustered_graph):
        """normalize_communities feeds JSON-style string keys into Q."""
        raw = {"1": ["w_a1", "w_a2", "w_a3"], "2": ["w_b1", "w_b2", "w_b3"]}
        q = calculate_modularity(clustered_graph, normalize_communities(raw))
        assert q > 0.0


class TestNormalizeCommunities:
    def test_string_keys_become_ints(self):
        result = normalize_communities({"1": ["c_1"], "2": ["c_2"]})
        assert set(result.keys()) == {1, 2}

    def test_copies_node_lists(self):
        original = {"1": ["c_1"]}
        result = normalize_communities(original)
        result[1].append("c_2")
        assert original["1"] == ["c_1"]


class TestCommunityCentrality:
    def test_ignores_edges_outside_community(self):
        """Only edges with both endpoints inside the community count."""
        graph = make_graph([
            ("w_a", "w_b", 1.0),
            ("w_b", "w_c", 5.0),  # w_c outside the community
        ])
        centrality = community_centrality(graph, ["w_a", "w_b"])
        assert centrality == {"w_a": 1.0, "w_b": 1.0}

    def test_skips_unknown_nodes(self):
        graph = make_graph([("w_a", "w_b", 1.0)])
        centrality = community_centrality(graph, ["w_a", "w_b", "w_ghost"])
        assert "w_ghost" not in centrality


class TestGetTopTerms:
    def test_only_word_nodes_returned(self):
        graph = make_graph([("w_a", "w_b", 1.0)])
        centrality = {"w_a": 2.0, "w_b": 1.0, "s_1": 9.0, "c_3": 9.0}
        top = get_top_terms({1: ["w_a", "w_b", "s_1", "c_3"]}, graph, centrality, n=5)
        assert top[1] == ["w_a", "w_b"]

    def test_sorted_by_centrality_then_key(self):
        graph = new_graph()
        centrality = {"w_a": 1.0, "w_b": 3.0, "w_c": 3.0}
        top = get_top_terms({1: ["w_a", "w_b", "w_c"]}, graph, centrality, n=2)
        assert top[1] == ["w_b", "w_c"]  # ties broken by key ascending

    def test_truncates_to_n(self):
        graph = new_graph()
        centrality = {"w_a": 3.0, "w_b": 2.0, "w_c": 1.0}
        top = get_top_terms({1: ["w_a", "w_b", "w_c"]}, graph, centrality, n=1)
        assert top[1] == ["w_a"]


class TestPartitionStats:
    def test_empty_partition(self):
        assert partition_stats({}) == {
            "n_communities": 0,
            "size_min": 0,
            "size_max": 0,
            "singletons": 0,
            "n_comments": 0,
        }

    def test_counts_sizes_singletons_and_comments(self):
        partition = {
            1: ["c_1", "c_2", "w_x"],
            2: ["c_3"],
            3: ["s_1"],
        }
        stats = partition_stats(partition)
        assert stats["n_communities"] == 3
        assert stats["size_min"] == 1
        assert stats["size_max"] == 3
        assert stats["singletons"] == 2  # {c_3} and {s_1}
        assert stats["n_comments"] == 3  # c_1, c_2, c_3
