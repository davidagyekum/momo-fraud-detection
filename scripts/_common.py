"""Shared helpers for repository-level Python scripts."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]


def display_command(command: Sequence[str]) -> str:
    """Return a readable command without invoking a platform shell."""

    return " ".join(f'"{part}"' if " " in part else part for part in command)


def run(
    command: Sequence[str],
    *,
    check: bool = False,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command at the repository root without shell interpolation."""

    return subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        check=check,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ.copy(),
    )


def git_command(*arguments: str) -> list[str]:
    """Build a Git command that is safe in ownership-isolated sandboxes."""

    return ["git", "-c", f"safe.directory={REPO_ROOT.as_posix()}", *arguments]
