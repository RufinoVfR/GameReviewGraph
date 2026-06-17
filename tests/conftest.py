"""Shared pytest fixtures for GameReviewGraph test suite."""
import pytest

from src.shared.graph.ops import add_edge, new_graph
from src.types import Graph


# ── Helper functions ───────────────────────────────────────────────────────────


def make_graph(edges: list[tuple[str, str, float]]) -> Graph:
    """Build a symmetric Graph from a list of (u, v, weight) edge tuples.

    Args:
        edges: List of (u, v, weight) tuples. Each edge is stored in both
               directions so the result is always undirected.

    Returns:
        A Graph (adjacency matrix + name-to-index mapping).
    """
    graph = new_graph()
    for u, v, w in edges:
        add_edge(graph, u, v, w)
    return graph


# ── Domain fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def raw_comments() -> list[dict]:
    """Minimal dataset with two topics for unit tests."""
    return [
        {"id": 1, "topic": "desempenho", "text": "O jogo trava muito depois da atualização."},
        {"id": 2, "topic": "desempenho", "text": "O fps caiu bastante após o último patch."},
        {"id": 3, "topic": "narrativa", "text": "A história é envolvente e os personagens têm profundidade."},
        {"id": 4, "topic": "narrativa", "text": "A campanha principal tem uma narrativa excelente."},
    ]


@pytest.fixture
def processed_comments() -> list[dict]:
    """Pre-tokenized comments matching the output contract of the preprocessing/ package.

    No ``topic``: topic detection is unsupervised, so the gold label is dropped
    after ingestion (it stays in the raw dataset, re-joined by ``id`` only at
    validation). Tokens are accented surface forms (decision A1'): the RSLP stem
    only groups variants internally, while the emitted token is the most frequent
    surface form of the group, with its accent preserved.
    """
    return [
        {"id": 1, "sentences": [["jogo", "trava", "atualização"]]},
        {"id": 2, "sentences": [["fps", "caiu", "patch"]]},
        {"id": 3, "sentences": [["história", "envolvente", "personagens", "profundidade"]]},
        {"id": 4, "sentences": [["campanha", "principal", "narrativa", "excelente"]]},
    ]


@pytest.fixture
def small_word_graph() -> Graph:
    """Minimal word graph for testing sentence/comment graph builders."""
    return make_graph([
        ("w_jogo", "w_trav", 1.0),
        ("w_jogo", "w_atualizacao", 0.5),
        ("w_trav", "w_atualizacao", 1.0),
        ("w_fps", "w_cai", 1.0),
        ("w_fps", "w_patch", 0.5),
        ("w_cai", "w_patch", 1.0),
    ])


@pytest.fixture
def clustered_graph() -> Graph:
    """Graph with two dense clusters and one weak bridge edge.

    Cluster A: w_a1, w_a2, w_a3 — strongly connected (weights ~2.0).
    Cluster B: w_b1, w_b2, w_b3 — strongly connected (weights ~2.0).
    Bridge:    w_a1 — w_b1 with weight 0.1 — should be cut first by the
               progressive edge-cutting strategy.

    Use this fixture for community detection and traversal tests.
    """
    return make_graph([
        ("w_a1", "w_a2", 2.0),
        ("w_a1", "w_a3", 1.8),
        ("w_a2", "w_a3", 1.9),
        ("w_b1", "w_b2", 2.1),
        ("w_b1", "w_b3", 1.7),
        ("w_b2", "w_b3", 2.0),
        ("w_a1", "w_b1", 0.1),
    ])


# ── Infrastructure mocks ───────────────────────────────────────────────────────


@pytest.fixture
def mock_storage(monkeypatch):
    """Moto-backed S3Storage for offline testing.

    Resets the module-level singleton before the test so a fresh boto3 client
    is created inside the moto mock context. The singleton is restored to its
    pre-test value automatically by monkeypatch after the test completes.

    Yields:
        A fully initialized S3Storage backed by moto (no real MinIO required).
    """
    import src.shared.storage as storage_mod
    from moto import mock_aws

    monkeypatch.setattr(storage_mod, "_instance", None)
    # Override the endpoint so boto3 uses the default AWS endpoint
    # intercepted by moto instead of the MinIO URL.
    monkeypatch.setattr(storage_mod, "S3_ENDPOINT_URL", None)

    with mock_aws():
        yield storage_mod.get_storage()


@pytest.fixture
def mock_cache(monkeypatch):
    """Fakeredis-backed RedisCache for offline testing.

    Bypasses RedisCache.__init__ (which connects to a real Redis server) and
    injects a FakeRedis client directly. The singleton is restored automatically
    by monkeypatch after the test completes.

    Yields:
        A RedisCache instance whose internal client is a FakeRedis instance.
    """
    import fakeredis
    import src.shared.cache as cache_mod

    cache = cache_mod.RedisCache.__new__(cache_mod.RedisCache)
    cache._client = fakeredis.FakeRedis()

    monkeypatch.setattr(cache_mod, "_instance", cache)
    yield cache
