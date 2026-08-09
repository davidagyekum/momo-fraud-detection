"""Filesystem-backed private storage outside the repository/static tree."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from momo_fdvs.storage.base import ObjectStorage, StoredObject, sha256_bytes


class LocalPrivateStorage(ObjectStorage):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if candidate == self.root or self.root not in candidate.parents:
            raise ValueError("storage key escapes the private root")
        return candidate

    def put_bytes(
        self, key: str, content: bytes, content_type: str, metadata: dict[str, str] | None = None
    ) -> StoredObject:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return StoredObject(key, sha256_bytes(content), len(content), content_type, metadata or {})

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
