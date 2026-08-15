"""Reproducible Tesseract 5 bootstrap for the Ubuntu Jammy Colab image."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, MutableMapping, Sequence
from pathlib import Path
from typing import Final

TESSERACT_REQUIRED_MAJOR: Final = 5
TESSERACT_SOURCE_VERSION: Final = "5.5.3"
TESSERACT_SOURCE_COMMIT: Final = "db0ec62f81b0737fbbe184d8fea40af5738f8eef"
TESSERACT_SOURCE_REPOSITORY: Final = "https://github.com/tesseract-ocr/tesseract.git"
TESSERACT_BOOTSTRAP_VERSION: Final = "colab-tesseract-bootstrap-v1"
DEFAULT_TESSDATA_CANDIDATES: Final = (
    Path("/usr/share/tesseract-ocr/5/tessdata"),
    Path("/usr/share/tesseract-ocr/4.00/tessdata"),
    Path("/usr/share/tesseract-ocr/tessdata"),
    Path("/usr/local/share/tessdata"),
)

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class ColabOCRBootstrapError(RuntimeError):
    """Raised when the Colab OCR runtime cannot satisfy its pinned binary contract."""


def _captured_command(
    runner: CommandRunner, command: list[str]
) -> subprocess.CompletedProcess[str]:
    try:
        completed = runner(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise ColabOCRBootstrapError("required OCR bootstrap command is unavailable") from exc
    if completed.returncode != 0:
        raise ColabOCRBootstrapError("required OCR bootstrap command failed")
    return completed


def _streaming_command(runner: CommandRunner, command: list[str]) -> None:
    try:
        completed = runner(command, check=False, text=True)
    except OSError as exc:
        raise ColabOCRBootstrapError("required OCR bootstrap command is unavailable") from exc
    if completed.returncode != 0:
        raise ColabOCRBootstrapError("required OCR bootstrap command failed")


def _probe_tesseract_version(runner: CommandRunner) -> str | None:
    try:
        completed = runner(["tesseract", "--version"], check=False, capture_output=True, text=True)
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    first_line = completed.stdout.splitlines()[0] if completed.stdout else ""
    match = re.fullmatch(r"tesseract\s+(\d+(?:\.\d+){1,3})(?:\s.*)?", first_line.strip())
    return match.group(1) if match is not None else None


def _major(version: str | None) -> int | None:
    if version is None:
        return None
    match = re.match(r"(\d+)", version)
    return int(match.group(1)) if match is not None else None


def _select_tessdata(candidates: Sequence[Path]) -> Path:
    for candidate in candidates:
        if (candidate / "eng.traineddata").is_file():
            return candidate.resolve()
    raise ColabOCRBootstrapError("English Tesseract language data is unavailable")


def ensure_tesseract5(
    *,
    source_root: Path,
    runner: CommandRunner = subprocess.run,
    tessdata_candidates: Sequence[Path] = DEFAULT_TESSDATA_CANDIDATES,
    environment: MutableMapping[str, str] = os.environ,
) -> dict[str, object]:
    """Ensure an exact-major Tesseract runtime without trusting Jammy's version 4 package."""

    source_root = source_root.resolve()
    initial_version = _probe_tesseract_version(runner)
    built_from_source = _major(initial_version) != TESSERACT_REQUIRED_MAJOR

    if built_from_source:
        source_root.mkdir(parents=True, exist_ok=True)
        build_root = source_root.with_name(f"{source_root.name}-build")
        build_root.mkdir(parents=True, exist_ok=True)
        _streaming_command(runner, ["apt-get", "update"])
        _streaming_command(
            runner,
            [
                "apt-get",
                "install",
                "-y",
                "build-essential",
                "cmake",
                "ninja-build",
                "pkg-config",
                "libarchive-dev",
                "libcairo2-dev",
                "libcurl4-openssl-dev",
                "libicu-dev",
                "libleptonica-dev",
                "libpango1.0-dev",
                "tesseract-ocr-eng",
            ],
        )
        if not (source_root / ".git").is_dir():
            _streaming_command(runner, ["git", "init", str(source_root)])
            _streaming_command(
                runner,
                [
                    "git",
                    "-C",
                    str(source_root),
                    "remote",
                    "add",
                    "origin",
                    TESSERACT_SOURCE_REPOSITORY,
                ],
            )
        _streaming_command(
            runner,
            [
                "git",
                "-C",
                str(source_root),
                "fetch",
                "--depth",
                "1",
                "origin",
                TESSERACT_SOURCE_COMMIT,
            ],
        )
        _streaming_command(
            runner,
            ["git", "-C", str(source_root), "checkout", "--detach", TESSERACT_SOURCE_COMMIT],
        )
        revision = _captured_command(
            runner, ["git", "-C", str(source_root), "rev-parse", "HEAD"]
        ).stdout.strip()
        if revision != TESSERACT_SOURCE_COMMIT:
            raise ColabOCRBootstrapError("Tesseract source commit identity changed")
        _streaming_command(
            runner,
            [
                "cmake",
                "-S",
                str(source_root),
                "-B",
                str(build_root),
                "-G",
                "Ninja",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_INSTALL_PREFIX=/usr/local",
                "-DBUILD_TRAINING_TOOLS=OFF",
                "-DBUILD_TESTS=OFF",
            ],
        )
        _streaming_command(runner, ["cmake", "--build", str(build_root), "--parallel", "2"])
        _streaming_command(runner, ["cmake", "--install", str(build_root)])
        _streaming_command(runner, ["ldconfig"])

    final_version = _probe_tesseract_version(runner) if built_from_source else initial_version
    if _major(final_version) != TESSERACT_REQUIRED_MAJOR:
        raise ColabOCRBootstrapError("Tesseract required major version 5 is unavailable")
    tessdata = _select_tessdata(tessdata_candidates)
    environment["TESSDATA_PREFIX"] = str(tessdata)
    return {
        "schema_version": TESSERACT_BOOTSTRAP_VERSION,
        "required_major_version": TESSERACT_REQUIRED_MAJOR,
        "version": final_version,
        "built_from_source": built_from_source,
        "source_repository": TESSERACT_SOURCE_REPOSITORY if built_from_source else None,
        "source_version": TESSERACT_SOURCE_VERSION if built_from_source else None,
        "source_commit": TESSERACT_SOURCE_COMMIT if built_from_source else None,
        "tessdata_prefix": str(tessdata),
    }
