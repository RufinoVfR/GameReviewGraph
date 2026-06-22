"""Tests for the frontend visualization bundle builder."""

import json
from pathlib import Path

from scripts.build_bundle import build_bundle


def test_build_bundle_writes_expected_files(tmp_path):
    """Build bundles from a minimal pipeline input directory.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        None.
    """
    input_dir = tmp_path / "pipeline"
    output_dir = tmp_path / "frontend-public"
    input_dir.mkdir()

    (input_dir / "comments.json").write_text(
        json.dumps(
            [
                {"id": 1, "topic": "desempenho", "text": "O jogo trava muito."},
                {"id": 2, "topic": "narrativa", "text": "A história é envolvente."},
            ]
        ),
        encoding="utf-8",
    )
    (input_dir / "communities.json").write_text("[]", encoding="utf-8")
    (input_dir / "word_graph.json").write_text(
        json.dumps({"nodes": ["w_a"], "index": {"w_a": 0}, "matrix": [[0.0]]}),
        encoding="utf-8",
    )
    (input_dir / "sentence_neighbors.json").write_text("{}", encoding="utf-8")
    (input_dir / "containment.json").write_text(
        json.dumps({"commentToSentences": {}, "sentenceToWords": {}}),
        encoding="utf-8",
    )
    (input_dir / "inverted_index.json").write_text("{}", encoding="utf-8")

    build_bundle(input_dir, output_dir)

    bundle_dir = output_dir / "bundle"
    assert (bundle_dir / "meta.json").exists()
    assert (bundle_dir / "communities.json").exists()
    assert (bundle_dir / "comments.json").exists()
    assert (bundle_dir / "word_graph.json").exists()
    assert (bundle_dir / "sentence_neighbors.json").exists()
    assert (bundle_dir / "containment.json").exists()
    assert (bundle_dir / "inverted_index.json").exists()
    assert (bundle_dir / "text_store.json").exists()

    meta = json.loads((bundle_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["counts"]["comments"] == 2
    assert meta["topics"] == ["desempenho", "narrativa"]

    text_store = json.loads((bundle_dir / "text_store.json").read_text(encoding="utf-8"))
    assert text_store == {
        "comment-1": "O jogo trava muito.",
        "comment-2": "A história é envolvente.",
    }

    comments = json.loads((bundle_dir / "comments.json").read_text(encoding="utf-8"))
    assert comments == [
        {
            "id": "comment-1",
            "label": "Comentário 1",
            "text": "O jogo trava muito.",
            "topic": "desempenho",
            "sentenceIds": [],
        },
        {
            "id": "comment-2",
            "label": "Comentário 2",
            "text": "A história é envolvente.",
            "topic": "narrativa",
            "sentenceIds": [],
        },
    ]
