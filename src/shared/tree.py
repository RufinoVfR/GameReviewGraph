"""Readers over the deserialized ``tree.json`` dict (uniform-node format).

These helpers live here, not in ``src/tree/``, so the graph filters that consume
the tree never import another filter — the same reason graph (de)serialization
lives in ``src/shared/graph`` rather than inside each graph filter. They walk the
plain nested dict produced by the ``tree`` filter and apply the ``w_``/``s_``/``c_``
key convention; they carry **no domain logic** (the positional weight formula and
the sentence/comment normalizations stay in their respective graph filters).

The on-disk shape is the closed contract from ``docs/guia_implementacao.md`` (C.1):
a uniform node ``{"type", "children", ...}`` where ``comment`` carries ``id``,
``sentence`` carries a global ``index``, and ``word`` leaves carry ``value`` +
``position``. Node prefixes: ``w_<value>``, ``s_<index>``, ``c_<id>``.
"""

from collections.abc import Iterator

from src.types import NodeKey

# Single source of truth for the node-key prefixes derived from the tree.
WORD_PREFIX = "w_"
SENTENCE_PREFIX = "s_"
COMMENT_PREFIX = "c_"


def iter_comments(tree: dict) -> Iterator[dict]:
    """Yield each ``comment`` node of the tree, in order.

    Args:
        tree: The deserialized ``tree.json`` dict (the ``dataset`` root).

    Yields:
        Each ``comment`` node dict (``id`` + ``children``).
    """
    yield from tree.get("children", [])


def iter_sentences(tree: dict) -> Iterator[dict]:
    """Yield every ``sentence`` node across all comments, in document order.

    Args:
        tree: The deserialized ``tree.json`` dict (the ``dataset`` root).

    Yields:
        Each ``sentence`` node dict (``index`` + ``children``).
    """
    for comment in iter_comments(tree):
        yield from comment.get("children", [])


def iter_words(sentence: dict) -> Iterator[dict]:
    """Yield the ``word`` leaves of a sentence, in reading order.

    Args:
        sentence: A ``sentence`` node dict.

    Yields:
        Each ``word`` leaf dict (``value`` + ``position``).
    """
    yield from sentence.get("children", [])


def hierarchical_edges(tree: dict) -> list[tuple[NodeKey, NodeKey]]:
    """Build the tree's hierarchical edges as node-key pairs.

    Produces a ``(w_<value>, s_<index>)`` edge for every word and a
    ``(s_<index>, c_<id>)`` edge for every sentence — the level-linking edges
    that ``final_graph`` adds on top of the three relational graphs.

    Args:
        tree: The deserialized ``tree.json`` dict (the ``dataset`` root).

    Returns:
        Hierarchical edges as ``(child_key, parent_key)`` tuples, in document
        order. May contain duplicates when a word value repeats within a
        sentence; consumers add edges idempotently.
    """
    edges: list[tuple[NodeKey, NodeKey]] = []
    for comment in iter_comments(tree):
        comment_key = f"{COMMENT_PREFIX}{comment['id']}"
        for sentence in comment.get("children", []):
            sentence_key = f"{SENTENCE_PREFIX}{sentence['index']}"
            edges.append((sentence_key, comment_key))
            for word in iter_words(sentence):
                edges.append((f"{WORD_PREFIX}{word['value']}", sentence_key))
    return edges
