#!/usr/bin/env python3
"""Run the P04 Expo mobile quality gates under the pinned Node runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from _common import REPO_ROOT, display_command

MOBILE_ROOT = REPO_ROOT / "apps" / "mobile"


def node_argv(script: str, *args: str) -> list[str]:
    node = os.environ.get("MOMO_NODE_EXECUTABLE") or shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is not available")
    script_path = MOBILE_ROOT / script
    if not script_path.is_file():
        raise RuntimeError(
            f"missing JavaScript tool: {script_path.relative_to(REPO_ROOT)}"
        )
    return [node, str(script_path), *args]


def run(label: str, command: list[str], cwd: Path = MOBILE_ROOT) -> bool:
    print(f"\n== {label} ==")
    print(f"$ {display_command(command)}")
    return subprocess.run(command, cwd=cwd, check=False).returncode == 0


def main() -> int:
    try:
        commands = [
            (
                "mobile format",
                node_argv("node_modules/prettier/bin/prettier.cjs", "--check", "."),
            ),
            (
                "mobile lint",
                node_argv(
                    "node_modules/eslint/bin/eslint.js", ".", "--max-warnings", "0"
                ),
            ),
            (
                "mobile typecheck",
                node_argv("node_modules/typescript/bin/tsc", "--noEmit"),
            ),
            (
                "mobile unit and component tests",
                node_argv(
                    "node_modules/jest/bin/jest.js",
                    "--ci",
                    "--runInBand",
                    "--coverage",
                ),
            ),
            (
                "mobile static web export",
                node_argv(
                    "node_modules/expo/bin/cli",
                    "export",
                    "--platform",
                    "web",
                    "--output-dir",
                    "dist",
                ),
            ),
        ]
    except RuntimeError as error:
        print(f"Mobile verification: FAIL ({error})")
        return 1

    success = run(
        "mobile token-storage policy",
        [sys.executable, "scripts/check_mobile_token_storage.py"],
        REPO_ROOT,
    )
    for label, command in commands:
        success &= run(label, command)
    print(f"\nMobile verification: {'PASS' if success else 'FAIL'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
