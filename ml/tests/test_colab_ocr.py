from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from momo_fdvs_ml.colab_ocr import (
    TESSERACT_SOURCE_COMMIT,
    ColabOCRBootstrapError,
    ensure_tesseract5,
)


class CommandRunner:
    def __init__(
        self,
        *,
        initial_version: str,
        final_version: str | None = None,
        failed_command: tuple[str, ...] | None = None,
        unavailable_command: tuple[str, ...] | None = None,
    ) -> None:
        self.initial_version = initial_version
        self.final_version = final_version or initial_version
        self.failed_command = failed_command
        self.unavailable_command = unavailable_command
        self.commands: list[tuple[str, ...]] = []
        self.version_calls = 0
        self.revision = TESSERACT_SOURCE_COMMIT

    def __call__(self, command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        normalized = tuple(command)
        self.commands.append(normalized)
        if normalized == self.unavailable_command:
            raise OSError("controlled missing command")
        if normalized == self.failed_command:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="controlled failure")
        if normalized == ("tesseract", "--version"):
            self.version_calls += 1
            version = self.initial_version if self.version_calls == 1 else self.final_version
            return subprocess.CompletedProcess(
                command, 0, stdout=f"tesseract {version}\n", stderr=""
            )
        if normalized[-2:] == ("rev-parse", "HEAD"):
            return subprocess.CompletedProcess(command, 0, stdout=f"{self.revision}\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _tessdata(tmp_path: Path) -> Path:
    root = tmp_path / "tessdata"
    root.mkdir()
    (root / "eng.traineddata").write_bytes(b"controlled-test-language-data")
    return root


def test_tesseract5_bootstrap_uses_compatible_binary_without_building(tmp_path: Path) -> None:
    runner = CommandRunner(initial_version="5.3.0")
    environment: dict[str, str] = {}
    tessdata = _tessdata(tmp_path)

    report = ensure_tesseract5(
        source_root=tmp_path / "source",
        runner=runner,
        tessdata_candidates=(tessdata,),
        environment=environment,
    )

    assert report["version"] == "5.3.0"
    assert report["built_from_source"] is False
    assert report["source_commit"] is None
    assert environment["TESSDATA_PREFIX"] == str(tessdata)
    assert runner.commands == [("tesseract", "--version")]


def test_tesseract5_bootstrap_builds_exact_official_commit_on_jammy(tmp_path: Path) -> None:
    runner = CommandRunner(initial_version="4.1.1", final_version="5.5.3")
    environment: dict[str, str] = {}
    tessdata = _tessdata(tmp_path)
    source_root = tmp_path / "source"

    report = ensure_tesseract5(
        source_root=source_root,
        runner=runner,
        tessdata_candidates=(tessdata,),
        environment=environment,
    )

    assert report["version"] == "5.5.3"
    assert report["built_from_source"] is True
    assert report["source_commit"] == TESSERACT_SOURCE_COMMIT
    assert (
        "git",
        "-C",
        str(source_root),
        "fetch",
        "--depth",
        "1",
        "origin",
        TESSERACT_SOURCE_COMMIT,
    ) in runner.commands
    assert any(
        command[:3] == ("cmake", "--build", str(tmp_path / "source-build"))
        for command in runner.commands
    )
    assert ("cmake", "--install", str(tmp_path / "source-build")) in runner.commands
    assert environment["TESSDATA_PREFIX"] == str(tessdata)


def test_tesseract5_bootstrap_rejects_source_identity_drift(tmp_path: Path) -> None:
    runner = CommandRunner(initial_version="4.1.1", final_version="5.5.3")
    runner.revision = "0" * 40

    with pytest.raises(ColabOCRBootstrapError, match="source commit"):
        ensure_tesseract5(
            source_root=tmp_path / "source",
            runner=runner,
            tessdata_candidates=(_tessdata(tmp_path),),
            environment={},
        )


def test_tesseract5_bootstrap_rejects_non_major_five_after_build(tmp_path: Path) -> None:
    runner = CommandRunner(initial_version="4.1.1", final_version="4.1.1")

    with pytest.raises(ColabOCRBootstrapError, match="required major version"):
        ensure_tesseract5(
            source_root=tmp_path / "source",
            runner=runner,
            tessdata_candidates=(_tessdata(tmp_path),),
            environment={},
        )


@pytest.mark.parametrize(
    ("runner", "expected_message"),
    [
        (
            CommandRunner(initial_version="4.1.1", failed_command=("apt-get", "update")),
            "command failed",
        ),
        (
            CommandRunner(initial_version="4.1.1", unavailable_command=("apt-get", "update")),
            "command is unavailable",
        ),
        (
            CommandRunner(
                initial_version="4.1.1",
                final_version="5.5.3",
                failed_command=("git", "-C", "SOURCE", "rev-parse", "HEAD"),
            ),
            "command failed",
        ),
    ],
)
def test_tesseract5_bootstrap_reports_command_failures(
    tmp_path: Path, runner: CommandRunner, expected_message: str
) -> None:
    source_root = tmp_path / "source"
    if runner.failed_command and "SOURCE" in runner.failed_command:
        runner.failed_command = tuple(
            str(source_root) if part == "SOURCE" else part for part in runner.failed_command
        )

    with pytest.raises(ColabOCRBootstrapError, match=expected_message):
        ensure_tesseract5(
            source_root=source_root,
            runner=runner,
            tessdata_candidates=(_tessdata(tmp_path),),
            environment={},
        )


def test_tesseract5_bootstrap_requires_english_language_data(tmp_path: Path) -> None:
    with pytest.raises(ColabOCRBootstrapError, match="English Tesseract language data"):
        ensure_tesseract5(
            source_root=tmp_path / "source",
            runner=CommandRunner(initial_version="5.5.3"),
            tessdata_candidates=(tmp_path / "missing-tessdata",),
            environment={},
        )
