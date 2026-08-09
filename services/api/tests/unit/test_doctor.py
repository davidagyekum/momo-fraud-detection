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


def test_mobile_runtime_requires_pinned_node(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "REPO_ROOT", REPO_ROOT)

    status, detail = doctor.javascript_runtime_status("Node.js", True, "v22.11.0")

    assert status == "FAIL"
    assert doctor.EXPECTED_NODE_VERSION in detail


def test_mobile_runtime_accepts_pinned_npm(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "REPO_ROOT", REPO_ROOT)

    assert doctor.javascript_runtime_status("npm", True, "10.9.0") == (
        "PASS",
        "10.9.0",
    )
