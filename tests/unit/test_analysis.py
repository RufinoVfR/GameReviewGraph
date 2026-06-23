"""Unit tests for analysis.py (Filter 9) — the cross-method comparison report."""

from src.analysis import AnalysisFilter, _dominant_topic, _gold_topics
from src.shared.graph import add_edge, serialize_graph
from src.types import Graph


# ── Helpers ───────────────────────────────────────────────────────────────────

def _with_nodes(*names: str) -> Graph:
    g = Graph(nodes=[], index={}, matrix=[])
    for n in names:
        g.nodes.append(n)
        g.index[n] = len(g.nodes) - 1
        for row in g.matrix:
            row.append(0.0)
        g.matrix.append([0.0] * len(g.nodes))
    return g


def _three_level_graph() -> Graph:
    g = _with_nodes("w_fps", "w_lag", "s_1", "s_2", "c_1", "c_2", "c_3", "c_4")
    add_edge(g, "w_fps", "w_lag", 0.4)
    add_edge(g, "s_1", "s_2", 0.5)
    add_edge(g, "c_1", "c_2", 2.0)
    add_edge(g, "c_3", "c_4", 2.0)
    add_edge(g, "c_2", "c_3", 0.1)
    add_edge(g, "w_fps", "s_1", 1.0)
    add_edge(g, "w_lag", "s_2", 1.0)
    add_edge(g, "s_1", "c_1", 1.0)
    add_edge(g, "s_2", "c_3", 1.0)
    return g


def _raw() -> list[dict]:
    return [
        {"id": 1, "topic": "desempenho", "text": "..."},
        {"id": 2, "topic": "desempenho", "text": "..."},
        {"id": 3, "topic": "narrativa", "text": "..."},
        {"id": 4, "topic": "narrativa", "text": "..."},
    ]


# ── TestGoldTopics ────────────────────────────────────────────────────────────

class TestGoldTopics:
    def test_maps_comment_keys_to_topics(self):
        assert _gold_topics(_raw()) == {
            "c_1": "desempenho",
            "c_2": "desempenho",
            "c_3": "narrativa",
            "c_4": "narrativa",
        }


class TestDominantTopic:
    def test_majority_wins(self):
        topic_of = {"c_1": "desempenho", "c_2": "desempenho", "c_3": "narrativa"}
        assert _dominant_topic(["c_1", "c_2", "c_3"], topic_of) == "desempenho"

    def test_tie_broken_alphabetically(self):
        topic_of = {"c_1": "narrativa", "c_2": "desempenho"}
        assert _dominant_topic(["c_1", "c_2"], topic_of) == "desempenho"

    def test_no_comments_returns_none(self):
        assert _dominant_topic([], {"c_1": "desempenho"}) is None


# ── TestAnalysisFilter ────────────────────────────────────────────────────────

class TestAnalysisFilter:
    def _report(self) -> dict:
        data = {"primary": serialize_graph(_three_level_graph()), "raw": _raw()}
        return AnalysisFilter().process(data)

    def test_filter_contract(self):
        assert AnalysisFilter.name == "analysis"
        assert AnalysisFilter.input_key == "final_graph"
        assert AnalysisFilter.extra_input_keys == ["raw"]
        assert AnalysisFilter.output_key == "report_json"

    def test_top_level_shape(self):
        report = self._report()
        assert report["k"] == 10
        assert report["n_comments"] == 4
        assert len(report["methods"]) == 5
        assert len(report["comparison"]) == 5
        assert "chosen_method" not in report  # no winner is elected

    def test_each_method_has_metrics_and_communities(self):
        for method in self._report()["methods"]:
            assert isinstance(method["modularity_q"], float)
            assert set(method["stats"]) == {
                "n_communities", "size_min", "size_max", "singletons", "n_comments",
            }
            assert method["communities"]

    def test_central_terms_have_no_prefix(self):
        for method in self._report()["methods"]:
            for community in method["communities"]:
                for term in community["central_terms"]:
                    assert not term.startswith("w_")

    def test_comments_carry_dominant_topic(self):
        """Any community holding comments must resolve a gold topic."""
        for method in self._report()["methods"]:
            for community in method["communities"]:
                if community["comments"]:
                    assert community["topic"] in {"desempenho", "narrativa"}

    def test_comparison_rows_mirror_method_stats(self):
        report = self._report()
        by_id = {m["id"]: m for m in report["methods"]}
        for row in report["comparison"]:
            method = by_id[row["id"]]
            assert row["modularity_q"] == method["modularity_q"]
            assert row["n_communities"] == method["stats"]["n_communities"]
            assert row["singletons"] == method["stats"]["singletons"]
