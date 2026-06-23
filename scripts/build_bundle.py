"""Build compact visualization bundles for the frontend.

Args:
    None.

Returns:
    None.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from src.config import S3_KEYS
from src.shared.graph.ops import add_node, deserialize_graph, iter_edges, new_graph, serialize_graph
from src.shared.storage import get_storage
from src.shared.tree import COMMENT_PREFIX, SENTENCE_PREFIX, WORD_PREFIX, iter_comments, iter_words

# Frontend-only artifact: built by the UI tooling, never produced by the
# pipeline, so it has no entry in ``S3_KEYS``.
_INVERTED_INDEX = "inverted_index.json"

# An artifact reader resolves an artifact filename to its parsed JSON payload,
# or ``None`` when the artifact is unavailable. This indirection lets the same
# assembly logic read either from MinIO (default) or a local directory (tests).
ArtifactReader = Callable[[str], Any]


def _read_json(path: Path) -> Any:
    """Read a JSON file from disk.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON content.
    """
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    """Write a JSON file to disk.

    Args:
        path: Target file path.

    Returns:
        None.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _frontend_comment_id(raw_id: Any) -> str:
    """Convert a raw comment identifier to the frontend convention.

    Args:
        raw_id: Raw identifier from the pipeline.

    Returns:
        Frontend comment id.
    """
    return f"comment-{raw_id}"


def _frontend_sentence_id(raw_index: Any) -> str:
    """Convert a raw sentence index to the frontend convention.

    Args:
        raw_index: Raw sentence index from tree.json.

    Returns:
        Frontend sentence id.
    """
    return f"sentence-{raw_index}"


def _frontend_word_id(raw_value: Any) -> str:
    """Convert a raw token to the frontend convention.

    Args:
        raw_value: Raw token from tree.json or a graph node key.

    Returns:
        Frontend word id.
    """
    return f"word-{raw_value}"


def _normalize_node_id(node_key: str) -> str:
    """Convert a pipeline node key to the frontend id convention.

    Args:
        node_key: Raw node key such as ``c_3`` or ``w_travamento``.

    Returns:
        Frontend node id.
    """
    if node_key.startswith(COMMENT_PREFIX):
        return _frontend_comment_id(node_key.removeprefix(COMMENT_PREFIX))
    if node_key.startswith(SENTENCE_PREFIX):
        return _frontend_sentence_id(node_key.removeprefix(SENTENCE_PREFIX))
    if node_key.startswith(WORD_PREFIX):
        return _frontend_word_id(node_key.removeprefix(WORD_PREFIX))
    return node_key


