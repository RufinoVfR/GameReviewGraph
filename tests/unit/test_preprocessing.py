"""Unit tests for the preprocessing package (Filter 1)."""

from src.preprocessing import PreprocessingFilter
from src.preprocessing.clean import (
    drop_noise,
    remove_punctuation,
    remove_stopwords,
    segment_sentences,
    tokenize,
)
from src.preprocessing.normalize import (
    build_representatives,
    fold_accents,
    group_key,
)


class TestRemovePunctuation:
    def test_preserves_accented_letters(self):
        """Accents survive punctuation removal; only marks become spaces."""
        assert remove_punctuation("história, é envolvente!") == "história  é envolvente "

    def test_replaces_with_space_not_deletes(self):
        """Punctuation between words turns into a space, not an empty string."""
        parts = remove_punctuation("fim.começo").split()
        assert parts == ["fim", "começo"]


class TestSegmentSentences:
    def test_splits_on_terminators(self):
        """Splits on ., ! and ?."""
        assert segment_sentences("Um. Dois! Três?") == ["Um", "Dois", "Três"]

    def test_discards_empty_fragments(self):
        """Trailing/consecutive delimiters do not produce empty sentences."""
        assert segment_sentences("Oi!!!   ") == ["Oi"]


class TestTokenize:
    def test_extracts_word_runs(self):
        """Tokenizer returns maximal word-character runs in order."""
        assert tokenize("o fps caiu 30") == ["o", "fps", "caiu", "30"]


class TestDropNoise:
    def test_drops_numeric_and_short_tokens(self):
        """Purely numeric tokens and tokens shorter than 3 chars are removed."""
        assert drop_noise(["30", "fps", "ok", "lag", "a"]) == ["fps", "lag"]


class TestRemoveStopwords:
    def test_removes_only_listed_tokens(self):
        """Tokens present in the stopword set are dropped, others kept in order."""
        stopwords = {"o", "e", "da"}
        assert remove_stopwords(["o", "jogo", "e", "trava"], stopwords) == ["jogo", "trava"]


class TestFoldAccents:
    def test_strips_diacritics(self):
        """Combining accent marks are removed."""
        assert fold_accents("história") == "historia"
        assert fold_accents("atualização") == "atualizacao"


class TestGroupKey:
    def test_variants_share_a_key(self):
        """Singular/plural variants of a word map to the same grouping key."""
        assert group_key("jogo") == group_key("jogos")

    def test_key_is_accent_insensitive(self):
        """Accented and unaccented spellings collapse to the same key."""
        assert group_key("histÓRIA") == group_key("historia")


class TestBuildRepresentatives:
    def test_groups_variants_to_most_frequent_surface_form(self):
        """The representative is the most frequent surface form of the group."""
        tokens = ["atualização", "atualizações", "atualização"]
        reps = build_representatives(tokens, min_freq=1)
        assert reps[group_key("atualização")] == "atualização"

    def test_drops_groups_below_min_freq(self):
        """A group whose total frequency is below min_freq is excluded."""
        reps = build_representatives(["lag"], min_freq=2)
        assert group_key("lag") not in reps

    def test_ties_broken_alphabetically(self):
        """Distinct equal-frequency groups each emit their own surface form."""
        reps = build_representatives(["beta", "alfa"], min_freq=1)
        assert reps[group_key("alfa")] == "alfa"
        assert reps[group_key("beta")] == "beta"


# Corpus with repeated stems so tokens survive the MIN_FREQ=2 cut. "trava" and
# "travando" share a stem (exercising A1'); "atualização" repeats accented.
_REPEATED_CORPUS = [
    {"id": 1, "topic": "desempenho", "text": "O jogo trava muito. A atualização trava o jogo."},
    {"id": 2, "topic": "desempenho", "text": "Depois da atualização o jogo continua travando."},
]


