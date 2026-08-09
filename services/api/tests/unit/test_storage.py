from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

from momo_fdvs.storage.base import (
    DeletionDecision,
    delete_with_retention_guard,
    generated_key,
)
from momo_fdvs.storage.local import LocalPrivateStorage
from momo_fdvs.storage.s3 import S3PrivateStorage


def test_local_private_storage_hash_read_and_guarded_delete(tmp_path: Path) -> None:
    storage = LocalPrivateStorage(tmp_path / "not-public")
    key = generated_key("receipts/user-id/transaction-id/original", "png")
    stored = storage.put_bytes(key, b"private-receipt", "image/png")

    assert stored.sha256 == "72119fb5980e98a7a00945e1abe9746cc832f1f746d6a80888a2afe6abdd8a67"
    assert storage.read_bytes(key) == b"private-receipt"
    assert storage.exists(key)
    with pytest.raises(PermissionError):
        delete_with_retention_guard(storage, key, DeletionDecision(False, "open case"))
    delete_with_retention_guard(storage, key, DeletionDecision(True, "retention expired"))
    assert not storage.exists(key)


@pytest.mark.parametrize("key", ["../escape", "/absolute", "safe/../../escape"])
def test_local_storage_rejects_path_escape(tmp_path: Path, key: str) -> None:
    storage = LocalPrivateStorage(tmp_path / "private")
    with pytest.raises(ValueError):
        storage.put_bytes(key, b"x", "application/octet-stream")


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, Any]] = {}

    def put_object(self, **kwargs: Any) -> None:
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        value = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {"Body": io.BytesIO(value["Body"])}

    def head_object(self, **kwargs: Any) -> dict[str, Any]:
        self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {}

    def delete_object(self, **kwargs: Any) -> None:
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)

    def generate_presigned_url(self, *_args: Any, **_kwargs: Any) -> str:
        return "https://private.example/temporary"


def test_s3_adapter_keeps_private_prefix_hash_and_encryption() -> None:
    client = FakeS3Client()
    storage = S3PrivateStorage(
        bucket="private-bucket",
        prefix="momo-fdvs",
        region=None,
        endpoint_url=None,
        access_key_id=None,
        secret_access_key=None,
        encryption="AES256",
        signed_url_ttl_seconds=300,
        client=client,
    )
    stored = storage.put_bytes("receipts/id.png", b"secret", "image/png")
    uploaded = client.objects[("private-bucket", "momo-fdvs/receipts/id.png")]

    assert stored.sha256 == "2bb80d537b1da3e38bd30361aa855686bde0eacd7162fef6a25fe97bf527a25b"
    assert uploaded["ServerSideEncryption"] == "AES256"
    assert "ACL" not in uploaded
    assert storage.read_bytes(stored.key) == b"secret"
    assert storage.presigned_private_read(stored.key).startswith("https://private.example/")