def _derive_tree_data(tree: dict[str, Any] | None) -> tuple[dict[str, list[str]], dict[str, list[str]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive containment maps and visible records from tree.json.

    Args:
        tree: Parsed tree.json payload, or None when unavailable.

    Returns:
        comment-to-sentence map, sentence-to-word map, sentence records, and
        word records.
    """
    if not tree:
        return {}, {}, [], []

    comment_to_sentences: dict[str, list[str]] = {}
    sentence_to_words: dict[str, list[str]] = {}
    sentence_records: list[dict[str, Any]] = []
    word_frequency: dict[str, int] = {}
    word_order: list[str] = []

    for comment in iter_comments(tree):
        comment_id = _frontend_comment_id(comment["id"])
        sentence_ids: list[str] = []
        for sentence in comment.get("children", []):
            sentence_id = _frontend_sentence_id(sentence["index"])
            sentence_ids.append(sentence_id)
            tokens = [word["value"] for word in iter_words(sentence)]
            word_ids = [_frontend_word_id(token) for token in tokens]
            sentence_to_words[sentence_id] = word_ids
            sentence_records.append(
                {
                    "id": sentence_id,
                    "label": " ".join(tokens[:4]) if tokens else f"sentence {sentence['index']}",
                    "wordIds": word_ids,
                }
            )
            for token in tokens:
                word_id = _frontend_word_id(token)
                word_frequency[word_id] = word_frequency.get(word_id, 0) + 1
                if word_id not in word_order:
                    word_order.append(word_id)
        comment_to_sentences[comment_id] = sentence_ids

    word_records = [
        {
            "id": word_id,
            "label": word_id.removeprefix("word-"),
            "frequency": word_frequency[word_id],
        }
        for word_id in word_order
    ]

    return comment_to_sentences, sentence_to_words, sentence_records, word_records


def _build_comment_records(
    comments: list[dict[str, Any]],
    comment_to_sentences: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Build frontend comment records from raw comments and tree containment.

    The frontend expects each comment keyed by its frontend id (``comment-N``)
    and carrying its child sentence ids, so it can be matched against the
    community ``commentIds`` and expanded on zoom. The raw pipeline comments
    (integer id, no sentence links) are not usable as-is.

    Args:
        comments: Raw comments from comments.json.
        comment_to_sentences: Map of frontend comment id to its sentence ids,
            derived from tree.json.

    Returns:
        Frontend comment records ``{id, label, text, topic, sentenceIds}``.
    """
    records: list[dict[str, Any]] = []
    for item in comments:
        if not isinstance(item, dict) or "id" not in item:
            continue
        comment_id = _frontend_comment_id(item["id"])
        records.append(
            {
                "id": comment_id,
                "label": f"Comentário {item['id']}",
                "text": item.get("text", ""),
                "topic": item.get("topic", ""),
                "sentenceIds": comment_to_sentences.get(comment_id, []),
            }
        )
    return records


def _build_text_store(comments: list[dict[str, Any]]) -> dict[str, str]:
    """Build a frontend-friendly id -> text store from raw comments.

    Args:
        comments: Raw comments from comments.json.

    Returns:
        Mapping of frontend comment ids to raw text.
    """
    return {
        _frontend_comment_id(item["id"]): item["text"]
        for item in comments
        if isinstance(item, dict) and "id" in item and "text" in item
    }


def _derive_communities(raw_communities: Any, comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert raw pipeline communities into frontend records.

    Args:
        raw_communities: Raw communities payload from communities.json.
        comments: Raw comments from comments.json.

    Returns:
        Frontend community records.
    """
    topic_by_comment = {
        _frontend_comment_id(item["id"]): item.get("topic", "geral")
        for item in comments
        if isinstance(item, dict) and "id" in item
    }

    if isinstance(raw_communities, dict):
        iterable = list(raw_communities.items())
    elif isinstance(raw_communities, list):
        iterable = [(str(index), community) for index, community in enumerate(raw_communities)]
    else:
        iterable = []

    records: list[dict[str, Any]] = []
    for community_id, members in iterable:
        comment_ids = [
            _normalize_node_id(member)
            for member in members
            if isinstance(member, str) and member.startswith(COMMENT_PREFIX)
        ] if isinstance(members, list) else []
        topic_counts: dict[str, int] = {}
        for comment_id in comment_ids:
            topic = topic_by_comment.get(comment_id)
            if topic:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        dominant_topic = max(topic_counts, key=topic_counts.get) if topic_counts else "geral"
        records.append(
            {
                "id": f"community-{community_id}",
                "label": dominant_topic.title() if dominant_topic != "geral" else f"Comunidade {community_id}",
                "topic": dominant_topic,
                "size": len(comment_ids),
                "commentIds": comment_ids,
            }
        )
    return records


def _copy_or_empty_graph(raw_graph: Any, prefix: str) -> dict[str, Any]:
    """Extract a frontend graph bundle from a raw serialized Graph.

    Args:
        raw_graph: Raw serialized graph dict, or ``None``.
        prefix: Node prefix to preserve while inducing the subgraph.

    Returns:
        Serialized graph bundle using the frontend id convention.
    """
    if not raw_graph:
        return {"nodes": [], "index": {}, "matrix": []}

    graph = deserialize_graph(raw_graph)
    output = new_graph()

    for node in graph.nodes:
        if isinstance(node, str) and node.startswith(prefix):
            add_node(output, _normalize_node_id(node))

    for left, right, weight in iter_edges(graph):
        if not left.startswith(prefix) or not right.startswith(prefix):
            continue
        add_node(output, _normalize_node_id(left))
        add_node(output, _normalize_node_id(right))
        i = output.index[_normalize_node_id(left)]
        j = output.index[_normalize_node_id(right)]
        output.matrix[i][j] = weight
        output.matrix[j][i] = weight

    return serialize_graph(output)


def _graph_to_neighbors(graph_bundle: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Convert a serialized graph bundle into adjacency lists.

    Args:
        graph_bundle: Serialized graph bundle produced by ``_copy_or_empty_graph``.

    Returns:
        Mapping ``node_id -> [{id, weight}, ...]``.
    """
    neighbors: dict[str, list[dict[str, Any]]] = {}
    nodes = graph_bundle.get("nodes", [])
    matrix = graph_bundle.get("matrix", [])
    for i, source in enumerate(nodes):
        row = matrix[i] if i < len(matrix) else []
        entries: list[dict[str, Any]] = []
        for j, target in enumerate(nodes):
            if i == j or j >= len(row):
                continue
            weight = row[j]
            if weight != 0.0:
                entries.append({"id": target, "weight": weight})
        neighbors[source] = entries
    return neighbors


def _derive_report(report: Any) -> dict[str, Any] | None:
    """Reshape the pipeline report.json into the frontend's camelCase contract.

    The pipeline emits the final report (Filter 9) in snake_case with raw node
    keys (``c_3``); the frontend expects camelCase fields and ``comment-3`` ids,
    matching every other bundle. This adapter performs that translation so the
    report page can consume it without any per-field remapping.

    Args:
        report: Parsed report.json payload, or ``None`` when unavailable.

    Returns:
        The frontend-shaped report dict, or ``None`` when no report exists.
    """
    if not report:
        return None

    def method(item: dict[str, Any]) -> dict[str, Any]:
        stats = item.get("stats", {})
        return {
            "id": item["id"],
            "label": item["label"],
            "modularityQ": item["modularity_q"],
            "stats": {
                "nCommunities": stats.get("n_communities", 0),
                "sizeMin": stats.get("size_min", 0),
                "sizeMax": stats.get("size_max", 0),
                "singletons": stats.get("singletons", 0),
                "nComments": stats.get("n_comments", 0),
            },
            "communities": [
                {
                    "id": community["id"],
                    "topic": community.get("topic"),
                    "centralTerms": community.get("central_terms", []),
                    "comments": [_normalize_node_id(node) for node in community.get("comments", [])],
                }
                for community in item.get("communities", [])
            ],
        }

    return {
        "k": report.get("k", 0),
        "nComments": report.get("n_comments", 0),
        "methods": [method(item) for item in report.get("methods", [])],
        "comparison": [
            {
                "id": row["id"],
                "label": row["label"],
                "modularityQ": row["modularity_q"],
                "nCommunities": row["n_communities"],
                "sizeMin": row["size_min"],
                "sizeMax": row["size_max"],
                "singletons": row["singletons"],
            }
            for row in report.get("comparison", [])
        ],
    }


def _local_reader(input_dir: Path) -> ArtifactReader:
    """Build an artifact reader backed by a local directory.

    Args:
        input_dir: Directory containing pipeline JSON artifacts.

    Returns:
        Reader that resolves artifact filenames to parsed JSON, or ``None``.
    """

    def read(filename: str) -> Any:
        path = input_dir / filename
        return _read_json(path) if path.exists() else None

    return read


def _storage_reader() -> ArtifactReader:
    """Build an artifact reader backed by the shared MinIO storage adapter.

    Reading goes through ``get_storage()`` (the same ``S3Storage`` used by the
    pipeline) so the bundle builder never talks to boto3 or S3 keys directly.

    Returns:
        Reader that resolves artifact filenames to parsed JSON, or ``None``.
    """
    storage = get_storage()

    def read(filename: str) -> Any:
        return storage.read_json(filename) if storage.exists(filename) else None

    return read


def build_bundle(input_dir: Path, output_dir: Path) -> None:
    """Build frontend bundles from pipeline artifacts in a local directory.

    Thin wrapper around :func:`assemble_bundle` for callers (and tests) that
    stage the pipeline artifacts on disk instead of in MinIO.

    Args:
        input_dir: Directory containing pipeline JSON artifacts.
        output_dir: Directory where frontend bundles will be written.

    Returns:
        None.
    """
    assemble_bundle(_local_reader(input_dir), output_dir)


def assemble_bundle(read_artifact: ArtifactReader, output_dir: Path) -> None:
    """Build frontend bundles from pipeline artifacts.

    Args:
        read_artifact: Reader resolving an artifact filename to parsed JSON,
            or ``None`` when the artifact is unavailable.
        output_dir: Directory where frontend bundles will be written.

    Returns:
        None.
    """
    comments = read_artifact(S3_KEYS["raw"]) or []
    raw_communities = read_artifact(S3_KEYS["communities"]) or {}
    tree = read_artifact(S3_KEYS["tree"])
    final_graph = read_artifact(S3_KEYS["final_graph"])
    word_graph = read_artifact(S3_KEYS["word_graph"])
    sentence_graph = read_artifact(S3_KEYS["sentence_graph"])
    inverted_index = read_artifact(_INVERTED_INDEX) or {}
    report = _derive_report(read_artifact(S3_KEYS["report_json"]))

    comment_to_sentences, sentence_to_words, sentences, words = _derive_tree_data(tree)
    communities = _derive_communities(raw_communities, comments)
    comment_records = _build_comment_records(comments, comment_to_sentences)
    text_store = _build_text_store(comments)

    word_graph_bundle = _copy_or_empty_graph(final_graph or word_graph, WORD_PREFIX)
    sentence_neighbors_bundle = _copy_or_empty_graph(final_graph or sentence_graph, SENTENCE_PREFIX)
    sentence_neighbors = _graph_to_neighbors(sentence_neighbors_bundle)

    topics = sorted({item.get("topic", "") for item in comments if isinstance(item, dict) and item.get("topic")})
    meta = {
        "version": "bundle-0.1",
        "generatedAt": "2026-06-22T00:00:00.000Z",
        "counts": {
            "communities": len(communities),
            "comments": len(comments),
            "sentences": len(sentences),
            "words": len(words),
        },
        "topics": topics,
    }

    output = output_dir / "bundle"
    _write_json(output / "meta.json", meta)
    _write_json(output / "communities.json", communities)
    _write_json(output / "comments.json", comment_records)
    _write_json(output / "sentences.json", sentences)
    _write_json(output / "words.json", words)
    _write_json(output / "word_graph.json", word_graph_bundle)
    _write_json(output / "sentence_neighbors.json", sentence_neighbors)
    _write_json(
        output / "containment.json",
        {"commentToSentences": comment_to_sentences, "sentenceToWords": sentence_to_words},
    )
    _write_json(output / "inverted_index.json", inverted_index)
    _write_json(output / "text_store.json", text_store)
    if report is not None:
        _write_json(output / "report.json", report)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Args:
        None.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(description="Build frontend visualization bundles.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Read artifacts from this local directory instead of MinIO storage.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("frontend/public"))
    return parser.parse_args()


def main() -> None:
    """Run the bundle builder.

    Reads pipeline artifacts from MinIO via the shared storage adapter by
    default; ``--input-dir`` switches to a local directory instead.

    Args:
        None.

    Returns:
        None.
    """
    args = parse_args()
    read_artifact = _local_reader(args.input_dir) if args.input_dir else _storage_reader()
    assemble_bundle(read_artifact, args.output_dir)


if __name__ == "__main__":
    main()
