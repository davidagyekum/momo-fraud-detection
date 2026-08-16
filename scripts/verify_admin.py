#!/usr/bin/env python3
"""Run the P05 administrator portal quality gates under the pinned Node runtime."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
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


def run(
    label: str,
    command: list[str],
    cwd: Path = ADMIN_ROOT,
    environment: dict[str, str] | None = None,
) -> bool:
    print(f"\n== {label} ==")
    print(f"$ {display_command(command)}")
    return (
        subprocess.run(command, cwd=cwd, env=environment, check=False).returncode == 0
    )


def run_playwright(command: list[str]) -> bool:
    """Run Playwright against an explicitly managed Vite process.

    Playwright's Windows web-server teardown can leave Vite workers alive. Owning the
    exact Vite process here keeps the acceptance gate deterministic on every host.
    """
    vite_command = node_argv(
        "node_modules/vite/bin/vite.js",
        "--host",
        "127.0.0.1",
        "--port",
        "5174",
        "--strictPort",
    )
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    server = subprocess.Popen(
        vite_command,
        cwd=ADMIN_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if server.poll() is not None:
                print("Admin Playwright: FAIL (Vite exited before becoming ready)")
                return False
            try:
                with urllib.request.urlopen(
                    "http://127.0.0.1:5174/login", timeout=1
                ) as response:
                    if response.status == 200:
                        break
            except (OSError, urllib.error.URLError):
                time.sleep(0.25)
        else:
            print("Admin Playwright: FAIL (Vite readiness timed out)")
            return False
        environment = os.environ.copy()
        environment["PLAYWRIGHT_EXTERNAL_SERVER"] = "1"
        return run("admin Playwright smoke tests", command, environment=environment)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)


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
        if label == "admin unit and component tests":
            success &= run_playwright(
                node_argv(
                    "node_modules/@playwright/test/cli.js",
                    "test",
                    "--config",
                    "playwright.config.ts",
                )
            )
    print(f"\nAdmin verification: {'PASS' if success else 'FAIL'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
