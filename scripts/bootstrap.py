#!/usr/bin/env python3
"""Prepare safe, ignored local directories for MoMo-FDVS development."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from _common import REPO_ROOT


LOCAL_DIRECTORIES = (
    Path(".local/private-storage"),
    Path(".local/model-artifacts"),
    Path(".local/tmp"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--create-env",
        action="store_true",
        help="copy .env.example to ignored .env when .env is absent",
    )
    args = parser.parse_args()

    for relative in LOCAL_DIRECTORIES:
        target = REPO_ROOT / relative
        target.mkdir(parents=True, exist_ok=True)
        print(f"ready: {relative.as_posix()}")

    if args.create_env:
        source = REPO_ROOT / ".env.example"
        target = REPO_ROOT / ".env"
        if target.exists():
            print("kept: .env already exists")
        elif not source.is_file():
            print("error: .env.example is missing")
            return 1
        else:
            shutil.copyfile(source, target)
            print("created: .env from .env.example (review placeholders before running services)")

    print("Bootstrap foundation complete. Product dependencies are installed in their implementation phases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
