from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from momo_fdvs_ml import cli
from momo_fdvs_ml.cli import main
from momo_fdvs_ml.image_model import ImageTrainingOutputs


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


def test_cli_validates_recorded_image_report(capsys) -> None:  # type: ignore[no-untyped-def]
    root = Path(__file__).parents[1] / "data" / "controlled"
    assert (
        main(
            [
                "validate-image",
                "--manifest",
                str(root / "manifest.csv"),
                "--root",
                str(root),
                "--recorded-report",
                str(root / "image_dataset_report.json"),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["report_scope"] == "dataset_preflight_only"
    assert report["training_executed_by_report"] is False
    assert report["record_count"] == 12


def test_cli_image_training_and_verification_dispatch(tmp_path: Path, capsys, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    artifact = tmp_path / "model.keras"
    artifact.write_bytes(b"artifact")
    report = {"acceptance_passed": True}
    outputs = ImageTrainingOutputs(
        artifact,
        "a" * 64,
        tmp_path / "report.json",
        tmp_path / "card.md",
        tmp_path / "registry.json",
        tmp_path / "matrix.png",
        report,
    )
    monkeypatch.setattr(cli, "train_and_package_image_model", lambda **kwargs: outputs)
    monkeypatch.setattr(cli, "image_runtime_fingerprint", lambda: {"tensorflow": "test"})
    assert (
        main(
            [
                "train-image",
                "--manifest",
                "manifest.csv",
                "--root",
                ".",
                "--output-dir",
                str(tmp_path),
                "--model-version",
                "v1",
                "--training-commit-sha",
                "a" * 40,
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["acceptance_passed"] is True

    loaded = SimpleNamespace(input_shape=(None, 224, 224, 3), output_shape=(None, 1))
    monkeypatch.setattr(cli, "load_and_verify_image_artifact", lambda *a, **k: loaded)
    assert (
        main(
            [
                "verify-image-artifact",
                "--artifact",
                str(artifact),
                "--sha256",
                "a" * 64,
                "--schema-hash",
                "b" * 64,
            ]
        )
        == 0
    )
    verified = json.loads(capsys.readouterr().out)
    assert verified["artifact_verified"] is True
    assert verified["output_shape"] == [None, 1]
