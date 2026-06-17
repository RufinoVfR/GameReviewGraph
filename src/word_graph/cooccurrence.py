"""Within-sentence word co-occurrence: pairs and their positional weight.

This is the domain logic of the word graph (US05): two words co-occur when they
appear in the same sentence, and the strength of their link decays with the
distance between their positions. It lives in the filter package (not in
``src/shared/graph``, which forbids domain logic) and reads the tree through the
shared readers, so it never imports ``src/tree/``.

The pairing is implemented from scratch (a ``j > i`` double loop) rather than via
``itertools.combinations``: each unordered pair of distinct sentence positions is
visited exactly once, which keeps the undirected graph from being weighted twice.
"""

from collections.abc import Iterator

from src.shared.tree import iter_sentences, iter_words

WORD_PREFIX = "w_"


def word_pair_deltas(tree: dict) -> Iterator[tuple[str, str, float]]:
    """Yield positional co-occurrence deltas for every word pair, per sentence.

    For each sentence, every unordered pair of words at distinct positions
    contributes a ``1 / (1 + |pos_i - pos_j|)`` delta to the edge between them.
    Pairs whose two words share the same value are skipped: they would form a
    self-loop (forbidden by ``assert_valid``), e.g. a word repeated in a
    sentence. Deltas for the same pair across sentences are summed downstream by
    ``build_graph_from_deltas``.

    Args:
        tree: The deserialized ``tree.json`` dict (the ``dataset`` root).

    Yields:
        ``(w_<value_i>, w_<value_j>, weight)`` triples, one per co-occurring
        word pair occurrence.
    """
    for sentence in iter_sentences(tree):
        words = list(iter_words(sentence))
        for i in range(len(words)):
            for j in range(i + 1, len(words)):
                first, second = words[i], words[j]
                if first["value"] == second["value"]:
                    continue
                weight = 1.0 / (1.0 + abs(first["position"] - second["position"]))
                yield (
                    f"{WORD_PREFIX}{first['value']}",
                    f"{WORD_PREFIX}{second['value']}",
                    weight,
                )
