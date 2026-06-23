"""AnalysisFilter — Filter 9 of the pipeline.

Builds the structured final report ``report.json`` (US14): a **cross-method
comparison** of the five community-detection methods. For each method it runs the
corresponding ``CommunityDetectionStrategy`` over the unified ``final_graph``,
then, per community, derives the dominant gold topic, the central terms (top
weighted-degree word nodes), and the associated comments — plus the partition's
modularity Q and balance statistics. A ``comparison`` matrix summarizes all
methods side by side.

There is **no** chosen method: the report delivers the comparison; interpreting a
winner is left to the written analysis.

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()``. The human-readable
``report.txt`` is a separate projection produced by ``ReportTextFilter``
(``src/report_text.py``) from this same ``report.json``.
"""

from typing import Any

from src.config import K, N_CENTRAL_TERMS
from src.shared.filter_base import AbstractFilter
from src.shared.graph import deserialize_graph
from src.shared.scoring import (
    calculate_modularity,
    community_centrality,
    get_top_terms,
    partition_stats,
)
from src.shared.strategies import DETECTION_METHODS
from src.types import Communities, Graph, Report


def _gold_topics(raw: list[dict[str, Any]]) -> dict[str, str]:
    """Map each comment node key to its gold topic.

    Args:
        raw: The raw corpus (``comments.json``): a list of
            ``{"id": int, "topic": str, "text": str}`` records.

    Returns:
        A dict mapping ``"c_<id>"`` -> gold topic string.
    """
    return {f"c_{record['id']}": record["topic"] for record in raw}


def _dominant_topic(comments: list[str], topic_of: dict[str, str]) -> str | None:
    """Return the majority gold topic among a community's comment nodes.

    Ties are broken alphabetically (deterministic). A community with no comment
    nodes (e.g. a word-only community) has no topic.

    Args:
        comments: Comment node keys (``c_``) of the community.
        topic_of: Map of comment node key -> gold topic.

    Returns:
        The dominant topic string, or ``None`` if the community has no comments.
    """
    counts: dict[str, int] = {}
    for comment in comments:
        topic = topic_of.get(comment)
        if topic is not None:
            counts[topic] = counts.get(topic, 0) + 1
    if not counts:
        return None
    return min(counts, key=lambda topic: (-counts[topic], topic))


def _summarize_community(
    community_id: int,
    nodes: list[str],
    graph: Graph,
    topic_of: dict[str, str],
) -> dict[str, Any]:
    """Build one community's report entry: topic, central terms, comments.

    Args:
        community_id: 1-indexed id of the community.
        nodes: Node keys belonging to the community.
        graph: The unified final graph (for intra-community centrality).
        topic_of: Map of comment node key -> gold topic.

    Returns:
        A dict ``{"id", "topic", "central_terms", "comments"}``. ``central_terms``
        are the top weighted-degree word nodes with the ``w_`` prefix stripped.
    """
    comments = sorted(node for node in nodes if node.startswith("c_"))
    centrality = community_centrality(graph, nodes)
    top_terms = get_top_terms({community_id: nodes}, graph, centrality, N_CENTRAL_TERMS)
    central_terms = [term.removeprefix("w_") for term in top_terms[community_id]]
    return {
        "id": community_id,
        "topic": _dominant_topic(comments, topic_of),
        "central_terms": central_terms,
        "comments": comments,
    }


def _analyze_method(
    method: dict[str, Any],
    graph: Graph,
    topic_of: dict[str, str],
) -> dict[str, Any]:
    """Run one detection method and summarize its partition.

    Args:
        method: A registry entry ``{"id", "label", "strategy"}`` from
            ``DETECTION_METHODS``.
        graph: The unified final graph. Not mutated (strategies copy internally).
        topic_of: Map of comment node key -> gold topic.

    Returns:
        A dict with the method's id, label, global modularity Q, balance stats,
        and the per-community summaries.
    """
    partition: Communities = method["strategy"].detect(graph, K)
    communities = [
        _summarize_community(community_id, nodes, graph, topic_of)
        for community_id, nodes in sorted(partition.items())
    ]
    return {
        "id": method["id"],
        "label": method["label"],
        "modularity_q": calculate_modularity(graph, partition),
        "stats": partition_stats(partition),
        "communities": communities,
    }


class AnalysisFilter(AbstractFilter):
    """Generate the structured final report comparing the 5 detection methods (Filter 9).

    Reads the unified ``final_graph`` and the raw corpus (for gold topics), runs
    every method in ``DETECTION_METHODS``, and writes ``report.json`` with the
    per-method communities and the cross-method comparison matrix.
    """

    name = "analysis"
    input_key = "final_graph"
    extra_input_keys = ["raw"]
    output_key = "report_json"

    def process(self, data: dict[str, Any]) -> Report:
        """Build the cross-method comparison report.

        Args:
            data: Multi-input payload ``{"primary": <serialized final graph>,
                "raw": <raw corpus list>}``.

        Returns:
            The ``report.json`` dict (see ``src/types/report.py`` for the schema).
        """
        graph = deserialize_graph(data["primary"])
        topic_of = _gold_topics(data["raw"])

        methods = [_analyze_method(method, graph, topic_of) for method in DETECTION_METHODS]
        comparison = [
            {
                "id": method["id"],
                "label": method["label"],
                "modularity_q": method["modularity_q"],
                "n_communities": method["stats"]["n_communities"],
                "size_min": method["stats"]["size_min"],
                "size_max": method["stats"]["size_max"],
                "singletons": method["stats"]["singletons"],
            }
            for method in methods
        ]

        return {
            "k": K,
            "n_comments": len(data["raw"]),
            "methods": methods,
            "comparison": comparison,
        }


if __name__ == "__main__":
    AnalysisFilter().execute()
