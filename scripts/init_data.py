"""Upload a raw comments dataset to MinIO before running the pipeline.

The pipeline's first filter always reads ``pipeline/comments.json`` from MinIO;
this script decides which local file populates it. Pass a path to choose the
dataset (defaults to ``data/comments.json``).

Run via:
    make init-data                               # uploads data/comments.json
    make init-data ARGS=data/comments_multi.json # uploads a different dataset
"""

import argparse
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT_URL, S3_KEYS

_DEFAULT_PATH = Path("data/comments.json")
_PREFIX = "pipeline"


def _get_client() -> boto3.client:
    """Create and return a boto3 S3 client pointed at MinIO.

    Returns:
        Configured boto3 S3 client.
    """
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def _ensure_bucket(client: boto3.client) -> None:
    """Create the S3 bucket if it does not already exist.

    Args:
        client: Configured boto3 S3 client.
    """
    try:
        client.head_bucket(Bucket=S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=S3_BUCKET)
        print(f"[init_data] Bucket '{S3_BUCKET}' created.")


def upload_raw_comments(client: boto3.client, source: Path) -> None:
    """Upload a local dataset to MinIO as pipeline/comments.json.

    The object key is always ``pipeline/comments.json`` (``S3_KEYS['raw']``), so
    the preprocessing filter's input contract is unchanged regardless of which
    local file is chosen.

    Args:
        client: Configured boto3 S3 client.
        source: Path to the local raw comments JSON file to upload.

    Raises:
        FileNotFoundError: If ``source`` does not exist locally.
        ValueError: If ``source`` is not valid JSON.
    """
    if not source.exists():
        raise FileNotFoundError(
            f"{source} not found. Pass a path to an existing raw comments JSON file, "
            "e.g. make init-data ARGS=data/comments.json."
        )

    body = source.read_bytes()
    try:
        json.loads(body)  # fail fast on a malformed dataset before uploading
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source} is not valid JSON: {exc}") from exc

    key = f"{_PREFIX}/{S3_KEYS['raw']}"
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    print(f"[init_data] Uploaded {source} → s3://{S3_BUCKET}/{key}")


def main() -> None:
    """Parse the dataset path and upload it to MinIO."""
    parser = argparse.ArgumentParser(prog="python -m scripts.init_data")
    parser.add_argument(
        "source",
        nargs="?",
        default=str(_DEFAULT_PATH),
        help="Path to the raw comments JSON file to upload (default: data/comments.json).",
    )
    args = parser.parse_args()

    client = _get_client()
    _ensure_bucket(client)
    upload_raw_comments(client, Path(args.source))
    print("[init_data] Done.")


if __name__ == "__main__":
    main()
