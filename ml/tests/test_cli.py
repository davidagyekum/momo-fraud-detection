from __future__ import annotations

import json
from pathlib import Path

from momo_fdvs_ml.cli import main


def test_cli_generates_and_validates_dataset(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    root = tmp_path / "controlled"
    assert main(["generate", "--output", str(root), "--seed", "20260810"]) == 0
    generated_output = json.loads(capsys.readouterr().out)
    assert generated_output["error_count"] == 0

    assert (
        main(
            [
                "validate",
                "--manifest",
                str(root / "manifest.csv"),
                "--root",
                str(root),
                "--check-recorded-report",
            ]
        )
        == 0
    )
    validation_output = json.loads(capsys.readouterr().out)
    assert validation_output["recorded_report_errors"] == []


def test_cli_reports_manifest_error(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    missing = tmp_path / "missing.csv"
    assert main(["validate", "--manifest", str(missing), "--root", str(tmp_path)]) == 1
    assert "unable to read manifest" in capsys.readouterr().out
