#!/usr/bin/env python3
"""Run the complete implemented machine-learning data and code quality gate."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_ROOT = REPO_ROOT / "ml"
CONTROLLED_ROOT = ML_ROOT / "data" / "controlled"
sys.path.insert(0, str(ML_ROOT / "src"))

from momo_fdvs_ml.execution import (  # noqa: E402
    ExecutionGuardError,
    assert_ci_profile_is_safe,
)

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
    (
        "structured dataset",
        [
            sys.executable,
            "-m",
            "momo_fdvs_ml",
            "validate-structured",
            "--dataset",
            str(CONTROLLED_ROOT / "structured_features.csv"),
            "--source-manifest",
            str(CONTROLLED_ROOT / "manifest.csv"),
            "--recorded-report",
            str(CONTROLLED_ROOT / "structured_dataset_report.json"),
        ],
    ),
    (
        "image dataset",
        [
            sys.executable,
            "-m",
            "momo_fdvs_ml",
            "validate-image",
            "--manifest",
            str(CONTROLLED_ROOT / "manifest.csv"),
            "--root",
            str(CONTROLLED_ROOT),
            "--recorded-report",
            str(CONTROLLED_ROOT / "image_dataset_report.json"),
        ],
    ),
]


def main() -> int:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ML_ROOT / "src")
    try:
        assert_ci_profile_is_safe(environment)
    except ExecutionGuardError as exc:
        print(f"ML verification blocked by execution policy: {exc}")
        return 2
    for label, command in COMMANDS:
        print(f"\n== ml {label} ==", flush=True)
        result = subprocess.run(command, cwd=ML_ROOT, env=environment, check=False)
        if result.returncode != 0:
            print(f"ML verification failed at {label} (exit {result.returncode})")
            return result.returncode
    print(
        "\nML data/code verification passed; this command does not execute model training"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
