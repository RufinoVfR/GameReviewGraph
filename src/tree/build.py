"""Pure construction pass: preprocessed corpus -> ``NaryTree``.

Walks the preprocessing output and builds all four levels of the tree. Assigns
the **global** sentence index (a counter across the whole dataset, which becomes
the ``s_<index>`` node downstream) and each word's **per-sentence** position
(input to the positional co-occurrence weight in ``word_graph``).
"""

from src.tree.structure import NaryTree, TreeNode
from src.types import ProcessedComment


def build_from_corpus(corpus: list[ProcessedComment]) -> NaryTree:
    """Build the N-ary tree from the preprocessing output.

    A comment always yields its ``comment`` node even when it has no sentences,
    so its ``c_<id>`` node survives downstream. The sentence index is global: it
    increments across comments, never resetting per comment.

    Args:
        corpus: List of processed comments ``{"id": int, "sentences":
            list[list[str]]}`` (the ``preprocessed.json`` contract).

    Returns:
        A fully built ``NaryTree`` rooted at a ``dataset`` node.
    """
    root = TreeNode({"type": "dataset"})
    tree = NaryTree(root)

    sentence_index = 0
    for comment in corpus:
        comment_node = tree.add_child(root, {"type": "comment", "id": comment["id"]})
        for sentence in comment["sentences"]:
            sentence_node = tree.add_child(
                comment_node, {"type": "sentence", "index": sentence_index}
            )
            sentence_index += 1
            for position, token in enumerate(sentence):
                tree.add_child(
                    sentence_node,
                    {"type": "word", "value": token, "position": position},
                )
    return tree
