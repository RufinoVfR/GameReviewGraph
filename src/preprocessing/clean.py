"""Pure text and token cleaning helpers for the preprocessing filter.

These functions hold no NLP model state — they are deterministic string
transformations driven by regular expressions. Sentence segmentation and
tokenization use regex (decision B1): the corpus is short, well-behaved
fictional text where NLTK's trained ``punkt`` tokenizer adds no value and
would force an extra corpus download into the Docker image.
"""

import re

# Anything that is not a word character or whitespace is punctuation. The regex
# is unicode-aware by default in Python 3, so accented letters (á, ç, ã) are
# word characters and survive — only the accent itself is folded later, and
# only to build the grouping key (see normalize.fold_accents).
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_SENTENCE_BOUNDARY = re.compile(r"[.!?]+")
_WORD = re.compile(r"\w+", re.UNICODE)


def to_lowercase(text: str) -> str:
    """Lowercase a raw comment string.

    Args:
        text: Raw comment text.

    Returns:
        The text with all characters lowercased.
    """
    return text.lower()


def remove_punctuation(text: str) -> str:
    """Replace punctuation with spaces, preserving accented letters.

    Punctuation is turned into whitespace (not deleted) so that tokens on either
    side of a removed mark do not get glued together. Accents are kept here; they
    are only folded when computing the grouping key during normalization.

    Args:
        text: Input text (typically already lowercased).

    Returns:
        The text with every punctuation character replaced by a single space.
    """
    return _PUNCTUATION.sub(" ", text)


def segment_sentences(text: str) -> list[str]:
    """Split text into sentences on runs of ``.``, ``!`` or ``?``.

    Args:
        text: Input text.

    Returns:
        List of non-empty, stripped sentence strings. Empty fragments produced
        by trailing or consecutive delimiters are discarded.
    """
    return [part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part.strip()]


def tokenize(sentence: str) -> list[str]:
    """Extract word tokens from a sentence.

    Args:
        sentence: A single sentence string.

    Returns:
        List of word tokens (maximal runs of word characters), in order.
    """
    return _WORD.findall(sentence)


def drop_noise(tokens: list[str]) -> list[str]:
    """Drop purely numeric tokens and tokens shorter than three characters.

    Bare numbers and very short tokens rarely carry topic semantics and only add
    noise nodes to the graph.

    Args:
        tokens: List of word tokens.

    Returns:
        The tokens with numeric and ``len < 3`` entries removed, order preserved.
    """
    return [tok for tok in tokens if not tok.isdigit() and len(tok) >= 3]


def remove_stopwords(tokens: list[str], stopwords: set[str]) -> list[str]:
    """Remove Portuguese stopwords from a token list.

    Tokens are compared as-is (already lowercased, still accented) against the
    stopword set, which is the accented NLTK Portuguese list.

    Args:
        tokens: List of word tokens.
        stopwords: Set of stopwords to drop.

    Returns:
        The tokens with stopwords removed, order preserved.
    """
    return [tok for tok in tokens if tok not in stopwords]
