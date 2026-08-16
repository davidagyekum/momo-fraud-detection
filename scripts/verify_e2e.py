#!/usr/bin/env python3
"""Run the controlled PR19 owner-to-investigator acceptance journey."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from _common import REPO_ROOT, display_command
from verify_admin import node_argv as admin_node_argv
from verify_admin import run_playwright

API_ROOT = REPO_ROOT / "services" / "api"
MOBILE_ROOT = REPO_ROOT / "apps" / "mobile"


def node_argv(root: Path, script: str, *args: str) -> list[str]:
    node = os.environ.get("MOMO_NODE_EXECUTABLE") or shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is not available")
    script_path = root / script
    if not script_path.is_file():
        raise RuntimeError(
            f"missing JavaScript tool: {script_path.relative_to(REPO_ROOT)}"
        )
    return [node, str(script_path), *args]


def run(label: str, command: list[str], cwd: Path) -> bool:
    print(f"\n== {label} ==", flush=True)
    print(f"$ {display_command(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)
    print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}")
    return result.returncode == 0


def main() -> int:
    if not os.environ.get("TEST_DATABASE_URL"):
        print("End-to-end verification: FAIL (TEST_DATABASE_URL is required)")
        return 1
    try:
        mobile_tests = node_argv(
            MOBILE_ROOT,
            "node_modules/jest/bin/jest.js",
            "--ci",
            "--runInBand",
            "--coverage=false",
            "src/components/__tests__/analysis-result.test.tsx",
            "src/lib/__tests__/engagement-client.test.ts",
        )
        mobile_export = node_argv(
            MOBILE_ROOT,
            "node_modules/expo/bin/cli",
            "export",
            "--platform",
            "web",
            "--output-dir",
            "dist",
        )
        playwright = admin_node_argv(
            "node_modules/@playwright/test/cli.js",
            "test",
            "--config",
            "playwright.config.ts",
        )
    except RuntimeError as error:
        print(f"End-to-end verification: FAIL ({error})")
        return 1

    success = run(
        "controlled API acceptance journey",
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_analysis_journey.py",
            "--no-cov",
            "-q",
        ],
        API_ROOT,
    )
    success &= run("mobile result and engagement journey", mobile_tests, MOBILE_ROOT)
    success &= run("mobile static web acceptance export", mobile_export, MOBILE_ROOT)
    success &= run_playwright(playwright)
    print(f"\nEnd-to-end verification: {'PASS' if success else 'FAIL'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
