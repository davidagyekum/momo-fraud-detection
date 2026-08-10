#!/usr/bin/env python3
"""Scan repository candidates for committed secrets and prohibited artifacts."""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from _common import REPO_ROOT, git_command


MAX_TEXT_BYTES = 2_000_000
MAX_REPOSITORY_FILE_BYTES = 10_000_000
ALLOWED_ENV_FILES = {".env.example"}
PROHIBITED_SUFFIXES = {
    ".h5",
    ".hdf5",
    ".joblib",
    ".keras",
    ".onnx",
    ".p12",
    ".pfx",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".tflite",
}
PROHIBITED_PARTS = {
    "datasets",
    "model-artifacts",
    "private-storage",
    "private_uploads",
    "uploads",
}
PROHIBITED_PATH_PREFIXES = {
    ("ml", "data", "authorised"),
    ("ml", "data", "authorized"),
    ("ml", "data", "private"),
    ("ml", "data", "raw"),
}
PLACEHOLDER_MARKERS = {
    "change-me",
    "change_me",
    "changeme",
    "controlled",
    "demo",
    "example",
    "fixture",
    "local_only",
    "not-configured",
    "placeholder",
    "replace-me",
    "replace_with",
    "tbd",
    "test-only",
}


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


CONTENT_PATTERNS = [
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{30,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
]
ASSIGNMENT_PATTERN = re.compile(
    r"(?im)^\s*(?:export\s+)?(?:(?:const|let|var)\s+)?"
    r"([A-Z0-9_]*(?:SECRET|PASSWORD|PRIVATE_KEY|ACCESS_TOKEN|REFRESH_TOKEN|API_KEY)[A-Z0-9_]*)"
    r"[ \t]*[:=][ \t]*['\"]?([^'\"\s#]{8,})"
)
PYTHON_ASSIGNMENT_PATTERN = re.compile(
    r"(?im)^\s*([A-Z0-9_]*(?:SECRET|PASSWORD|PRIVATE_KEY|ACCESS_TOKEN|REFRESH_TOKEN|API_KEY)[A-Z0-9_]*)"
    r"[ \t]*=[ \t]*(['\"])([^'\"\r\n]{8,})\2"
)


def candidate_files() -> list[Path]:
    try:
        result = subprocess.run(
            git_command("ls-files", "--cached", "--others", "--exclude-standard", "-z"),
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
            timeout=20,
        )
        names = [
            name
            for name in result.stdout.decode("utf-8", errors="replace").split("\0")
            if name
        ]
        return sorted(REPO_ROOT / name for name in names)
    except (OSError, subprocess.SubprocessError):
        return sorted(
            path
            for path in REPO_ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts
        )


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def inspect_file(path: Path) -> list[Finding]:
    relative = path.relative_to(REPO_ROOT).as_posix()
    lowered_parts = {part.lower() for part in path.relative_to(REPO_ROOT).parts}
    findings: list[Finding] = []

    if path.name.startswith(".env") and path.name not in ALLOWED_ENV_FILES:
        findings.append(Finding(relative, "environment file is prohibited"))
    if path.suffix.lower() in PROHIBITED_SUFFIXES:
        findings.append(
            Finding(relative, f"artifact type {path.suffix.lower()} is prohibited")
        )
    if lowered_parts & PROHIBITED_PARTS:
        findings.append(Finding(relative, "path is reserved for private/runtime data"))
    lowered_path_parts = tuple(
        part.lower() for part in path.relative_to(REPO_ROOT).parts
    )
    if any(
        lowered_path_parts[: len(prefix)] == prefix
        for prefix in PROHIBITED_PATH_PREFIXES
    ):
        findings.append(Finding(relative, "path is reserved for private research data"))

    try:
        size = path.stat().st_size
    except OSError as exc:
        return [Finding(relative, f"unable to stat file: {exc}")]
    if size > MAX_REPOSITORY_FILE_BYTES:
        findings.append(
            Finding(relative, f"file is larger than {MAX_REPOSITORY_FILE_BYTES} bytes")
        )
    if size > MAX_TEXT_BYTES:
        return findings

    try:
        raw = path.read_bytes()
    except OSError as exc:
        findings.append(Finding(relative, f"unable to read file: {exc}"))
        return findings
    if b"\x00" in raw:
        return findings

    text = raw.decode("utf-8", errors="replace")
    for label, pattern in CONTENT_PATTERNS:
        if pattern.search(text):
            findings.append(Finding(relative, label))
    assignment_matches = (
        PYTHON_ASSIGNMENT_PATTERN.finditer(text)
        if path.suffix == ".py"
        else ASSIGNMENT_PATTERN.finditer(text)
    )
    for match in assignment_matches:
        groups = match.groups()
        key, value = (
            (groups[0], groups[2]) if path.suffix == ".py" else (groups[0], groups[1])
        )
        if path.name == ".env.example" and is_placeholder(value):
            continue
        if is_placeholder(value):
            continue
        code_value = value.rstrip(",;")
        if path.suffix in {".js", ".jsx", ".ts", ".tsx"} and (
            code_value in {"boolean", "number", "password", "string"}
            or code_value.startswith(("z.", "forwardRef<"))
        ):
            # Type declarations, schema expressions and same-module identifiers are
            # not assigned credential values. Quoted fixture values still reach the
            # placeholder check above, and unknown literals remain findings.
            continue
        findings.append(
            Finding(relative, f"possible non-placeholder secret assigned to {key}")
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verbose", action="store_true", help="list every scanned file"
    )
    args = parser.parse_args()

    files = candidate_files()
    findings: list[Finding] = []
    for path in files:
        if not path.is_file():
            continue
        if args.verbose:
            print(f"scan {path.relative_to(REPO_ROOT).as_posix()}")
        findings.extend(inspect_file(path))

    if findings:
        print(
            f"Secret/artifact scan: FAIL ({len(findings)} finding(s) across {len(files)} files)"
        )
        for finding in findings:
            print(f"- {finding.path}: {finding.reason}")
        return 1

    print(f"Secret/artifact scan: PASS ({len(files)} candidate files scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
