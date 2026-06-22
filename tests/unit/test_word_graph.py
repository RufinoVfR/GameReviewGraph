"""Unit tests for the word_graph/ package (Filter 3)."""

from src.shared.graph import (
    deserialize_graph,
    edge_count,
    get_edge_weight,
    invalid_prefixes,
    is_symmetric,
    node_count,
)
from src.tree.build import build_from_corpus
from src.tree.serialize import serialize
from src.word_graph import WordGraphFilter
from src.word_graph.cooccurrence import word_pair_deltas


def _sentence(index, *values):
    """Build a sentence node whose words take sequential positions (0, 1, 2, ...)."""
    return {
        "type": "sentence",
        "index": index,
        "children": [
            {"type": "word", "value": value, "position": position}
            for position, value in enumerate(values)
        ],
    }


def _tree(*sentences_per_comment):
    """Build a tree dict; each argument is the list of sentence nodes of one comment."""
    return {
        "type": "dataset",
        "children": [
            {"type": "comment", "id": cid, "children": list(sentences)}
            for cid, sentences in enumerate(sentences_per_comment, start=1)
        ],
    }


def _graph_of(tree):
    """Run the filter and deserialize its output graph."""
    return deserialize_graph(WordGraphFilter().process(tree))


class TestWordPairDeltas:
    def test_adjacent_pair_weight_is_half(self):
        """Neighbouring words (distance 1) get weight 0.5."""
        deltas = list(word_pair_deltas(_tree([_sentence(0, "fps", "cai")])))
        assert deltas == [("w_fps", "w_cai", 0.5)]

    def test_weight_decays_with_distance(self):
        """Weight is 1 / (1 + distance): 0.5, 1/3, 0.25 for distances 1, 2, 3."""
        deltas = dict(
            ((a, b), w) for a, b, w in word_pair_deltas(_tree([_sentence(0, "a", "b", "c", "d")]))
        )
        assert deltas[("w_a", "w_b")] == 0.5            # distance 1
        assert deltas[("w_a", "w_c")] == 1.0 / 3.0      # distance 2
        assert deltas[("w_a", "w_d")] == 0.25           # distance 3

    def test_all_unordered_pairs_once(self):
        """A sentence of n distinct words yields exactly C(n, 2) deltas."""
        deltas = list(word_pair_deltas(_tree([_sentence(0, "a", "b", "c", "d")])))
        assert len(deltas) == 6  # C(4, 2)
        pairs = [(a, b) for a, b, _ in deltas]
        assert len(set(pairs)) == 6  # no duplicates, no reversed repeats

    def test_document_order(self):
        """Pairs are emitted in i < j order within the sentence."""
        deltas = [(a, b) for a, b, _ in word_pair_deltas(_tree([_sentence(0, "a", "b", "c")]))]
        assert deltas == [("w_a", "w_b"), ("w_a", "w_c"), ("w_b", "w_c")]

    def test_repeated_value_is_skipped(self):
        """A word repeated in a sentence would self-loop; the pair is skipped."""
        assert list(word_pair_deltas(_tree([_sentence(0, "bug", "bug")]))) == []

    def test_repeated_value_still_pairs_with_others(self):
        """'a b a' pairs a-b twice (positions 0-1 and 1-2) but never a-a."""
        deltas = list(word_pair_deltas(_tree([_sentence(0, "a", "b", "a")])))
        assert deltas == [("w_a", "w_b", 0.5), ("w_b", "w_a", 0.5)]

    def test_single_word_sentence_yields_nothing(self):
        """A one-word sentence has no pairs."""
        assert list(word_pair_deltas(_tree([_sentence(0, "lag")]))) == []

    def test_empty_sentence_yields_nothing(self):
        """A sentence with no words yields no deltas."""
        assert list(word_pair_deltas(_tree([_sentence(0)]))) == []

    def test_empty_tree_yields_nothing(self):
        """A dataset with no comments yields no deltas."""
        assert list(word_pair_deltas({"type": "dataset", "children": []})) == []

    def test_spans_multiple_sentences_and_comments(self):
        """Deltas are produced across every sentence of every comment."""
        tree = _tree([_sentence(0, "a", "b")], [_sentence(1, "c", "d")])
        deltas = list(word_pair_deltas(tree))
        assert deltas == [("w_a", "w_b", 0.5), ("w_c", "w_d", 0.5)]


