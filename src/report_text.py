"""ReportTextFilter — Filter 10 of the pipeline.

Projects the structured ``report.json`` (Filter 9) into the human-readable
``report.txt`` used for the academic deliverable. It recomputes **nothing** — it
only formats the report dict into the section-style layout. Per the team's
decision, each community block repeats its method's **global** modularity Q (Q is
a property of the whole partition, not of a single community).

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()`` and declares
``output_format = "text"`` so ``execute()`` writes the returned string verbatim.
"""

from typing import Any

from src.shared.filter_base import AbstractFilter


def _format_topic(topic: str | None) -> str:
    """Render a community's dominant topic for display.

    Args:
        topic: Gold topic string, or ``None`` for a community with no comments.

    Returns:
        The capitalized topic, or a placeholder when absent.
    """
    return topic.capitalize() if topic else "(sem comentários)"


def _format_method(method: dict[str, Any]) -> list[str]:
    """Render one method's header and per-community blocks.

    Args:
        method: A method entry from ``report.json`` (``id``, ``label``,
            ``modularity_q``, ``stats``, ``communities``).

    Returns:
        The list of text lines for this method's section.
    """
    stats = method["stats"]
    q = method["modularity_q"]
    lines = [
        "#" * 72,
        f"Método {method['id']} — {method['label']}",
        (
            f"Modularidade Q: {q:.4f} | Comunidades: {stats['n_communities']} | "
            f"Tamanhos: {stats['size_min']}–{stats['size_max']} | "
            f"Singletons: {stats['singletons']}"
        ),
        "#" * 72,
        "",
    ]
    for community in method["communities"]:
        terms = ", ".join(community["central_terms"]) or "—"
        comments = ", ".join(community["comments"]) or "—"
        lines += [
            f"=== Comunidade {community['id']} — Tópico: {_format_topic(community['topic'])} ===",
            f"Termos centrais: {terms}",
            f"Comentários associados: {comments}",
            f"Modularidade Q: {q:.4f}",
            "",
        ]
    return lines


def _format_comparison(comparison: list[dict[str, Any]]) -> list[str]:
    """Render the cross-method comparison matrix.

    Args:
        comparison: The ``comparison`` rows from ``report.json``.

    Returns:
        The list of text lines for the comparison table.
    """
    lines = [
        "=== Matriz comparativa dos métodos ===",
        f"{'Método':<8}{'Q':>10}{'Comunidades':>14}{'Tam. mín':>10}{'Tam. máx':>10}{'Singletons':>12}",
    ]
    for row in comparison:
        lines.append(
            f"{row['id']:<8}{row['modularity_q']:>10.4f}{row['n_communities']:>14}"
            f"{row['size_min']:>10}{row['size_max']:>10}{row['singletons']:>12}"
        )
    return lines


class ReportTextFilter(AbstractFilter):
    """Project ``report.json`` into the human-readable ``report.txt`` (Filter 10)."""

    name = "report_text"
    input_key = "report_json"
    output_key = "report"
    output_format = "text"

    def process(self, data: dict[str, Any]) -> str:
        """Format the structured report into section-style text.

        Args:
            data: The deserialized ``report.json`` dict (Filter 9 output).

        Returns:
            The full ``report.txt`` contents as a single string.
        """
        lines = [
            "=== Relatório final — Comparação de métodos de detecção de comunidades ===",
            f"K-alvo: {data['k']} | Comentários: {data['n_comments']}",
            "",
        ]
        for method in data["methods"]:
            lines += _format_method(method)
        lines += _format_comparison(data["comparison"])
        return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ReportTextFilter().execute()
