#!/usr/bin/env python3
"""Run the complete P10 machine-learning data quality gate."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ML_ROOT = REPO_ROOT / "ml"
CONTROLLED_ROOT = ML_ROOT / "data" / "controlled"

COMMANDS = [
    ("format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("type", [sys.executable, "-m", "mypy", "src"]),
    ("tests", [sys.executable, "-m", "pytest"]),
    (
        "controlled dataset",
        [
            sys.executable,
            "-m",
            "momo_fdvs_ml",
            "validate",
            "--manifest",
            str(CONTROLLED_ROOT / "manifest.csv"),
            "--root",
            str(CONTROLLED_ROOT),
            "--check-recorded-report",
        ],
    ),
]


def main() -> int:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ML_ROOT / "src")
    for label, command in COMMANDS:
        print(f"\n== ml {label} ==", flush=True)
        result = subprocess.run(command, cwd=ML_ROOT, env=environment, check=False)
        if result.returncode != 0:
            print(f"ML verification failed at {label} (exit {result.returncode})")
            return result.returncode
    print("\nML data verification passed; no model training was executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
