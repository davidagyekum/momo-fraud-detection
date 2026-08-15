from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
import pandas as pd
import pytest

from momo_fdvs_ml.colab import validate_run_manifest
from momo_fdvs_ml.manifest import sha256_file
from momo_fdvs_ml.transaction_etl import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from momo_fdvs_ml.transaction_model import (
    ARTIFACT_FORMAT,
    MODEL_CONTRACT_VERSION,
    MODEL_NAME,
    BinaryCalibrator,
    CandidateSpec,
    FrozenPreprocessor,
    ThresholdArtifact,
    TransactionModelError,
    TransactionTrainingConfig,
    apply_frozen_preprocessor,
    binary_metrics,
    build_candidate_pipeline,
    classify_transaction_risk,
    compatibility_risk_class,
    default_training_config,
    evaluate_external_tuning_partition,
    load_and_verify_transaction_artifact,
    load_pr15_partition,
    load_training_config,
    predict_transaction_probability,
    select_risk_thresholds,
    train_and_package_transaction_core,
    verify_pr14_bundle,
)
from momo_fdvs_ml.transaction_pipeline import MODEL_FEATURES


def _json_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _feature_frame(rows: int, *, unknown_category: bool = False) -> pd.DataFrame:
    values: dict[str, list[object]] = {}
    for index, name in enumerate(NUMERIC_FEATURES):
        values[name] = [float(row + index + 1) for row in range(rows)]
    categorical_values = {
        "transaction_type": "TRANSFER",
        "initiator_role": "CUSTOMER",
        "recipient_role": "MERCHANT",
        "sequence_pattern": "START->TRANSFER",
    }
    for name in CATEGORICAL_FEATURES:
        values[name] = [categorical_values[name]] * rows
    if unknown_category:
        values["transaction_type"][0] = "UNKNOWN_TYPE"
    return pd.DataFrame(values, columns=list(MODEL_FEATURES))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_partition(root: Path, partition: str, rows: int) -> dict[str, object]:
    feature_path = root / partition / "features" / "part-00000.parquet"
    label_path = root / partition / "labels" / "part-00000.parquet"
    feature_path.parent.mkdir(parents=True, exist_ok=True)
    label_path.parent.mkdir(parents=True, exist_ok=True)
    frame = _feature_frame(rows, unknown_category=partition == "tuning")
    labels = pd.DataFrame({"label_is_fraud": [index % 2 for index in range(rows)]})
    frame.to_parquet(feature_path, index=False)
    labels.to_parquet(label_path, index=False)
    return {
        "partition": partition,
        "sealed": False,
        "row_count": rows,
        "positive_count": rows // 2,
        "shards": [
            {
                "index": 0,
                "row_count": rows,
                "features_sha256": sha256_file(feature_path),
                "labels_sha256": sha256_file(label_path),
                "provenance_sha256": "f" * 64,
            }
        ],
    }


def _pr14_bundle(tmp_path: Path, *, dataset_id: str = "paysim") -> Path:
    root = tmp_path / f"{dataset_id}-pr14"
    root.mkdir(parents=True)
    numeric = {name: 0.0 for name in NUMERIC_FEATURES}
    categorical = {
        "transaction_type": ["TRANSFER", "__UNKNOWN__"],
        "initiator_role": ["CUSTOMER", "__UNKNOWN__"],
        "recipient_role": ["MERCHANT", "__UNKNOWN__"],
        "sequence_pattern": ["START->TRANSFER", "__UNKNOWN__"],
    }
    preprocessor_payload = {
        "schema_version": "transaction-core-preprocessor-v1",
        "fit_partition": "train",
        "numeric_neutral_values": numeric,
        "categorical_values": categorical,
        "training_row_count": 40,
    }
    preprocessor_hash = _json_hash(preprocessor_payload)
    _write_json(
        root / "preprocessor.json",
        {**preprocessor_payload, "artifact_sha256": preprocessor_hash},
    )
    split_hash = {"paysim": "b", "momtsim-v1": "c", "momtsim-v2": "d"}[dataset_id] * 64
    source_hash = {"paysim": "a", "momtsim-v1": "e", "momtsim-v2": "f"}[dataset_id] * 64
    _write_json(
        root / "split-manifest.json",
        {
            "schema_version": "transaction-temporal-split-v1",
            "dataset_id": dataset_id,
            "manifest_sha256": split_hash,
            "locked_test_accessed_for_decisions": False,
        },
    )
    partitions = [
        _write_partition(root, "train", 40),
        _write_partition(root, "tuning", 20),
        _write_partition(root, "calibration", 40),
        {
            "partition": "locked_test",
            "sealed": True,
            "row_count": 20,
            "positive_count": 10,
            "shards": [],
        },
    ]
    _write_json(
        root / "build-report.json",
        {
            "schema_version": "transaction-etl-report-v1",
            "dataset_id": dataset_id,
            "source_sha256": source_hash,
            "split_manifest_sha256": split_hash,
            "preprocessor_sha256": preprocessor_hash,
            "partitions": partitions,
            "locked_test_sealed": True,
            "locked_test_accessed_for_decisions": False,
            "training_executed": False,
        },
    )
    return root


