"""Shared pytest fixtures for GameReviewGraph test suite."""
import pytest


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
    """Pre-tokenized comments matching the output contract of preprocessing.py."""
    return [
        {"id": 1, "topic": "desempenho", "sentences": [["jogo", "trav", "atualizacao"]]},
        {"id": 2, "topic": "desempenho", "sentences": [["fps", "cai", "patch"]]},
        {"id": 3, "topic": "narrativa", "sentences": [["historia", "envolv", "personagem", "profundidad"]]},
        {"id": 4, "topic": "narrativa", "sentences": [["campanha", "principal", "narrativ", "excelent"]]},
    ]


@pytest.fixture
def small_word_graph() -> dict[str, dict[str, float]]:
    """Minimal word graph for testing sentence/comment graph builders."""
    return {
        "w_jogo":      {"w_trav": 1.0, "w_atualizacao": 0.5},
        "w_trav":      {"w_jogo": 1.0, "w_atualizacao": 1.0},
        "w_atualizacao": {"w_jogo": 0.5, "w_trav": 1.0},
        "w_fps":       {"w_cai": 1.0, "w_patch": 0.5},
        "w_cai":       {"w_fps": 1.0, "w_patch": 1.0},
        "w_patch":     {"w_fps": 0.5, "w_cai": 1.0},
    }
