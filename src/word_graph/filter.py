"""WordGraphFilter — Filter 3 of the pipeline.

Builds the word co-occurrence graph from ``tree.json`` and writes
``word_graph.json``. Inherits the Template Method ``AbstractFilter``: all S3/Redis
I/O is handled by ``execute()``; this class implements only ``process()``, which
feeds the co-occurrence deltas into the shared graph builder and serializes the
result. The positional weight formula lives in ``cooccurrence.py`` (domain),
never in ``src/shared/graph``.
"""

from src.shared.graph import assert_valid, build_graph_from_deltas, serialize_graph
from src.shared.filter_base import AbstractFilter
from src.word_graph.cooccurrence import word_pair_deltas


class WordGraphFilter(AbstractFilter):
    """Build the positional word co-occurrence graph (US05).

    Reads ``tree.json`` (uniform-node dict) and writes ``word_graph.json`` (the
    serialized ``Graph``: ``nodes`` / ``index`` / ``matrix``). Word nodes are
    keyed ``w_<value>``; words that never co-occur with a different word do not
    appear (the graph is edge-driven).
    """

    name = "word_graph"
    input_key = "tree"
    output_key = "word_graph"

    def process(self, data: dict) -> dict:
        """Build the word graph from the tree and serialize it.

        Args:
            data: The deserialized ``tree.json`` dict loaded from S3.

        Returns:
            The serialized word co-occurrence ``Graph`` for ``word_graph.json``.
        """
        graph = build_graph_from_deltas(word_pair_deltas(data))
        assert_valid(graph)
        return serialize_graph(graph)
