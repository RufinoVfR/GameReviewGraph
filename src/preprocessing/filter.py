"""PreprocessingFilter — Filter 1 of the pipeline.

Turns raw Portuguese comments into normalized, structured tokens. Inherits the
Template Method ``AbstractFilter``: all S3/Redis I/O is handled by ``execute()``;
this class implements only ``process()``.
"""

from src.config import MIN_FREQ
from src.preprocessing.clean import (
    drop_noise,
    remove_punctuation,
    remove_stopwords,
    segment_sentences,
    to_lowercase,
    tokenize,
)
from src.preprocessing.normalize import (
    build_representatives,
    group_key,
    load_stopwords,
)
from src.shared.filter_base import AbstractFilter
from src.types import ProcessedComment, RawComment


class PreprocessingFilter(AbstractFilter):
    """Tokenize, clean, and normalize raw comments (decision A1').

    Reads ``comments.json`` (raw Portuguese text) and writes
    ``preprocessed.json`` (``id``/``topic`` preserved, ``text`` replaced by a
    list of sentences, each a list of normalized tokens).
    """

    name = "preprocessing"
    input_key = "raw"
    output_key = "preprocessed"

    def process(self, data: list[RawComment]) -> list[ProcessedComment]:
        """Transform raw comments into normalized, structured tokens.

        Three passes: (1) clean each comment into its sentence/token hierarchy of
        accented surface forms; (2) build the corpus-wide ``group_key →
        representative`` map (decision A1'), applying the low-frequency cut per
        group; (3) replace each surviving token by its representative and drop
        tokens whose group was cut. Empty sentences are discarded, but a comment
        is always kept (with its ``id``/``topic``) so its ``c_<id>`` node survives.

        Args:
            data: List of raw comments ``{"id", "topic", "text"}``.

        Returns:
            List of processed comments ``{"id", "topic", "sentences"}`` where
            ``sentences`` is a list of token lists. Token order is preserved.
        """
        stopwords = load_stopwords()

        # Pass 1 — clean, keeping the comment → sentences → tokens hierarchy.
        cleaned: list[list[list[str]]] = []
        for comment in data:
            sentences: list[list[str]] = []
            for sentence in segment_sentences(remove_punctuation(to_lowercase(comment["text"]))):
                tokens = remove_stopwords(drop_noise(tokenize(sentence)), stopwords)
                sentences.append(tokens)
            cleaned.append(sentences)

        # Pass 2 — corpus-wide grouping and low-frequency cut.
        flat = [token for comment in cleaned for sentence in comment for token in sentence]
        representatives = build_representatives(flat, MIN_FREQ)

        # Pass 3 — map each token to its group representative, dropping cut groups
        # and empty sentences while always preserving the comment.
        result: list[ProcessedComment] = []
        for comment, sentences in zip(data, cleaned):
            normalized_sentences: list[list[str]] = []
            for tokens in sentences:
                normalized = [
                    representatives[key]
                    for token in tokens
                    if (key := group_key(token)) in representatives
                ]
                if normalized:
                    normalized_sentences.append(normalized)
            result.append(
                {"id": comment["id"], "topic": comment["topic"], "sentences": normalized_sentences}
            )
        return result
