#!/usr/bin/env python3
"""Run the P05 administrator portal quality gates under the pinned Node runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from _common import REPO_ROOT, display_command

ADMIN_ROOT = REPO_ROOT / "apps" / "admin"


def node_argv(script: str, *args: str) -> list[str]:
    node = os.environ.get("MOMO_NODE_EXECUTABLE") or shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is not available")
    script_path = ADMIN_ROOT / script
    if not script_path.is_file():
        raise RuntimeError(
            f"missing JavaScript tool: {script_path.relative_to(REPO_ROOT)}"
        )
    return [node, str(script_path), *args]


def run(label: str, command: list[str], cwd: Path = ADMIN_ROOT) -> bool:
    print(f"\n== {label} ==")
    print(f"$ {display_command(command)}")
    return subprocess.run(command, cwd=cwd, check=False).returncode == 0


def main() -> int:
    try:
        commands = [
            (
                "admin format",
                node_argv("node_modules/prettier/bin/prettier.cjs", "--check", "."),
            ),
            (
                "admin lint",
                node_argv(
                    "node_modules/eslint/bin/eslint.js", ".", "--max-warnings", "0"
                ),
            ),
            (
                "admin typecheck",
                node_argv("node_modules/typescript/bin/tsc", "-b", "--pretty", "false"),
            ),
            (
                "admin unit and component tests",
                node_argv("node_modules/vitest/vitest.mjs", "run", "--coverage"),
            ),
            (
                "admin Playwright smoke tests",
                node_argv(
                    "node_modules/@playwright/test/cli.js",
                    "test",
                    "--config",
                    "playwright.config.ts",
                ),
            ),
            (
                "admin production build",
                node_argv("node_modules/typescript/bin/tsc", "-b"),
            ),
            (
                "admin Vite bundle",
                node_argv("node_modules/vite/bin/vite.js", "build"),
            ),
        ]
    except RuntimeError as error:
        print(f"Admin verification: FAIL ({error})")
        return 1

    success = run(
        "admin browser-security policy",
        [sys.executable, "scripts/check_admin_security_policy.py"],
        REPO_ROOT,
    )
    for label, command in commands:
        success &= run(label, command)
    print(f"\nAdmin verification: {'PASS' if success else 'FAIL'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
