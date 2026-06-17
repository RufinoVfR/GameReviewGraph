"""S3 storage backend for pipeline artifacts (MinIO-compatible).

Provides a single ``S3Storage`` class used by ``AbstractFilter`` to read and
write JSON and text artifacts. All objects are stored under the ``pipeline/``
prefix inside the configured bucket.

Usage is mediated through the module-level ``get_storage()`` factory, which
returns a lazily initialized singleton. Concrete filters never import this
module directly — ``AbstractFilter`` calls it internally.
"""

import json
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    S3_BUCKET,
    S3_ENDPOINT_URL,
)

_PREFIX = "pipeline"
_instance: "S3Storage | None" = None


def get_storage() -> "S3Storage":
    """Return the module-level S3Storage singleton, creating it on first call.

    Returns:
        Shared ``S3Storage`` instance.
    """
    global _instance
    if _instance is None:
        _instance = S3Storage()
    return _instance


class S3Storage:
    """Read and write pipeline artifacts in an S3-compatible store (MinIO).

    All objects are placed under the ``pipeline/`` prefix:
    e.g. ``pipeline/word_graph.json``, ``pipeline/report.txt``.

    The target bucket is created automatically on first use if it does not
    already exist.
    """

    def __init__(self) -> None:
        """Initialize the boto3 client and ensure the bucket exists."""
        self._client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
        self._bucket = S3_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """Create the S3 bucket if it does not already exist."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def _key(self, name: str) -> str:
        """Return the full S3 object key for an artifact name.

        Args:
            name: Artifact filename, e.g. ``"word_graph.json"``.

        Returns:
            Full key with prefix, e.g. ``"pipeline/word_graph.json"``.
        """
        return f"{_PREFIX}/{name}"

    def read_json(self, name: str) -> Any:
        """Download and deserialize a JSON artifact from S3.

        Args:
            name: Artifact filename, e.g. ``"word_graph.json"``.

        Returns:
            Deserialized Python object.
        """
        response = self._client.get_object(Bucket=self._bucket, Key=self._key(name))
        return json.loads(response["Body"].read().decode("utf-8"))

    def write_json(self, name: str, data: Any) -> None:
        """Serialize and upload a Python object as a JSON artifact.

        Args:
            name: Artifact filename, e.g. ``"word_graph.json"``.
            data: Python object to serialize.
        """
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._client.put_object(
            Bucket=self._bucket,
            Key=self._key(name),
            Body=body,
            ContentType="application/json",
        )

    def write_text(self, name: str, text: str) -> None:
        """Upload a plain-text artifact (e.g. ``report.txt``).

        Args:
            name: Artifact filename, e.g. ``"report.txt"``.
            text: UTF-8 text content to upload.
        """
        self._client.put_object(
            Bucket=self._bucket,
            Key=self._key(name),
            Body=text.encode("utf-8"),
            ContentType="text/plain; charset=utf-8",
        )

    def exists(self, name: str) -> bool:
        """Check whether an artifact exists in the bucket.

        Args:
            name: Artifact filename.

        Returns:
            ``True`` if the object exists, ``False`` otherwise.
        """
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._key(name))
            return True
        except ClientError:
            return False

    def delete(self, name: str) -> None:
        """Remove an artifact from the bucket.

        Args:
            name: Artifact filename to delete.
        """
        self._client.delete_object(Bucket=self._bucket, Key=self._key(name))
