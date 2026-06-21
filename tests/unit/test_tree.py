"""Unit tests for the tree/ package (Filter 2)."""

from src.tree.build import build_from_corpus
from src.tree.filter import TreeFilter
from src.tree.serialize import from_dict, serialize


class TestBuildFromCorpus:
    def test_four_levels_and_counts(self, processed_comments):
        """The tree has one dataset root, one node per comment, and per-sentence words."""
        tree = build_from_corpus(processed_comments)

        assert tree.root.data == {"type": "dataset"}
        comments = tree.root.children
        assert [c.data["type"] for c in comments] == ["comment"] * 4
        assert [c.data["id"] for c in comments] == [1, 2, 3, 4]

        # Comment 1 has one sentence with three words.
        first_sentence = comments[0].children[0]
        assert first_sentence.data["type"] == "sentence"
        words = first_sentence.children
        assert [w.data["value"] for w in words] == ["jogo", "trava", "atualização"]
        assert [w.data["position"] for w in words] == [0, 1, 2]

    def test_global_sentence_index_is_continuous(self, processed_comments):
        """Sentence index counts across the whole dataset, not per comment."""
        tree = build_from_corpus(processed_comments)
        indices = [
            sentence.data["index"]
            for comment in tree.root.children
            for sentence in comment.children
        ]
        assert indices == [0, 1, 2, 3]

    def test_empty_comment_keeps_its_node(self):
        """A comment with no sentences still yields its comment node (c_<id> survives)."""
        tree = build_from_corpus([{"id": 7, "sentences": []}])
        comment = tree.root.children[0]
        assert comment.data == {"type": "comment", "id": 7}
        assert comment.children == []

    def test_bidirectional_navigation(self, processed_comments):
        """Every non-root node points back at its parent (US04)."""
        tree = build_from_corpus(processed_comments)
        assert tree.root.parent is None
        for comment in tree.root.children:
            assert comment.parent is tree.root
            for sentence in comment.children:
                assert sentence.parent is comment
                for word in sentence.children:
                    assert word.parent is sentence


class TestNavigationAccessors:
    def test_get_words_and_sentences(self, processed_comments):
        """Accessors return the children of the matching level."""
        tree = build_from_corpus(processed_comments)
        comment = tree.root.children[2]  # id 3
        sentences = tree.get_sentences_of_comment(comment)
        assert len(sentences) == 1
        words = tree.get_words_of_sentence(sentences[0])
        assert [w.data["value"] for w in words] == [
            "história",
            "envolvente",
            "personagens",
            "profundidade",
        ]

    def test_get_all_word_nodes_in_document_order(self, processed_comments):
        """All word nodes are collected left-to-right across the dataset."""
        tree = build_from_corpus(processed_comments)
        values = [w.data["value"] for w in tree.get_all_word_nodes()]
        assert values == [
            "jogo", "trava", "atualização",
            "fps", "caiu", "patch",
            "história", "envolvente", "personagens", "profundidade",
            "campanha", "principal", "narrativa", "excelente",
        ]


class TestSerialize:
    def test_uniform_node_shape(self, processed_comments):
        """Serialized tree matches the closed tree.json contract."""
        data = serialize(build_from_corpus(processed_comments))

        assert data["type"] == "dataset"
        comment = data["children"][0]
        assert comment["type"] == "comment"
        assert comment["id"] == 1
        sentence = comment["children"][0]
        assert sentence["type"] == "sentence"
        assert sentence["index"] == 0
        assert sentence["children"][0] == {"type": "word", "value": "jogo", "position": 0}

    def test_word_leaves_have_no_children_key(self, processed_comments):
        """Word nodes are leaves; non-word nodes always carry a children list."""
        data = serialize(build_from_corpus(processed_comments))
        word = data["children"][0]["children"][0]["children"][0]
        assert "children" not in word

    def test_no_topic_anywhere(self, processed_comments):
        """The gold topic label must never appear in tree.json."""
        data = serialize(build_from_corpus(processed_comments))

        def walk(node):
            assert "topic" not in node
            for child in node.get("children", []):
                walk(child)

        walk(data)

    def test_round_trip_rebuilds_parents(self, processed_comments):
        """serialize -> from_dict reconstructs the structure and parent links."""
        original = build_from_corpus(processed_comments)
        rebuilt = from_dict(serialize(original))

        assert serialize(rebuilt) == serialize(original)
        assert rebuilt.root.parent is None
        first_comment = rebuilt.root.children[0]
        assert first_comment.parent is rebuilt.root


class TestTreeFilter:
    def test_filter_contract(self):
        """The filter declares the expected pipeline wiring."""
        assert TreeFilter.name == "tree"
        assert TreeFilter.input_key == "preprocessed"
        assert TreeFilter.output_key == "tree"

    def test_process_returns_serialized_tree(self, processed_comments):
        """process() builds and serializes in one step."""
        result = TreeFilter().process(processed_comments)
        assert result == serialize(build_from_corpus(processed_comments))
