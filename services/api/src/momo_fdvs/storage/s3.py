"""S3-compatible private object storage."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.exceptions import ClientError

from momo_fdvs.storage.base import ObjectStorage, StoredObject, sha256_bytes


class S3PrivateStorage(ObjectStorage):
    def __init__(
        self,
        *,
        bucket: str,
        prefix: str,
        region: str | None,
        endpoint_url: str | None,
        access_key_id: str | None,
        secret_access_key: str | None,
        encryption: str,
        signed_url_ttl_seconds: int,
        client: Any | None = None,
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.encryption = encryption
        self.signed_url_ttl_seconds = signed_url_ttl_seconds
        self.client = client or boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def _key(self, key: str) -> str:
        if key.startswith("/") or ".." in key.split("/"):
            raise ValueError("storage key is invalid")
        return f"{self.prefix}/{key}" if self.prefix else key

    def put_bytes(
        self, key: str, content: bytes, content_type: str, metadata: dict[str, str] | None = None
    ) -> StoredObject:
        digest = sha256_bytes(content)
        object_metadata = {"sha256": digest, **(metadata or {})}
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._key(key),
            Body=content,
            ContentType=content_type,
            Metadata=object_metadata,
            ServerSideEncryption=self.encryption,
        )
        return StoredObject(key, digest, len(content), content_type, object_metadata)

    def read_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=self._key(key))
        return bytes(response["Body"].read())

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(key))
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return False
            raise
        return True

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._key(key))

    def presigned_private_read(self, key: str) -> str:
        """Issue a short-lived read only after a caller has completed policy checks."""
        return str(
            self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": self._key(key)},
                ExpiresIn=self.signed_url_ttl_seconds,
            )
        )
