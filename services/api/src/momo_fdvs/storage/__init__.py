"""Configured private object-storage adapters."""

from __future__ import annotations

from flask import Flask

from momo_fdvs.storage.base import ObjectStorage
from momo_fdvs.storage.local import LocalPrivateStorage
from momo_fdvs.storage.s3 import S3PrivateStorage


def create_storage(app: Flask) -> ObjectStorage:
    """Create the configured private adapter without exposing a public path."""
    if app.config["STORAGE_ADAPTER"] == "local":
        return LocalPrivateStorage(app.config["LOCAL_PRIVATE_STORAGE_ROOT"])
    return S3PrivateStorage(
        bucket=app.config["S3_BUCKET"],
        prefix=app.config["S3_PREFIX"],
        region=app.config["S3_REGION"],
        endpoint_url=app.config["S3_ENDPOINT_URL"],
        access_key_id=app.config["S3_ACCESS_KEY_ID"],
        secret_access_key=app.config["S3_SECRET_ACCESS_KEY"],
        encryption=app.config["S3_SERVER_SIDE_ENCRYPTION"],
        signed_url_ttl_seconds=app.config["SIGNED_URL_TTL_SECONDS"],
    )


__all__ = ["LocalPrivateStorage", "ObjectStorage", "S3PrivateStorage", "create_storage"]