class TestProcess:
    def test_shape_and_metadata_preserved(self, raw_comments):
        """Output keeps id/topic and replaces text with a sentences structure."""
        result = PreprocessingFilter().process(raw_comments)
        assert len(result) == len(raw_comments)
        for original, processed in zip(raw_comments, result):
            assert processed["id"] == original["id"]
            assert processed["topic"] == original["topic"]
            assert "text" not in processed
            assert isinstance(processed["sentences"], list)

    def test_tokens_are_clean_and_accented(self):
        """Emitted tokens are lowercase and keep their accents (decision A1')."""
        result = PreprocessingFilter().process(_REPEATED_CORPUS)
        tokens = [tok for c in result for sent in c["sentences"] for tok in sent]
        assert tokens, "expected at least one surviving token"
        for tok in tokens:
            assert tok == tok.lower()
        # "atualização" appears accented, never the folded radical "atualizacao".
        assert "atualização" in tokens
        assert "atualizacao" not in tokens

    def test_variants_collapse_to_representative(self):
        """A1': "trava"/"travando" share a stem and emit the frequent surface form."""
        result = PreprocessingFilter().process(_REPEATED_CORPUS)
        tokens = [tok for c in result for sent in c["sentences"] for tok in sent]
        assert "trava" in tokens
        assert "travando" not in tokens

    def test_stopwords_removed(self):
        """Common Portuguese stopwords do not appear in the output."""
        result = PreprocessingFilter().process(_REPEATED_CORPUS)
        tokens = [tok for c in result for sent in c["sentences"] for tok in sent]
        assert "depois" not in tokens
        assert "muito" not in tokens

    def test_multiple_sentences_per_comment(self):
        """A comment with several .!?-separated sentences yields several token lists.

        Guards the segmentation order: punctuation removal must run after
        sentence segmentation, otherwise the .!? terminators are stripped and
        the comment collapses into a single sentence.
        """
        data = [
            {"id": 1, "topic": "t", "text": "O jogo trava sempre. O jogo trava demais! O jogo trava ainda?"},
        ]
        result = PreprocessingFilter().process(data)
        assert len(result[0]["sentences"]) == 3

    def test_comment_kept_when_all_sentences_empty(self):
        """A comment whose tokens are all cut is still returned (empty sentences)."""
        data = [{"id": 7, "topic": "x", "text": "a o e."}]  # all stopwords/short
        result = PreprocessingFilter().process(data)
        assert len(result) == 1
        assert result[0]["id"] == 7
        assert result[0]["sentences"] == []


class TestExecute:
    def test_reads_raw_writes_preprocessed(self, raw_comments, mock_storage, mock_cache):
        """execute() loads comments.json, runs process(), writes preprocessed.json."""
        from src.config import S3_KEYS

        mock_storage.write_json(S3_KEYS["raw"], raw_comments)
        PreprocessingFilter().execute()

        written = mock_storage.read_json(S3_KEYS["preprocessed"])
        assert len(written) == len(raw_comments)
        assert {c["id"] for c in written} == {c["id"] for c in raw_comments}
        assert all("sentences" in c for c in written)

    def test_no_cache_ignores_cached_result(self, raw_comments, mock_storage, mock_cache):
        """execute(use_cache=False) reprocesses instead of serving a stale cache."""
        from src.config import S3_KEYS

        mock_storage.write_json(S3_KEYS["raw"], raw_comments)
        # Seed a poisoned cache entry that a cache read would surface verbatim.
        mock_cache.set("preprocessing", [{"id": 999, "topic": "stale", "sentences": []}])

        PreprocessingFilter().execute(use_cache=False)

        written = mock_storage.read_json(S3_KEYS["preprocessed"])
        assert {c["id"] for c in written} == {c["id"] for c in raw_comments}
        assert 999 not in {c["id"] for c in written}

    def test_cache_hit_short_circuits_process(self, raw_comments, mock_storage, mock_cache):
        """With caching on, a cached result is served without reprocessing."""
        from src.config import S3_KEYS

        mock_storage.write_json(S3_KEYS["raw"], raw_comments)
        mock_cache.set("preprocessing", [{"id": 999, "topic": "stale", "sentences": []}])

        PreprocessingFilter().execute()  # use_cache=True by default

        written = mock_storage.read_json(S3_KEYS["preprocessed"])
        assert {c["id"] for c in written} == {999}
