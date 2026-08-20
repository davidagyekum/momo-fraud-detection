"""Regression tests for the live release verifier."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

verify_release = importlib.import_module("verify_release")


def test_release_verifier_tracks_the_migration_head() -> None:
    migration_heads = [
        path.stem.split("_", maxsplit=2)[0] + "_" + path.stem.split("_", maxsplit=2)[1]
        for path in (REPO_ROOT / "services" / "api" / "migrations" / "versions").glob("*.py")
        if "down_revision: str | None = None" not in path.read_text(encoding="utf-8")
    ]

    assert max(migration_heads) == verify_release.EXPECTED_MIGRATION
