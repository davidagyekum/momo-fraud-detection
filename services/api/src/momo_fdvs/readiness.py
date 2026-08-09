"""Dependency probes used by the public readiness endpoint."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import current_app
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from momo_fdvs.extensions import db


@dataclass(frozen=True)
class ReadinessResult:
    """Safe dependency matrix without credentials, paths or stack details."""

    ready: bool
    analysis_available: bool
    full_analysis_available: bool
    components: dict[str, dict[str, str]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "components": self.components,
            "analysis_available": self.analysis_available,
            "full_analysis_available": self.full_analysis_available,
        }


def _database() -> dict[str, str]:
    try:
        db.session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return {"status": "unavailable", "reason": "connection_failed"}
    return {"status": "ready"}


def _storage(root: Path) -> dict[str, str]:
    try:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="readiness-", dir=root, delete=True) as probe:
            probe.write(b"ready")
            probe.flush()
    except OSError:
        return {"status": "unavailable", "reason": "probe_failed"}
    return {"status": "ready"}


def _tesseract(command: str) -> dict[str, str]:
    executable = shutil.which(command)
    if executable is None:
        return {"status": "degraded", "reason": "not_installed"}
    try:
        result = subprocess.run(  # noqa: S603 - resolved executable, no shell or user arguments
            [executable, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"status": "degraded", "reason": "probe_failed"}
    first_line = (result.stdout or result.stderr).splitlines()
    safe_version = first_line[0].strip().split(maxsplit=1)[-1] if first_line else "unknown"
    if result.returncode != 0:
        return {"status": "degraded", "reason": "probe_failed"}
    return {"status": "ready", "version": safe_version[:32]}


def probe_readiness() -> ReadinessResult:
    database = _database()
    storage = _storage(current_app.config["LOCAL_PRIVATE_STORAGE_ROOT"])
    tesseract = _tesseract(current_app.config["TESSERACT_CMD"])
    components = {
        "database": database,
        "storage": storage,
        "tesseract": tesseract,
        "structured_model": {"status": "degraded", "reason": "not_activated"},
        "image_model": {"status": "degraded", "reason": "not_activated"},
    }
    core_ready = database["status"] == "ready" and storage["status"] == "ready"
    analysis_available = core_ready and tesseract["status"] == "ready"
    return ReadinessResult(
        ready=core_ready,
        analysis_available=analysis_available,
        full_analysis_available=False,
        components=components,
    )
