#!/usr/bin/env python3
"""Report the MoMo-FDVS development toolchain without installing software."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from _common import REPO_ROOT, git_command


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    required_for: str


def resolve_executable(name: str) -> str | None:
    """Resolve a command, including supported per-user Windows installs."""
    executable = shutil.which(name)
    if executable is not None:
        return executable

    if platform.system() != "Windows" or name.lower() not in {"docker", "docker.exe"}:
        return None

    candidates: list[Path] = []
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(
            Path(local_app_data)
            / "Programs"
            / "DockerDesktop"
            / "resources"
            / "bin"
            / "docker.exe"
        )
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(
            Path(program_files)
            / "Docker"
            / "Docker"
            / "resources"
            / "bin"
            / "docker.exe"
        )
    return next(
        (str(candidate) for candidate in candidates if candidate.is_file()), None
    )


def command_version(name: str, command: Sequence[str]) -> tuple[bool, str]:
    executable = resolve_executable(command[0])
    if executable is None:
        return False, "not found"
    argv = list(command)
    argv[0] = executable
    try:
        result = subprocess.run(
            argv,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"unable to run: {exc}"
    output = (result.stdout or result.stderr).strip().splitlines()
    detail = output[0] if output else f"exit code {result.returncode}"
    return result.returncode == 0, detail


def collect_checks() -> list[Check]:
    python_ok = sys.version_info[:2] == (3, 12)
    checks = [
        Check(
            "Python",
            "PASS" if python_ok else "FAIL",
            platform.python_version()
            + (
                ""
                if python_ok
                else " (Python 3.12 is required; use py -3.12 on Windows)"
            ),
            "P00+",
        )
    ]

    definitions = [
        ("Git", git_command("--version"), "P00+", True),
        ("Node.js", ["node", "--version"], "P04/P05", False),
        (
            "npm",
            ["npm.cmd" if platform.system() == "Windows" else "npm", "--version"],
            "P04/P05",
            False,
        ),
        ("Docker", ["docker", "--version"], "P01", False),
        ("Tesseract", ["tesseract", "--version"], "P07", False),
        ("PostgreSQL CLI", ["psql", "--version"], "optional local diagnostics", False),
    ]
    for name, command, required_for, p00_required in definitions:
        ok, detail = command_version(name, command)
        if ok:
            status = "PASS"
        elif p00_required:
            status = "FAIL"
        else:
            status = "MISSING"
        checks.append(Check(name, status, detail, required_for))

    checks.append(
        Check(
            "Repository root",
            "PASS" if (REPO_ROOT / "AGENTS.md").is_file() else "FAIL",
            str(REPO_ROOT),
            "P00+",
        )
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    args = parser.parse_args()
    checks = collect_checks()

    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        print("MoMo-FDVS toolchain doctor")
        print(f"Platform: {platform.platform()}")
        for check in checks:
            print(
                f"[{check.status:7}] {check.name}: {check.detail} (needed: {check.required_for})"
            )

    failures = [check for check in checks if check.status == "FAIL"]
    if failures:
        print(f"Doctor result: FAIL ({len(failures)} P00 requirement(s) missing)")
        return 1

    missing = [check for check in checks if check.status == "MISSING"]
    print(
        f"Doctor result: PASS for P00; {len(missing)} later-phase tool(s) not installed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
