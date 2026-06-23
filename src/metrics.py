"""MetricsFilter — Filter 8 of the pipeline.

Computes the quality metrics of a community partition:

- **Weighted degree centrality** (US12) for each vertex inside its community,
  ``C(v) = Σ weight(v, u)`` over neighbours ``u`` in the same community, and the
  N most central word nodes per community as the topic's representative terms.
- **Modularity Q** (US13) of the whole partition,
  ``Q = (1/2m) Σ_ij [A_ij − k_i·k_j/2m] δ(c_i, c_j)``, an objective score of how
  much denser the intra-community links are than chance.

Inherits the Template Method ``AbstractFilter``: all S3/Redis I/O is handled by
``execute()``; this class implements only ``process()``.
"""

from typing import Any

from src.config import N_CENTRAL_TERMS
from src.shared.filter_base import AbstractFilter
from src.shared.graph import deserialize_graph
from src.shared.scoring import (
    calculate_modularity,
    community_centrality as _community_centrality,
    get_top_terms,
    normalize_communities as _normalize_communities,
    weighted_degree_centrality,
)

# Re-exported from src.shared.scoring so existing importers (and tests) can keep
# using ``from src.metrics import calculate_modularity`` etc. The single
# from-scratch implementation now lives in scoring.py, shared with analysis.py.
__all__ = [
    "MetricsFilter",
    "calculate_modularity",
    "get_top_terms",
    "weighted_degree_centrality",
]


class MetricsFilter(AbstractFilter):
    """Compute weighted degree centrality and extract top terms by community."""

    name = "metrics"
    input_key = "communities"
    extra_input_keys = ["final_graph"]
    output_key = "metrics"

    def process(self, data: dict[str, Any]) -> dict[str, Any]:
        """Process communities and the unified graph to compute metrics.

        Computes, per community, the intra-community weighted degree centrality
        and its top central terms, plus the global modularity Q of the whole
        partition as an objective quality score.

        Args:
            data: Multi-input payload ``{"primary": <communities dict>,
                "final_graph": <serialized final graph>}``.

        Returns:
            Dict with ``"centrality"`` (node_key -> centrality), ``"top_terms"``
            (community_id -> [word nodes]), and ``"modularity"`` (float Q).
        """
        communities = _normalize_communities(data["primary"])
        graph = deserialize_graph(data["final_graph"])

        centrality: dict[str, float] = {}
        top_terms: dict[int, list[str]] = {}

        for community_id, nodes in communities.items():
            community_centrality = _community_centrality(graph, nodes)
            centrality.update(community_centrality)
            top_terms[community_id] = get_top_terms(
                {community_id: nodes},
                graph,
                community_centrality,
                n=N_CENTRAL_TERMS,
            )[community_id]

        return {
            "centrality": centrality,
            "top_terms": top_terms,
            "modularity": calculate_modularity(graph, communities),
        }


if __name__ == "__main__":
    MetricsFilter().execute()