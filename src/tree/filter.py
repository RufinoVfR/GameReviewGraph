"""TreeFilter — Filter 2 of the pipeline.

Turns the normalized token hierarchy into the N-ary tree Dataset -> Comment ->
Sentence -> Word and emits it as ``tree.json``. Inherits the Template Method
``AbstractFilter``: all S3/Redis I/O is handled by ``execute()``; this class
implements only ``process()``, which is a thin orchestration of the package's
build and serialize passes.
"""

from src.shared.filter_base import AbstractFilter
from src.tree.build import build_from_corpus
from src.tree.serialize import serialize
from src.types import ProcessedComment


class TreeFilter(AbstractFilter):
    """Build the N-ary tree from preprocessed comments (Dataset -> Word).

    Reads ``preprocessed.json`` (``list[{"id", "sentences"}]``) and writes
    ``tree.json`` (uniform-node nested format). The gold ``topic`` label never
    appears: it was already dropped upstream and must not flow down the pipeline.
    """

    name = "tree"
    input_key = "preprocessed"
    output_key = "tree"

    def process(self, data: list[ProcessedComment]) -> dict:
        """Build the tree from the corpus and serialize it.

        Args:
            data: List of processed comments ``{"id": int, "sentences":
                list[list[str]]}`` loaded from ``preprocessed.json``.

        Returns:
            The serialized N-ary tree (uniform-node nested dict) for
            ``tree.json``.
        """
        return serialize(build_from_corpus(data))
