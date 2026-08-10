from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from momo_fdvs_ml import cli
from momo_fdvs_ml.cli import main
from momo_fdvs_ml.execution import FULL_TRAINING_ACKNOWLEDGEMENT
from momo_fdvs_ml.image_model import ImageTrainingOutputs
from momo_fdvs_ml.smoke import SmokeOutputs


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


def test_cli_validates_data_governance(capsys) -> None:  # type: ignore[no-untyped-def]
    root = Path(__file__).resolve().parents[2] / "data"
    assert (
        main(
            [
                "validate-governance",
                "--root",
                str(root),
                "--recorded-report",
                str(root / "governance_report.json"),
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["registry_entry_count"] == 6
    assert report["enabled_dataset_count"] == 0
    assert report["acquisition_executed"] is False
    assert report["training_executed"] is False


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
    monkeypatch.setattr(cli, "require_training_execution", lambda *args, **kwargs: None)
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
                "--profile",
                "full",
                "--acknowledge-full-training",
                FULL_TRAINING_ACKNOWLEDGEMENT,
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


def test_cli_blocks_full_training_before_loading_missing_data(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "train-image",
                "--manifest",
                "missing.csv",
                "--root",
                ".",
                "--output-dir",
                ".",
                "--model-version",
                "blocked-v1",
                "--training-commit-sha",
                "a" * 40,
                "--profile",
                "full",
                "--acknowledge-full-training",
                FULL_TRAINING_ACKNOWLEDGEMENT,
            ]
        )
        == 1
    )
    assert "permitted only in Google Colab" in capsys.readouterr().out


def test_cli_validates_standard_notebooks_and_colab_locks(capsys) -> None:  # type: ignore[no-untyped-def]
    repository_root = Path(__file__).resolve().parents[2]
    notebook_root = repository_root / "ml/notebooks/colab"
    assert (
        main(
            [
                "validate-notebooks",
                "--root",
                str(notebook_root),
                "--recorded-report",
                str(notebook_root / "notebook_report.json"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["issue_count"] == 0
    assert (
        main(
            [
                "colab-lock-report",
                "--repository-root",
                str(repository_root),
                "--recorded-report",
                str(repository_root / "ml/colab_lock_report.json"),
            ]
        )
        == 0
    )
    assert len(json.loads(capsys.readouterr().out)["locks"]) == 3


def test_cli_reports_recorded_notebook_and_lock_drift(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    repository_root = Path(__file__).resolve().parents[2]
    mismatch = tmp_path / "mismatch.json"
    mismatch.write_text("{}", encoding="utf-8")
    assert (
        main(
            [
                "validate-notebooks",
                "--root",
                str(repository_root / "ml/notebooks/colab"),
                "--recorded-report",
                str(mismatch),
            ]
        )
        == 1
    )
    assert "does not match" in capsys.readouterr().out
    assert (
        main(
            [
                "colab-lock-report",
                "--repository-root",
                str(repository_root),
                "--recorded-report",
                str(mismatch),
            ]
        )
        == 1
    )
    assert "does not match" in capsys.readouterr().out


def test_cli_runs_preflight_and_tiny_smoke_adapters(tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        cli,
        "colab_preflight_report",
        lambda *args, **kwargs: {
            "profile": "smoke",
            "acquisition_executed": False,
            "full_training_executed": False,
        },
    )
    assert (
        main(
            [
                "colab-preflight",
                "--repository-root",
                str(tmp_path),
                "--notebook",
                "fixture.ipynb",
                "--profile",
                "smoke",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["profile"] == "smoke"

    outputs = SmokeOutputs(
        run_id="fixture-run",
        manifest_path=tmp_path / "manifest.json",
        report_path=tmp_path / "report.json",
        bundle_path=tmp_path / "bundle.json",
        prediction_digest="a" * 64,
        resumed=False,
    )
    monkeypatch.setattr(cli, "repository_state", lambda _root: {"commit": "a" * 40, "dirty": False})
    monkeypatch.setattr(cli, "run_smoke_flow", lambda **_kwargs: outputs)
    assert (
        main(
            [
                "smoke-colab",
                "--repository-root",
                str(tmp_path),
                "--vm-root",
                str(tmp_path / "vm"),
                "--drive-root",
                str(tmp_path / "drive"),
                "--notebook",
                "fixture.ipynb",
                "--profile",
                "smoke",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["prediction_digest"] == "a" * 64


def test_cli_rejects_non_smoke_profile_for_smoke_command(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "smoke-colab",
                "--repository-root",
                str(tmp_path),
                "--vm-root",
                str(tmp_path / "vm"),
                "--drive-root",
                str(tmp_path / "drive"),
                "--notebook",
                "fixture.ipynb",
                "--profile",
                "unit",
            ]
        )
        == 1
    )
    assert "requires --profile smoke" in capsys.readouterr().out
