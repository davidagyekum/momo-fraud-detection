from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask

from momo_fdvs import create_app


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Flask]:
    monkeypatch.setenv(
        "DATABASE_URL",
        os.getenv(
            "P02_TEST_DATABASE_URL",
            "postgresql+psycopg://momo_fdvs:momo_fdvs_local_only@localhost:5432/momo_fdvs_test",
        ),
    )
    monkeypatch.setenv("LOCAL_PRIVATE_STORAGE_ROOT", str(tmp_path / "private-storage"))
    monkeypatch.setenv("APP_VERSION", "0.1.0-test")
    application = create_app("testing")
    yield application
