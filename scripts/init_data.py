"""Upload data/comments.json to MinIO before running the pipeline.

Run via: make init-data
"""

import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from src.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET, S3_ENDPOINT_URL, S3_KEYS

_RAW_PATH = Path("data/comments.json")
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


def upload_raw_comments(client: boto3.client) -> None:
    """Upload data/comments.json to MinIO as pipeline/comments.json.

    Args:
        client: Configured boto3 S3 client.

    Raises:
        FileNotFoundError: If data/comments.json does not exist locally.
    """
    if not _RAW_PATH.exists():
        raise FileNotFoundError(
            f"{_RAW_PATH} not found. "
            "Place the raw comments file at data/comments.json before running init-data."
        )

    key = f"{_PREFIX}/{S3_KEYS['raw']}"
    body = _RAW_PATH.read_bytes()
    client.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json",
    )
    print(f"[init_data] Uploaded {_RAW_PATH} → s3://{S3_BUCKET}/{key}")


if __name__ == "__main__":
    client = _get_client()
    _ensure_bucket(client)
    upload_raw_comments(client)
    print("[init_data] Done.")
