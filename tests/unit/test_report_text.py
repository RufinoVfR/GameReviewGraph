"""Unit tests for report_text.py (Filter 10) — the report.json → report.txt projection."""

from src.report_text import ReportTextFilter


def _report() -> dict:
    return {
        "k": 10,
        "n_comments": 200,
        "methods": [
            {
                "id": 1,
                "label": "Corte progressivo na min-MST",
                "modularity_q": 0.0806,
                "stats": {
                    "n_communities": 2,
                    "size_min": 3,
                    "size_max": 703,
                    "singletons": 0,
                    "n_comments": 200,
                },
                "communities": [
                    {
                        "id": 1,
                        "topic": "desempenho",
                        "central_terms": ["fps", "lag"],
                        "comments": ["c_3", "c_17"],
                    },
                    {
                        "id": 2,
                        "topic": None,
                        "central_terms": [],
                        "comments": [],
                    },
                ],
            },
        ],
        "comparison": [
            {
                "id": 1,
                "label": "Corte progressivo na min-MST",
                "modularity_q": 0.0806,
                "n_communities": 2,
                "size_min": 3,
                "size_max": 703,
                "singletons": 0,
            },
        ],
    }


class TestReportTextFilter:
    def _render(self) -> str:
        return ReportTextFilter().process(_report())

    def test_filter_contract(self):
        assert ReportTextFilter.name == "report_text"
        assert ReportTextFilter.input_key == "report_json"
        assert ReportTextFilter.output_key == "report"
        assert ReportTextFilter.output_format == "text"

    def test_returns_string(self):
        assert isinstance(self._render(), str)

    def test_header_has_k_and_comment_count(self):
        text = self._render()
        assert "K-alvo: 10" in text
        assert "Comentários: 200" in text

    def test_topic_is_capitalized(self):
        assert "Tópico: Desempenho" in self._render()

    def test_missing_topic_uses_placeholder(self):
        assert "Tópico: (sem comentários)" in self._render()

    def test_global_q_repeated_per_community(self):
        """Decision #1: each community block shows the method's global Q."""
        text = self._render()
        assert text.count("Modularidade Q: 0.0806") >= 3  # header + 2 communities

    def test_empty_terms_render_dash(self):
        assert "Termos centrais: —" in self._render()

    def test_comparison_matrix_present(self):
        text = self._render()
        assert "Matriz comparativa" in text