def test_default_search_stays_within_blueprint_maxima() -> None:
    config = default_training_config()
    counts = {
        family: sum(candidate.family == family for candidate in config.candidates)
        for family in ("dummy", "logistic", "histogram", "xgboost", "forest")
    }
    assert counts["dummy"] == 1
    assert counts["logistic"] <= 8
    assert counts["histogram"] <= 20
    assert counts["xgboost"] <= 30
    assert counts["forest"] <= 12
    assert config.seeds == (42, 123, 2026)
    repository_config = Path(__file__).parents[1] / "configs" / "transaction_core_default.json"
    assert load_training_config(repository_config).config_sha256 == config.config_sha256


def test_pr14_bundle_verification_and_partition_loading(tmp_path: Path) -> None:
    root = _pr14_bundle(tmp_path)
    bundle = verify_pr14_bundle(root)

    assert bundle.dataset_id == "paysim"
    frame, labels = load_pr15_partition(bundle, "tuning")
    assert tuple(frame.columns) == MODEL_FEATURES
    assert frame.iloc[0]["transaction_type"] == "__UNKNOWN__"
    assert set(labels) == {0, 1}
    with pytest.raises(TransactionModelError, match="train, tuning, or calibration"):
        load_pr15_partition(bundle, "locked_test")


def test_pr14_bundle_rejects_tampered_non_test_shard(tmp_path: Path) -> None:
    root = _pr14_bundle(tmp_path)
    feature_path = root / "tuning" / "features" / "part-00000.parquet"
    feature_path.write_bytes(feature_path.read_bytes() + b"tamper")

    with pytest.raises(TransactionModelError, match="shard hash drifted"):
        verify_pr14_bundle(root)


def test_frozen_preprocessor_never_learns_later_categories() -> None:
    preprocessor = FrozenPreprocessor(
        numeric_neutral_values={name: 7.0 for name in NUMERIC_FEATURES},
        categorical_values={name: ("KNOWN", "__UNKNOWN__") for name in CATEGORICAL_FEATURES},
        artifact_sha256="a" * 64,
        training_row_count=10,
    )
    frame = _feature_frame(2, unknown_category=True)
    frame.loc[0, NUMERIC_FEATURES[0]] = np.nan
    transformed = apply_frozen_preprocessor(frame, preprocessor)

    assert transformed.loc[0, NUMERIC_FEATURES[0]] == 7.0
    assert transformed.loc[0, "transaction_type"] == "__UNKNOWN__"


