#!/usr/bin/env python3
"""Orchestrate honest repository verification for the implemented project sections."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from _common import REPO_ROOT, display_command


@dataclass(frozen=True)
class Section:
    name: str
    marker: Path
    command: tuple[str, ...] | None


SECTIONS = {
    "backend": Section(
        "backend",
        Path("services/api/pyproject.toml"),
        (sys.executable, "scripts/verify_backend.py"),
    ),
    "admin": Section(
        "admin",
        Path("apps/admin/package.json"),
        (sys.executable, "scripts/verify_admin.py"),
    ),
    "mobile": Section(
        "mobile",
        Path("apps/mobile/package.json"),
        (sys.executable, "scripts/verify_mobile.py"),
    ),
    "ml": Section(
        "ml", Path("ml/pyproject.toml"), (sys.executable, "scripts/verify_ml.py")
    ),
    "e2e": Section(
        "e2e",
        Path("services/api/tests/integration/test_analysis_journey.py"),
        (sys.executable, "scripts/verify_e2e.py"),
    ),
    "security": Section(
        "security",
        Path("services/api/tests/security"),
        (sys.executable, "scripts/verify_security.py"),
    ),
    "release": Section(
        "release",
        Path("docker-compose.yml"),
        (sys.executable, "scripts/verify_release.py"),
    ),
}


def run_step(label: str, command: Sequence[str]) -> bool:
    print(f"\n== {label} ==")
    print(f"$ {display_command(command)}")
    started = time.perf_counter()
    result = subprocess.run(list(command), cwd=REPO_ROOT, check=False)
    duration = time.perf_counter() - started
    outcome = "PASS" if result.returncode == 0 else "FAIL"
    print(f"{outcome}: {label} ({duration:.2f}s, exit {result.returncode})")
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--quick",
        action="store_true",
        help="run repository policy checks available in P00",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        help="run every project section and fail for missing sections",
    )
    for name in SECTIONS:
        mode.add_argument(
            f"--{name}", action="store_true", help=f"run the {name} section"
        )
    args = parser.parse_args()

    python = sys.executable
    success = True
    success &= run_step("toolchain doctor", [python, "scripts/doctor.py"])
    success &= run_step(
        "secret and prohibited-artifact scan", [python, "scripts/check_secrets.py"]
    )

    if args.quick:
        print(
            "\nVerification summary: P00 quick checks complete; product suites are not part of --quick."
        )
        return 0 if success else 1

    selected = (
        list(SECTIONS)
        if args.all
        else [name for name in SECTIONS if getattr(args, name)]
    )
    unavailable: list[str] = []
    for name in selected:
        section = SECTIONS[name]
        if not (REPO_ROOT / section.marker).exists():
            print(
                f"\nBLOCKED: {section.name} is not implemented; missing {section.marker.as_posix()}"
            )
            unavailable.append(section.name)
            continue
        if section.command is None:
            print(
                f"\nBLOCKED: {section.name} marker exists but its phase verification command "
                "is not registered yet"
            )
            unavailable.append(section.name)
            continue
        success &= run_step(f"{section.name} verification", section.command)

    if unavailable:
        print(
            f"\nVerification summary: FAIL/BLOCKED ({len(unavailable)} section(s): {', '.join(unavailable)})"
        )
        return 2
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
