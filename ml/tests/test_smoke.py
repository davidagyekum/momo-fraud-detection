from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from momo_fdvs_ml.colab import ColabFoundationError, load_json_object, validate_run_manifest
from momo_fdvs_ml.smoke import (
    SMOKE_SEED,
    SimulatedRuntimeLoss,
    _image_features,
    _ocr_component,
    _predict_exported,
    run_smoke_flow,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COMMIT = "a" * 40
GIT_STATE = {"commit": COMMIT, "dirty": False}
STARTED_AT = datetime(2026, 8, 10, 14, 31, tzinfo=UTC)
NOTEBOOK = "ml/notebooks/colab/01_tiny_restart_safe_smoke.ipynb"


def _run(tmp_path: Path, *, suffix: str, started_at: datetime = STARTED_AT):
    return run_smoke_flow(
        repository_root=REPOSITORY_ROOT,
        vm_root=tmp_path / f"vm-{suffix}",
        drive_root=tmp_path / f"drive-{suffix}",
        git_state=GIT_STATE,
        notebook=NOTEBOOK,
        seed=SMOKE_SEED,
        started_at=started_at,
    )


def test_smoke_flow_is_deterministic_bounded_non_promotable_and_complete(tmp_path: Path) -> None:
    first = _run(tmp_path, suffix="first")
    second = _run(tmp_path, suffix="second")
    assert first.prediction_digest == second.prediction_digest
    assert len(first.prediction_digest) == 64
    assert first.resumed is False

    report = load_json_object(first.report_path)
    assert report == load_json_object(second.report_path)
    assert report["transaction_rows"] == 15
    assert report["image_count"] == 10
    assert report["image_epochs"] == 1
    assert report["test_partition_accessed"] is False
    assert report["acquisition_executed"] is False
    assert report["full_training_executed"] is False
    assert report["promotable"] is False

    bundle = load_json_object(first.bundle_path)
    assert bundle["prediction_digest"] == first.prediction_digest
    assert bundle["training_scope"] == "tiny_fictitious_smoke_only"
    components = bundle["components"]
    assert isinstance(components, dict)
    assert components["transaction"]["test_rows_accessed"] == 0
    assert components["image"]["test_images_accessed"] == 0
    assert components["ocr"]["ground_truth_match"] is True

    manifest = load_json_object(first.manifest_path)
    validate_run_manifest(manifest)
    assert manifest["status"] == "completed"
    assert len(manifest["checkpoints"]) == 3  # type: ignore[arg-type]
    assert len(manifest["artifacts"]) == 2  # type: ignore[arg-type]
    assert manifest["promotable"] is False


def test_smoke_flow_recovers_same_run_after_simulated_runtime_loss(tmp_path: Path) -> None:
    vm_root = tmp_path / "vm"
    drive_root = tmp_path / "drive"
    with pytest.raises(SimulatedRuntimeLoss, match="transaction"):
        run_smoke_flow(
            repository_root=REPOSITORY_ROOT,
            vm_root=vm_root,
            drive_root=drive_root,
            git_state=GIT_STATE,
            notebook=NOTEBOOK,
            seed=SMOKE_SEED,
            started_at=STARTED_AT,
            stop_after_checkpoint="transaction",
        )
    run_id = "20260810T143100Z_smoke-foundation_aaaaaaaa_seed20260810"
    partial_manifest_path = drive_root / "runs" / run_id / "run_manifest.json"
    partial = load_json_object(partial_manifest_path)
    assert partial["status"] == "running"
    assert len(partial["checkpoints"]) == 1  # type: ignore[arg-type]

    resumed = run_smoke_flow(
        repository_root=REPOSITORY_ROOT,
        vm_root=vm_root,
        drive_root=drive_root,
        git_state=GIT_STATE,
        notebook=NOTEBOOK,
        run_id=run_id,
        seed=SMOKE_SEED,
        started_at=STARTED_AT + timedelta(minutes=5),
    )
    assert resumed.resumed is True
    manifest = load_json_object(resumed.manifest_path)
    sessions = manifest["sessions"]
    assert isinstance(sessions, list)
    assert [session["outcome"] for session in sessions] == ["interrupted", "completed"]
    assert sessions[1]["resumed_from_checkpoint_sha256"] is not None
    assert len(manifest["checkpoints"]) == 3  # type: ignore[arg-type]


def test_smoke_resume_rejects_corrupt_durable_checkpoint(tmp_path: Path) -> None:
    vm_root = tmp_path / "vm"
    drive_root = tmp_path / "drive"
    with pytest.raises(SimulatedRuntimeLoss):
        run_smoke_flow(
            repository_root=REPOSITORY_ROOT,
            vm_root=vm_root,
            drive_root=drive_root,
            git_state=GIT_STATE,
            notebook=NOTEBOOK,
            seed=SMOKE_SEED,
            started_at=STARTED_AT,
            stop_after_checkpoint="transaction",
        )
    run_id = "20260810T143100Z_smoke-foundation_aaaaaaaa_seed20260810"
    local_checkpoint = vm_root / "checkpoints" / run_id / "transaction.json"
    local_checkpoint.unlink()
    durable_checkpoint = drive_root / "checkpoints" / run_id / "transaction.json"
    durable_checkpoint.write_bytes(b"corrupt")
    with pytest.raises(ColabFoundationError, match="durable checkpoint"):
        run_smoke_flow(
            repository_root=REPOSITORY_ROOT,
            vm_root=vm_root,
            drive_root=drive_root,
            git_state=GIT_STATE,
            notebook=NOTEBOOK,
            run_id=run_id,
            seed=SMOKE_SEED,
            started_at=STARTED_AT + timedelta(minutes=5),
        )


def test_smoke_flow_rejects_invalid_stop_git_and_completed_resume(tmp_path: Path) -> None:
    with pytest.raises(ColabFoundationError, match="unknown simulated"):
        run_smoke_flow(
            repository_root=REPOSITORY_ROOT,
            vm_root=tmp_path / "vm",
            drive_root=tmp_path / "drive",
            git_state=GIT_STATE,
            notebook=NOTEBOOK,
            stop_after_checkpoint="unknown",
        )
    with pytest.raises(ColabFoundationError, match="must contain a commit"):
        run_smoke_flow(
            repository_root=REPOSITORY_ROOT,
            vm_root=tmp_path / "vm2",
            drive_root=tmp_path / "drive2",
            git_state={},
            notebook=NOTEBOOK,
        )
    completed = _run(tmp_path, suffix="completed")
    with pytest.raises(ColabFoundationError, match="completed smoke run"):
        run_smoke_flow(
            repository_root=REPOSITORY_ROOT,
            vm_root=tmp_path / "vm-completed",
            drive_root=tmp_path / "drive-completed",
            git_state=GIT_STATE,
            notebook=NOTEBOOK,
            run_id=completed.run_id,
            seed=SMOKE_SEED,
            started_at=STARTED_AT + timedelta(minutes=5),
        )


def test_exported_prediction_supports_binary_and_multiclass() -> None:
    binary = {
        "scaler_mean": [0.0],
        "scaler_scale": [1.0],
        "coefficients": [[1.0]],
        "intercepts": [0.0],
    }
    probabilities = _predict_exported(binary, np.asarray([[0.0], [1.0]]))
    assert probabilities.shape == (2, 2)
    assert np.allclose(probabilities.sum(axis=1), 1.0)
    multiclass = {
        "scaler_mean": [0.0],
        "scaler_scale": [1.0],
        "coefficients": [[-1.0], [0.0], [1.0]],
        "intercepts": [0.0, 0.0, 0.0],
    }
    probabilities = _predict_exported(multiclass, np.asarray([[1.0]]))
    assert probabilities.shape == (1, 3)
    assert np.allclose(probabilities.sum(axis=1), 1.0)


def test_image_feature_extraction_is_fixed_shape_and_deterministic() -> None:
    image_path = REPOSITORY_ROOT / "ml/data/controlled/images/controlled-original-0001.png"
    first = _image_features(image_path)
    second = _image_features(image_path)
    assert first.shape == (6,)
    assert np.array_equal(first, second)
    assert np.isfinite(first).all()


def test_ocr_smoke_rejects_non_synthetic_or_mismatched_truth(tmp_path: Path) -> None:
    fixture_root = tmp_path / "data/fixtures"
    fixture_root.mkdir(parents=True)
    source = json.loads(
        (REPOSITORY_ROOT / "data/fixtures/ocr-truth.fixture.json").read_text(encoding="utf-8")
    )
    source["full_transcript"] = "GHS 42.50 sent. Reference DEMO-REF-0001."
    (fixture_root / "ocr-truth.fixture.json").write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ColabFoundationError, match="explicitly synthetic"):
        _ocr_component(tmp_path)

    source["full_transcript"] = "SYNTHETIC GHS 99.99 Reference DEMO-REF-0001."
    (fixture_root / "ocr-truth.fixture.json").write_text(json.dumps(source), encoding="utf-8")
    with pytest.raises(ColabFoundationError, match="disagrees"):
        _ocr_component(tmp_path)