def test_candidate_adapters_and_xgboost_unavailable_state(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    preprocessor = FrozenPreprocessor(
        numeric_neutral_values={name: 0.0 for name in NUMERIC_FEATURES},
        categorical_values={
            name: (
                "TRANSFER" if name == "transaction_type" else "CUSTOMER",
                "__UNKNOWN__",
            )
            for name in CATEGORICAL_FEATURES
        },
        artifact_sha256="a" * 64,
        training_row_count=10,
    )
    for family in ("dummy", "logistic", "histogram", "forest"):
        pipeline = build_candidate_pipeline(
            CandidateSpec(family, {}),
            preprocessor=preprocessor,
            random_seed=42,
            positive_weight=3.0,
        )
        assert tuple(pipeline.named_steps) == ("features", "classifier")

    def missing(name: str):  # type: ignore[no-untyped-def]
        if name == "xgboost":
            raise ImportError(name)
        raise AssertionError(name)

    monkeypatch.setattr("momo_fdvs_ml.transaction_model.importlib.import_module", missing)
    with pytest.raises(TransactionModelError, match="pinned training dependency"):
        build_candidate_pipeline(
            CandidateSpec("xgboost", {}),
            preprocessor=preprocessor,
            random_seed=42,
            positive_weight=3.0,
        )


def test_metrics_thresholds_and_compatibility_projection() -> None:
    labels = [0, 0, 0, 1, 1, 1]
    scores = [0.01, 0.2, 0.4, 0.55, 0.8, 0.99]
    metrics = binary_metrics(labels, scores)
    thresholds = select_risk_thresholds(
        labels,
        scores,
        medium_fpr_cap=0.34,
        high_precision_target=0.9,
    )

    assert metrics["average_precision"] == 1.0
    assert 0 <= thresholds.medium <= thresholds.high <= 1
    assert classify_transaction_risk(0.0, thresholds) == "low_risk"
    assert classify_transaction_risk(thresholds.high, thresholds) == "high_risk"
    assert compatibility_risk_class("medium_risk") == "SUSPICIOUS"
    with pytest.raises(TransactionModelError, match="finite"):
        classify_transaction_risk(float("nan"), thresholds)


def test_tiny_pr15_training_exports_reloadable_non_final_bundle(tmp_path: Path) -> None:
    dataset_root = _pr14_bundle(tmp_path)
    external_root = _pr14_bundle(tmp_path, dataset_id="momtsim-v1")
    config = TransactionTrainingConfig(
        candidates=(
            CandidateSpec("dummy", {"strategy": "prior"}),
            CandidateSpec("logistic", {"C": 1.0, "max_iter": 100}),
        ),
        forest_max_rows=100,
        minimum_isotonic_positives=100,
        parity_rows=12,
    )
    outputs = train_and_package_transaction_core(
        dataset_root=dataset_root,
        output_dir=tmp_path / "outputs",
        model_version="transaction-core-test-v1",
        training_commit_sha="d" * 40,
        notebook="ml/notebooks/colab/04_train_transaction_models.ipynb",
        dependency_lock_sha256="e" * 64,
        config=config,
        external_dataset_roots=(external_root,),
    )

    assert outputs.report["full_training_executed"] is True
    assert outputs.report["locked_test_accessed_for_decisions"] is False
    assert outputs.report["final_evaluation_executed"] is False
    assert outputs.report["not_real_world_probability"] is True
    assert outputs.report["external_tuning_evaluations"][0]["external_dataset_id"] == ("momtsim-v1")
    assert outputs.artifact_sha256 == sha256_file(outputs.artifact_path)
    verified = load_and_verify_transaction_artifact(
        outputs.artifact_path, expected_sha256=outputs.artifact_sha256
    )
    raw = _feature_frame(3)
    probabilities = predict_transaction_probability(verified, raw)
    assert probabilities.shape == (3,)
    assert np.all((probabilities >= 0) & (probabilities <= 1))
    with pytest.raises(TransactionModelError, match="different source"):
        evaluate_external_tuning_partition(verified, external_dataset_root=dataset_root)
    manifest = json.loads(outputs.run_manifest_path.read_text(encoding="utf-8"))
    validate_run_manifest(manifest)
    assert manifest["full_training_executed"] is True
    assert manifest["promotable"] is False


def test_artifact_hash_and_contract_fail_closed(tmp_path: Path) -> None:
    artifact = tmp_path / "bundle.joblib"
    payload = {
        "artifact_format": ARTIFACT_FORMAT,
        "model_name": MODEL_NAME,
        "model_contract_version": MODEL_CONTRACT_VERSION,
        "feature_names": MODEL_FEATURES,
        "locked_test_accessed": False,
        "not_real_world_probability": True,
        "thresholds": ThresholdArtifact(0.4, 0.8, "medium", "high", 0.5, 0.1, 0.9, 0.5),
        "preprocessor": FrozenPreprocessor({}, {}, "a" * 64, 1),
        "model": object(),
        "calibrator": BinaryCalibrator("sigmoid", object()),
    }
    joblib.dump(payload, artifact)

    with pytest.raises(TransactionModelError, match="hash mismatch"):
        load_and_verify_transaction_artifact(artifact, expected_sha256="0" * 64)


class _PredictValues:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def predict(self, scores: np.ndarray) -> np.ndarray:  # type: ignore[type-arg]
        return np.asarray(self.values[: len(scores)], dtype=float)


def test_calibrator_and_prediction_contract_errors() -> None:
    isotonic = BinaryCalibrator("isotonic", _PredictValues([0.2, 0.8]))
    assert isotonic.transform([0.1, 0.9]).tolist() == [0.2, 0.8]
    with pytest.raises(TransactionModelError, match=r"unknown.*method"):
        BinaryCalibrator("unknown", object()).transform([0.5])
    with pytest.raises(TransactionModelError, match="non-finite"):
        BinaryCalibrator("isotonic", _PredictValues([float("nan")])).transform([0.5])
    with pytest.raises(TransactionModelError, match="frozen preprocessor"):
        predict_transaction_probability({}, _feature_frame(1))
    with pytest.raises(TransactionModelError, match="incomplete"):
        predict_transaction_probability(
            {
                "preprocessor": FrozenPreprocessor({}, {}, "a" * 64, 1),
                "model": None,
                "calibrator": None,
            },
            _feature_frame(1),
        )


def test_config_file_and_policy_errors_are_fail_closed(tmp_path: Path) -> None:
    config_path = Path(__file__).parents[1] / "configs" / "transaction_core_default.json"
    original = json.loads(config_path.read_text(encoding="utf-8"))
    mutations = [
        lambda value: value.update(extra=True),
        lambda value: value.update(schema_version="bad"),
        lambda value: value.update(candidates=["bad"]),
        lambda value: value.update(candidates=[{"family": 7, "parameters": {}}]),
        lambda value: value.update(candidates=[]),
        lambda value: value.update(candidates=[{"family": "unknown", "parameters": {}}]),
        lambda value: value.update(candidates=[{"family": "dummy", "parameters": {}}] * 2),
        lambda value: value.update(seeds=[42]),
        lambda value: value.update(tuning_fpr_cap=0),
        lambda value: value.update(minimum_isotonic_positives=0),
        lambda value: value.update(parity_rows="bad"),
    ]
    for index, mutation in enumerate(mutations):
        payload = json.loads(json.dumps(original))
        mutation(payload)
        path = tmp_path / f"bad-{index}.json"
        _write_json(path, payload)
        with pytest.raises(TransactionModelError):
            load_training_config(path)
    with pytest.raises(TransactionModelError, match="unable to read"):
        load_training_config(tmp_path / "missing.json")
    assert load_training_config(None).seeds == (42, 123, 2026)


def test_pr14_metadata_drift_cases_fail_closed(tmp_path: Path) -> None:
    cases = [
        ("schema_version", "bad", "version"),
        ("locked_test_sealed", False, "locked-test boundary"),
        ("dataset_id", "unknown", "dataset identity"),
        ("source_sha256", "bad", "content identities"),
        ("split_manifest_sha256", "c" * 64, "split manifest identity"),
        ("partitions", None, "partition report"),
    ]
    for index, (field, value, message) in enumerate(cases):
        root = _pr14_bundle(tmp_path / str(index))
        report_path = root / "build-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report[field] = value
        _write_json(report_path, report)
        with pytest.raises(TransactionModelError, match=message):
            verify_pr14_bundle(root)

    root = _pr14_bundle(tmp_path / "split-access")
    split_path = root / "split-manifest.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    split["locked_test_accessed_for_decisions"] = True
    _write_json(split_path, split)
    with pytest.raises(TransactionModelError, match="exposes"):
        verify_pr14_bundle(root)


def _rewrite_preprocessor(root: Path, mutation) -> None:  # type: ignore[no-untyped-def]
    path = root / "preprocessor.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("artifact_sha256")
    mutation(payload)
    digest = _json_hash(payload)
    _write_json(path, {**payload, "artifact_sha256": digest})
    report_path = root / "build-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["preprocessor_sha256"] = digest
    _write_json(report_path, report)


def test_pr14_preprocessor_and_partition_contract_drift_fail_closed(tmp_path: Path) -> None:
    mutations = [
        (lambda value: value.update(fit_partition="tuning"), "train-only"),
        (lambda value: value["numeric_neutral_values"].pop(NUMERIC_FEATURES[0]), "numeric"),
        (lambda value: value["categorical_values"].pop(CATEGORICAL_FEATURES[0]), "categorical"),
        (lambda value: value.update(training_row_count=0), "incomplete"),
    ]
    for index, (mutation, message) in enumerate(mutations):
        root = _pr14_bundle(tmp_path / str(index))
        _rewrite_preprocessor(root, mutation)
        with pytest.raises(TransactionModelError, match=message):
            verify_pr14_bundle(root)

    for index, mutation in enumerate(
        [
            lambda report: report["partitions"][0].update(sealed=True),
            lambda report: report["partitions"][0].update(shards=[]),
            lambda report: report["partitions"][0]["shards"][0].update(index="bad"),
            lambda report: report["partitions"][3].update(sealed=False),
        ]
    ):
        root = _pr14_bundle(tmp_path / f"partition-{index}")
        report_path = root / "build-report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        mutation(report)
        _write_json(report_path, report)
        with pytest.raises(TransactionModelError):
            verify_pr14_bundle(root)


def test_artifact_and_candidate_contract_variants_fail_closed(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(TransactionModelError, match="malformed"):
        load_and_verify_transaction_artifact(tmp_path / "none", expected_sha256="bad")
    corrupt = tmp_path / "corrupt.joblib"
    corrupt.write_bytes(b"not-joblib")
    with pytest.raises(TransactionModelError, match="unable to load"):
        load_and_verify_transaction_artifact(corrupt, expected_sha256=sha256_file(corrupt))
    for index, payload in enumerate(
        [
            ["not", "a", "mapping"],
            {"artifact_format": "bad"},
            {
                "artifact_format": ARTIFACT_FORMAT,
                "model_name": MODEL_NAME,
                "model_contract_version": MODEL_CONTRACT_VERSION,
                "feature_names": MODEL_FEATURES,
                "locked_test_accessed": False,
                "not_real_world_probability": True,
            },
        ]
    ):
        path = tmp_path / f"invalid-{index}.joblib"
        joblib.dump(payload, path)
        with pytest.raises(TransactionModelError):
            load_and_verify_transaction_artifact(path, expected_sha256=sha256_file(path))

    monkeypatch.setattr(
        "momo_fdvs_ml.transaction_model.importlib.import_module",
        lambda name: SimpleNamespace(),
    )
    preprocessor = FrozenPreprocessor(
        {name: 0.0 for name in NUMERIC_FEATURES},
        {name: ("__UNKNOWN__",) for name in CATEGORICAL_FEATURES},
        "a" * 64,
        1,
    )
    with pytest.raises(TransactionModelError, match="XGBClassifier"):
        build_candidate_pipeline(
            CandidateSpec("xgboost", {}),
            preprocessor=preprocessor,
            random_seed=42,
            positive_weight=1.0,
        )
    with pytest.raises(TransactionModelError, match="unsupported"):
        build_candidate_pipeline(
            CandidateSpec("unknown", {}),
            preprocessor=preprocessor,
            random_seed=42,
            positive_weight=1.0,
        )


def test_public_validation_errors_cover_input_boundaries(tmp_path: Path) -> None:
    thresholds = ThresholdArtifact(0.8, 0.4, "bad", "bad", 0, 0, 0, 0)
    with pytest.raises(TransactionModelError, match="thresholds are invalid"):
        classify_transaction_risk(0.5, thresholds)
    with pytest.raises(TransactionModelError, match="unknown transaction risk band"):
        compatibility_risk_class("unknown")
    with pytest.raises(TransactionModelError, match="aligned two-class"):
        binary_metrics([0, 0], [0.1, 0.2])
    with pytest.raises(TransactionModelError, match="aligned two-class"):
        select_risk_thresholds([0, 0], [0.1, 0.2], medium_fpr_cap=0.1, high_precision_target=0.9)
    raw = _feature_frame(1).drop(columns=[MODEL_FEATURES[0]])
    preprocessor = FrozenPreprocessor({}, {}, "a" * 64, 1)
    with pytest.raises(TransactionModelError, match="feature frame drifted"):
        apply_frozen_preprocessor(raw, preprocessor)
    common = {
        "dataset_root": tmp_path,
        "output_dir": tmp_path / "output",
        "model_version": "transaction-core-v1",
        "training_commit_sha": "a" * 40,
        "notebook": "ml/notebooks/colab/04_train_transaction_models.ipynb",
        "dependency_lock_sha256": "b" * 64,
    }
    for field, value, message in [
        ("training_commit_sha", "bad", "training commit"),
        ("model_version", "BAD VERSION", "model version"),
        ("dependency_lock_sha256", "bad", "dependency lock"),
    ]:
        arguments = {**common, field: value}
        with pytest.raises(TransactionModelError, match=message):
            train_and_package_transaction_core(**arguments)
