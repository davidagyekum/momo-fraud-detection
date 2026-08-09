#!/usr/bin/env python3
"""Run the complete P01 backend quality gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "services" / "api"

COMMANDS = [
    ("format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("type", [sys.executable, "-m", "mypy", "src"]),
    ("tests", [sys.executable, "-m", "pytest"]),
    (
        "contract",
        [sys.executable, str(REPO_ROOT / "scripts" / "export_openapi.py"), "--check"],
    ),
]


def main() -> int:
    for label, command in COMMANDS:
        print(f"\n== backend {label} ==", flush=True)
        result = subprocess.run(command, cwd=API_ROOT, check=False)
        if result.returncode != 0:
            print(f"Backend verification failed at {label} (exit {result.returncode})")
            return result.returncode
    print("\nBackend verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
