"""Private object-storage contract and key generation."""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass(frozen=True)
class StoredObject:
    key: str
    sha256: str
    size_bytes: int
    content_type: str
    metadata: dict[str, str] = field(default_factory=dict)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def generated_key(namespace: str, suffix: str = "bin") -> str:
    """Generate a non-identifying server key under an approved namespace."""
    parts = PurePosixPath(namespace).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError("storage namespace must be a safe relative path")
    clean_suffix = suffix.lower().lstrip(".")
    if not clean_suffix.isalnum() or len(clean_suffix) > 10:
        raise ValueError("storage suffix is invalid")
    return str(PurePosixPath(*parts, f"{uuid.uuid4()}.{clean_suffix}"))


class ObjectStorage(ABC):
    @abstractmethod
    def put_bytes(
        self, key: str, content: bytes, content_type: str, metadata: dict[str, str] | None = None
    ) -> StoredObject: ...

    @abstractmethod
    def read_bytes(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


@dataclass(frozen=True)
class DeletionDecision:
    allowed: bool
    reason: str


def delete_with_retention_guard(
    storage: ObjectStorage, key: str, decision: DeletionDecision
) -> None:
    """Delete bytes only after the domain retention policy explicitly permits it."""
    if not decision.allowed or not decision.reason.strip():
        raise PermissionError("object deletion requires an approved retention decision")
    storage.delete(key)
