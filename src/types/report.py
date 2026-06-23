"""Type alias for the final report (Filter 9) output schema.

``Report`` is the structured ``report.json`` produced by ``analysis.py``: a
cross-method comparison of the community-detection methods (US14). It is a plain
``dict`` (not runtime-validated); this comment is the contract.

Shape::

    {
        "k": 10,                       # target number of communities
        "n_comments": 200,             # corpus size (gold comments)
        "methods": [                   # one entry per detection method
            {
                "id": 1,
                "label": "Corte progressivo na min-MST (baseline)",
                "modularity_q": 0.41,  # global Q of this method's partition
                "stats": {             # balance descriptors (partition_stats)
                    "n_communities": 10,
                    "size_min": 1,
                    "size_max": 703,
                    "singletons": 2,
                    "n_comments": 200,
                },
                "communities": [
                    {
                        "id": 1,
                        "topic": "desempenho",          # dominant gold topic
                        "central_terms": ["fps", "lag"],# top-N w_ nodes (no prefix)
                        "comments": ["c_3", "c_17"],    # associated c_ nodes
                    },
                    ...
                ],
            },
            ...
        ],
        "comparison": [                # the comparison matrix (one row per method)
            {
                "id": 1,
                "label": "Corte progressivo na min-MST (baseline)",
                "modularity_q": 0.41,
                "n_communities": 10,
                "size_min": 1,
                "size_max": 703,
                "singletons": 2,
            },
            ...
        ],
    }

There is **no** "chosen method": the report delivers the comparison matrix of all
methods; selecting/interpreting a winner is left to the written analysis.
"""

from typing import TypeAlias

# Output of analysis.py (Filter 9) — see module docstring for the full schema.
Report: TypeAlias = dict