class TestProcess:
    def test_graph_is_symmetric_with_valid_prefixes(self):
        """process() returns a symmetric graph whose nodes are all w_-prefixed."""
        graph = _graph_of(_tree([_sentence(0, "jogo", "trava", "atualizacao")]))
        assert is_symmetric(graph)
        assert invalid_prefixes(graph) == []
        assert all(node.startswith("w_") for node in graph.nodes)

    def test_known_weights_exact(self):
        """Edge weights match the positional formula for distances 1 and 2."""
        graph = _graph_of(_tree([_sentence(0, "jogo", "trava", "atualizacao")]))
        assert get_edge_weight(graph, "w_jogo", "w_trava") == 0.5
        assert get_edge_weight(graph, "w_jogo", "w_atualizacao") == 1.0 / 3.0

    def test_node_and_edge_counts(self):
        """A triangle of three words gives 3 nodes and 3 edges."""
        graph = _graph_of(_tree([_sentence(0, "a", "b", "c")]))
        assert node_count(graph) == 3
        assert edge_count(graph) == 3

    def test_weights_accumulate_across_sentences(self):
        """The same pair in two sentences sums its positional weights."""
        graph = _graph_of(_tree([_sentence(0, "jogo", "trava")], [_sentence(1, "jogo", "trava")]))
        assert get_edge_weight(graph, "w_jogo", "w_trava") == 1.0

    def test_accumulates_three_occurrences(self):
        """Three adjacent co-occurrences sum to 1.5."""
        graph = _graph_of(
            _tree(
                [_sentence(0, "a", "b")],
                [_sentence(1, "a", "b")],
                [_sentence(2, "a", "b")],
            )
        )
        assert get_edge_weight(graph, "w_a", "w_b") == 1.5

    def test_no_self_loop_with_repeats(self):
        """Repeated words never produce a self-loop (process asserts validity)."""
        graph = _graph_of(_tree([_sentence(0, "a", "b", "a")]))
        for i in range(node_count(graph)):
            assert graph.matrix[i][i] == 0.0
        assert get_edge_weight(graph, "w_a", "w_b") == 1.0  # 0.5 + 0.5

    def test_isolated_word_is_not_a_node(self):
        """A word that never co-occurs with a different word is absent."""
        graph = _graph_of(_tree([_sentence(0, "lag")]))
        assert "w_lag" not in graph.nodes
        assert node_count(graph) == 0

    def test_accented_values_are_preserved_in_keys(self):
        """Accented surface forms flow into the node keys unchanged."""
        graph = _graph_of(_tree([_sentence(0, "atualização", "história")]))
        assert "w_atualização" in graph.nodes
        assert get_edge_weight(graph, "w_atualização", "w_história") == 0.5

    def test_empty_tree_produces_empty_graph(self):
        """No comments → an empty graph."""
        graph = _graph_of({"type": "dataset", "children": []})
        assert node_count(graph) == 0
        assert edge_count(graph) == 0

    def test_output_is_serializable_shape(self):
        """process() returns the JSON-native serialized-graph shape."""
        result = WordGraphFilter().process(_tree([_sentence(0, "a", "b")]))
        assert set(result) == {"nodes", "index", "matrix"}
        assert result["nodes"] == ["w_a", "w_b"]

    def test_output_is_deterministic(self):
        """The same tree yields an identical serialized graph."""
        tree = _tree([_sentence(0, "a", "b", "c")], [_sentence(1, "b", "c")])
        assert WordGraphFilter().process(tree) == WordGraphFilter().process(tree)

    def test_on_real_tree_from_corpus(self, processed_comments):
        """End-to-end on a tree built by the real producer chain."""
        tree = serialize(build_from_corpus(processed_comments))
        graph = _graph_of(tree)
        assert is_symmetric(graph)
        assert invalid_prefixes(graph) == []
        # "jogo trava atualização" → adjacent pair weight 0.5.
        assert get_edge_weight(graph, "w_jogo", "w_trava") == 0.5


class TestFilterContract:
    def test_declared_keys(self):
        """The filter declares the expected pipeline wiring."""
        assert WordGraphFilter.name == "word_graph"
        assert WordGraphFilter.input_key == "tree"
        assert WordGraphFilter.output_key == "word_graph"

    def test_importable_from_package_root(self):
        """WordGraphFilter is re-exported from the package root."""
        from src.word_graph import WordGraphFilter as Exported

        assert Exported is WordGraphFilter
