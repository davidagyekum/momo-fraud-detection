from __future__ import annotations

import json
from pathlib import Path

import pytest

from momo_fdvs_ml.feature_schema import (
    FEATURE_NAMES,
    RISK_CLASSES,
    STRUCTURED_FEATURE_SCHEMA_HASH,
)
from momo_fdvs_ml.structured_dataset import load_structured_dataset
from momo_fdvs_ml.structured_model import (
    RANDOM_SEED,
    StructuredModelError,
    Thresholds,
    build_pipeline,
    evaluate_partition,
    load_and_verify_artifact,
    predict_with_bundle,
    runtime_fingerprint,
    select_thresholds,
    train_and_package,
)

ML_ROOT = Path(__file__).resolve().parents[1]
CONTROLLED_ROOT = ML_ROOT / "data" / "controlled"
SOURCE_MANIFEST = CONTROLLED_ROOT / "manifest.csv"
STRUCTURED_CSV = CONTROLLED_ROOT / "structured_features.csv"
TRAINING_COMMIT = "a" * 40


def _dataset():  # type: ignore[no-untyped-def]
    return load_structured_dataset(path=STRUCTURED_CSV, source_manifest_path=SOURCE_MANIFEST)


def test_pipeline_is_column_transformer_random_forest_graph() -> None:
    pipeline = build_pipeline(random_seed=RANDOM_SEED, n_estimators=10)
    assert list(pipeline.named_steps) == ["preprocess", "classifier"]
    assert pipeline.named_steps["classifier"].random_state == RANDOM_SEED
    assert pipeline.named_steps["classifier"].class_weight == "balanced"


def test_validation_threshold_selection_prioritises_correct_three_class_boundaries() -> None:
    labels = list(RISK_CLASSES)
    probabilities = [
        {"GENUINE": 0.95, "SUSPICIOUS": 0.04, "FRAUDULENT": 0.01},
        {"GENUINE": 0.1, "SUSPICIOUS": 0.8, "FRAUDULENT": 0.1},
        {"GENUINE": 0.02, "SUSPICIOUS": 0.08, "FRAUDULENT": 0.9},
    ]
    thresholds = select_thresholds(labels, probabilities)
    assert thresholds.validation_macro_f1 == 1.0
    assert thresholds.validation_fraudulent_recall == 1.0
    assert thresholds.suspicious < thresholds.fraudulent


def test_threshold_selection_rejects_empty_inputs() -> None:
    with pytest.raises(StructuredModelError, match="non-empty"):
        select_thresholds([], [])


def test_controlled_fit_packages_honest_outputs_and_predicts(tmp_path: Path) -> None:
    dataset = _dataset()
    outputs = train_and_package(
        dataset=dataset,
        output_dir=tmp_path / "outputs",
        model_version="structured-rf-controlled-v1",
        training_commit_sha=TRAINING_COMMIT,
    )

    assert outputs.report["acceptance_passed"] is True
    assert outputs.report["dataset_scope"] == "controlled_synthetic_only"
    assert outputs.report["held_out_test"]["sample_count"] == 3
    assert outputs.report["held_out_test"]["source_group_count"] == 1
    assert outputs.report["held_out_test"]["macro_f1"] >= 0.85
    assert outputs.artifact_path.is_file()
    assert outputs.confusion_matrix_path.is_file()
    assert len(outputs.artifact_sha256) == 64
    assert (
        json.loads(outputs.registry_payload_path.read_text(encoding="utf-8"))["metrics"][
            "acceptance_passed"
        ]
        is True
    )

    bundle = load_and_verify_artifact(
        outputs.artifact_path,
        expected_sha256=outputs.artifact_sha256,
        expected_schema_hash=STRUCTURED_FEATURE_SCHEMA_HASH,
    )
    test_x, _, _, _ = dataset.partition("test")
    result = predict_with_bundle(bundle, test_x.iloc[0].to_dict())
    assert result["predicted_class"] in RISK_CLASSES
    assert sum(result["probabilities"].values()) == pytest.approx(1.0)
    assert result["feature_schema_hash"] == STRUCTURED_FEATURE_SCHEMA_HASH


def test_artifact_hash_is_repeatable_for_same_code_data_and_seed(tmp_path: Path) -> None:
    dataset = _dataset()
    first = train_and_package(
        dataset=dataset,
        output_dir=tmp_path / "first",
        model_version="structured-rf-controlled-v1",
        training_commit_sha=TRAINING_COMMIT,
    )
    second = train_and_package(
        dataset=dataset,
        output_dir=tmp_path / "second",
        model_version="structured-rf-controlled-v1",
        training_commit_sha=TRAINING_COMMIT,
    )
    assert first.artifact_sha256 == second.artifact_sha256
    assert first.report["held_out_test"] == second.report["held_out_test"]


def test_corrupt_or_wrong_schema_artifact_is_rejected(tmp_path: Path) -> None:
    outputs = train_and_package(
        dataset=_dataset(),
        output_dir=tmp_path / "outputs",
        model_version="structured-rf-controlled-v1",
        training_commit_sha=TRAINING_COMMIT,
    )
    with pytest.raises(StructuredModelError, match="schema hash mismatch"):
        load_and_verify_artifact(
            outputs.artifact_path,
            expected_sha256=outputs.artifact_sha256,
            expected_schema_hash="0" * 64,
        )
    outputs.artifact_path.write_bytes(outputs.artifact_path.read_bytes() + b"corrupt")
    with pytest.raises(StructuredModelError, match="SHA-256 mismatch"):
        load_and_verify_artifact(
            outputs.artifact_path,
            expected_sha256=outputs.artifact_sha256,
            expected_schema_hash=STRUCTURED_FEATURE_SCHEMA_HASH,
        )


@pytest.mark.parametrize(
    ("version", "commit", "message"),
    [
        ("INVALID VERSION", "a" * 40, "safe lowercase"),
        ("structured-v1", "short", "40 lowercase"),
    ],
)
def test_training_metadata_must_be_safe(
    tmp_path: Path, version: str, commit: str, message: str
) -> None:
    with pytest.raises(StructuredModelError, match=message):
        train_and_package(
            dataset=_dataset(),
            output_dir=tmp_path,
            model_version=version,
            training_commit_sha=commit,
        )


def test_evaluation_rejects_misaligned_arrays() -> None:
    with pytest.raises(StructuredModelError, match="equal length"):
        evaluate_partition(
            ["GENUINE"],
            [],
            thresholds=Thresholds(0.3, 0.7, 1.0, 1.0),
            sample_ids=["one"],
            groups=["group"],
        )


def test_runtime_fingerprint_records_pinned_core_versions() -> None:
    versions = runtime_fingerprint()
    assert versions["scikit_learn"] == "1.9.0"
    assert versions["pandas"] == "3.0.3"
    assert versions["joblib"] == "1.5.3"


def test_all_feature_names_reach_pipeline_input() -> None:
    dataset = _dataset()
    train_x, _, _, _ = dataset.partition("train")
    assert tuple(train_x.columns) == FEATURE_NAMES
