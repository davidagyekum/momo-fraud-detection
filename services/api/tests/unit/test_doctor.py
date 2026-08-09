"""Tests for repository toolchain discovery."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

doctor = importlib.import_module("doctor")


def test_resolve_docker_from_per_user_windows_install(tmp_path, monkeypatch) -> None:
    docker_executable = tmp_path / "Programs" / "DockerDesktop" / "resources" / "bin" / "docker.exe"
    docker_executable.parent.mkdir(parents=True)
    docker_executable.touch()

    monkeypatch.setattr(doctor.platform, "system", lambda: "Windows")
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("ProgramFiles", raising=False)

    assert doctor.resolve_executable("docker") == str(docker_executable)


def test_resolve_unknown_command_without_fallback(monkeypatch) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _name: None)

    assert doctor.resolve_executable("unknown-command") is None
