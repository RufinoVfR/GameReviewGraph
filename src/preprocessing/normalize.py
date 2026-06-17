"""Normalization (decision A1') and stopword loading for the preprocessing filter.

The RSLP stemmer is used **only** as an internal grouping key: morphological
variants of a word (``atualização``/``atualizações``) share a stem (``atualiz``)
and are therefore counted together. The token actually emitted — and thus the
``w_<token>`` graph node — is the most frequent *surface form* of the group,
**with its accent**. This keeps the grouping benefit of stemming without
polluting the final report with non-word radicals, and the ``group_key →
representative`` map is built and consumed entirely inside the filter's
``process()`` (no coupling between pipeline layers).
"""

import unicodedata
from collections import Counter

import nltk
from nltk.stem import RSLPStemmer

_stemmer = RSLPStemmer()


def fold_accents(token: str) -> str:
    """Strip diacritics from a token (e.g. ``história`` → ``historia``).

    Used only to canonicalize a token before stemming, so that accented and
    unaccented spellings of the same word land in the same group. The folded
    form is never emitted.

    Args:
        token: A word token.

    Returns:
        The token with combining accent marks removed.
    """
    decomposed = unicodedata.normalize("NFKD", token)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def group_key(token: str) -> str:
    """Compute the internal grouping key for a token (accent-folded RSLP stem).

    This key is an implementation detail of normalization — it groups
    morphological variants together but is never written to the output artifact.

    Args:
        token: A word token (already lowercased).

    Returns:
        The RSLP stem of the accent-folded token.
    """
    return _stemmer.stem(fold_accents(token.lower()))


def load_stopwords() -> set[str]:
    """Load the NLTK Portuguese stopword list.

    Requires the ``stopwords`` corpus to be available (provisioned in the Docker
    image at build time).

    Returns:
        Set of Portuguese stopwords (accented, lowercased).
    """
    return set(nltk.corpus.stopwords.words("portuguese"))


def build_representatives(tokens: list[str], min_freq: int) -> dict[str, str]:
    """Map each surviving group key to its representative surface form.

    Counts every token of the corpus by its ``group_key``. Groups whose total
    frequency is below ``min_freq`` are dropped entirely (low-frequency cut
    applied per group, not per surface form). For each surviving group, the
    representative is the most frequent surface form; ties are broken
    alphabetically so the result is deterministic.

    Args:
        tokens: Flat list of every surface token in the corpus (accented,
            lowercased, already cleaned of noise and stopwords).
        min_freq: Minimum total group frequency for a group to survive.

    Returns:
        Mapping ``{group_key: representative_surface_form}`` for surviving groups.
    """
    surface_counts: dict[str, Counter] = {}
    for token in tokens:
        key = group_key(token)
        surface_counts.setdefault(key, Counter())[token] += 1

    representatives: dict[str, str] = {}
    for key, counts in surface_counts.items():
        if sum(counts.values()) < min_freq:
            continue
        # Most frequent surface form; alphabetical order breaks frequency ties.
        representatives[key] = min(counts, key=lambda form: (-counts[form], form))
    return representatives
