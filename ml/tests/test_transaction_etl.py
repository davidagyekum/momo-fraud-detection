from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from momo_fdvs_ml.transaction_etl import (
    FEATURE_CONTRACT_VERSION,
    PREPROCESSOR_VERSION,
    TransactionBuildSpec,
    build_transaction_parquet_dataset,
    fit_training_preprocessor,
    load_non_test_partition,
    scan_transaction_source,
    transaction_feature_contract,
    transform_features,
)
from momo_fdvs_ml.transaction_pipeline import (
    MODEL_FEATURES,
    CanonicalTransaction,
    StepStatistic,
    TransactionPipelineError,
    iter_causal_feature_records,
    plan_temporal_splits,
    source_mapping,
)


def _write_paysim_fixture(path: Path, *, unsorted: bool = False) -> tuple[str, int, int]:
    mapping = source_mapping("paysim")
    steps = list(range(1, 9))
    if unsorted:
        steps[3], steps[4] = steps[4], steps[3]
    positive_count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mapping.expected_columns, lineterminator="\n")
        writer.writeheader()
        for step in steps:
            for offset in range(2):
                label = int(offset == 1 and step % 2 == 0)
                positive_count += label
                writer.writerow(
                    {
                        "step": step,
                        "type": "TRANSFER" if offset == 0 else "CASH_OUT",
                        "amount": float(step * 10 + offset),
                        "nameOrig": f"C{offset}",
                        "oldbalanceOrg": 500,
                        "newbalanceOrig": 400,
                        "nameDest": f"M{step % 3}",
                        "oldbalanceDest": 0,
                        "newbalanceDest": 100,
                        "isFraud": label,
                        "isFlaggedFraud": 0,
                    }
                )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest, 16, positive_count


def _spec(path: Path, *, unsorted: bool = False, **updates: object) -> TransactionBuildSpec:
    digest, rows, positives = _write_paysim_fixture(path, unsorted=unsorted)
    values: dict[str, object] = {
        "dataset_id": "paysim",
        "source_sha256": digest,
        "expected_row_count": rows,
        "expected_positive_count": positives,
        "minimum_partition_positives": 0,
        "shard_size": 3,
    }
    values.update(updates)
    return TransactionBuildSpec(**values)  # type: ignore[arg-type]


def _training_records():
    plan = plan_temporal_splits(
        dataset_id="paysim",
        source_sha256="a" * 64,
        step_statistics=[StepStatistic(step, 1, 0) for step in range(1, 9)],
        minimum_positive_count=0,
    )
    rows = [
        CanonicalTransaction(
            dataset_source="paysim",
            source_row_id=str(index).zfill(64),
            step=step,
            transaction_type="TRANSFER",
            amount=float(step * 10),
            initiator_id="C1",
            recipient_id="M1",
            label_is_fraud=0,
        )
        for index, step in enumerate(range(1, 6), start=1)
    ]
    return list(iter_causal_feature_records(rows, split_plan=plan))


def test_scan_validates_hash_counts_steps_and_sorted_source(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    spec = _spec(path)
    scan = scan_transaction_source(path, spec=spec)

    assert scan.row_count == 16
    assert scan.positive_count == 4
    assert len(scan.step_statistics) == 8
    assert scan.step_statistics[0] == StepStatistic(1, 2, 0)
    assert scan.step_statistics[1] == StepStatistic(2, 2, 1)


def test_scan_streams_the_registered_paysim_entrypoint_from_zip(tmp_path: Path) -> None:
    csv_path = tmp_path / "source.csv"
    _, rows, positives = _write_paysim_fixture(csv_path)
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(csv_path, arcname="registered/source.csv")
    archive_hash = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    spec = TransactionBuildSpec(
        dataset_id="paysim",
        source_sha256=archive_hash,
        expected_row_count=rows,
        expected_positive_count=positives,
        minimum_partition_positives=0,
        shard_size=3,
        entrypoint="registered/source.csv",
    )

    assert scan_transaction_source(archive_path, spec=spec).row_count == rows
    for entrypoint in ("missing.csv", "../source.csv", ""):
        with pytest.raises(TransactionPipelineError, match="entrypoint"):
            scan_transaction_source(
                archive_path,
                spec=TransactionBuildSpec(**{**spec.__dict__, "entrypoint": entrypoint}),
            )


def test_scan_rejects_hash_count_or_order_drift(tmp_path: Path) -> None:
    path = tmp_path / "source.csv"
    spec = _spec(path)
    with pytest.raises(TransactionPipelineError, match="SHA-256"):
        scan_transaction_source(
            path, spec=TransactionBuildSpec(**{**spec.__dict__, "source_sha256": "b" * 64})
        )

    spec = _spec(path, expected_row_count=15)
    with pytest.raises(TransactionPipelineError, match="counts drifted"):
        scan_transaction_source(path, spec=spec)

    spec = _spec(path, unsorted=True)
    with pytest.raises(TransactionPipelineError, match="non-decreasing"):
        scan_transaction_source(path, spec=spec)


def test_end_to_end_private_parquet_build_is_atomic_sealed_and_loadable(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    spec = _spec(source)
    output = tmp_path / "private-output"
    report = build_transaction_parquet_dataset(source_path=source, output_path=output, spec=spec)

    assert report["row_count"] == 16
    assert report["positive_count"] == 4
    assert report["training_executed"] is False
    assert report["locked_test_sealed"] is True
    assert report["locked_test_accessed_for_decisions"] is False
    assert report["raw_actor_ids_exported_as_features"] is False
    assert len(report["partitions"]) == 4  # type: ignore[arg-type]
    assert (output / "split-manifest.json").exists()
    assert (output / "preprocessor.json").exists()
    assert (output / "feature-contract.json").exists()
    assert not list(tmp_path.glob(".private-output.tmp-*"))

    features, labels = load_non_test_partition(dataset_root=output, partition="train")
    assert tuple(features.columns) == MODEL_FEATURES
    assert labels is not None
    assert len(features) == len(labels) == 10
    assert not {
        "source_row_id",
        "dataset_source",
        "initiator_id",
        "recipient_id",
        "isFraud",
    } & set(features.columns)
    without_labels, omitted = load_non_test_partition(
        dataset_root=output, partition="tuning", include_labels=False
    )
    assert len(without_labels) == 2
    assert omitted is None

    provenance = pd.concat(
        [
            pd.read_parquet(path)
            for path in sorted((output / "train" / "provenance").glob("*.parquet"))
        ],
        ignore_index=True,
    )
    assert tuple(provenance.columns) == ("source_row_id", "dataset_source", "partition")
    assert all(provenance["source_row_id"].str.fullmatch(r"[0-9a-f]{64}"))
    assert not provenance["source_row_id"].str.contains("C0|M0", regex=True).any()

    locked_report = next(
        item
        for item in report["partitions"]
        if item["partition"] == "locked_test"  # type: ignore[union-attr]
    )
    assert locked_report["sealed"] is True
    with pytest.raises(TransactionPipelineError, match="prohibited before PR20"):
        load_non_test_partition(dataset_root=output, partition="locked_test")
    with pytest.raises(TransactionPipelineError, match="already exists"):
        build_transaction_parquet_dataset(source_path=source, output_path=output, spec=spec)


def test_parquet_build_is_content_stable_except_runtime_fields(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    spec = _spec(source)
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = build_transaction_parquet_dataset(source_path=source, output_path=first_root, spec=spec)
    second = build_transaction_parquet_dataset(
        source_path=source, output_path=second_root, spec=spec
    )

    assert first["split_manifest_sha256"] == second["split_manifest_sha256"]
    assert first["preprocessor_sha256"] == second["preprocessor_sha256"]
    first_parts = [{k: v for k, v in part.items() if k != "shards"} for part in first["partitions"]]  # type: ignore[union-attr]
    second_parts = [
        {k: v for k, v in part.items() if k != "shards"} for part in second["partitions"]
    ]  # type: ignore[union-attr]
    assert first_parts == second_parts


def test_build_rejects_invalid_shard_size_and_cleans_failed_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.csv"
    spec = _spec(source, shard_size=0)
    with pytest.raises(TransactionPipelineError, match="shard_size"):
        build_transaction_parquet_dataset(
            source_path=source, output_path=tmp_path / "invalid", spec=spec
        )

    spec = _spec(source)

    def fail_parquet(*args: object, **kwargs: object) -> None:
        raise ValueError("fixture writer failure")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_parquet)
    with pytest.raises(TransactionPipelineError, match="governed Parquet"):
        build_transaction_parquet_dataset(
            source_path=source, output_path=tmp_path / "failed", spec=spec
        )
    assert not (tmp_path / "failed").exists()
    assert not list(tmp_path.glob(".failed.tmp-*"))


def test_train_only_preprocessor_and_transform_do_not_refit_later_partitions() -> None:
    records = _training_records()
    preprocessor = fit_training_preprocessor(records)

    assert preprocessor.schema_version == PREPROCESSOR_VERSION
    assert preprocessor.fit_partition == "train"
    assert preprocessor.training_row_count == len(records)
    assert "__UNKNOWN__" in preprocessor.categorical_values["transaction_type"]
    assert len(preprocessor.artifact_sha256) == 64
    row = dict(records[0].features)
    row["transaction_type"] = "UNSEEN_TYPE"
    row["time_since_previous"] = None
    transformed = transform_features(row, preprocessor=preprocessor)
    assert transformed["transaction_type"] == "__UNKNOWN__"
    assert (
        transformed["time_since_previous"]
        == preprocessor.numeric_neutral_values["time_since_previous"]
    )

    later = records[0]
    later = type(later)(
        source_row_id=later.source_row_id,
        dataset_source=later.dataset_source,
        partition="tuning",
        label_is_fraud=later.label_is_fraud,
        features=later.features,
    )
    with pytest.raises(TransactionPipelineError, match="train partition only"):
        fit_training_preprocessor([later])
    with pytest.raises(TransactionPipelineError, match="zero rows"):
        fit_training_preprocessor([])
    with pytest.raises(TransactionPipelineError, match="inference contract"):
        transform_features(
            {key: value for key, value in row.items() if key != "amount"},
            preprocessor=preprocessor,
        )


def test_feature_contract_declares_timing_missingness_and_forbidden_inputs() -> None:
    contract = transaction_feature_contract()
    assert contract["schema_version"] == FEATURE_CONTRACT_VERSION
    assert len(contract["features"]) == len(MODEL_FEATURES)  # type: ignore[arg-type]
    by_name = {item["name"]: item for item in contract["features"]}  # type: ignore[union-attr]
    assert by_name["amount"]["availability"] == "current_transaction"
    assert by_name["prior_24h_mean"]["availability"] == "strictly_prior_steps"
    assert by_name["prior_24h_mean"]["nullable_before_preprocessing"] is True
    assert "raw_actor_identifiers" in contract["forbidden"]  # type: ignore[operator]
    assert contract["screenshot_only_supported"] is False


@pytest.mark.parametrize("partition", ["other", "calibration"])
def test_partition_loader_rejects_unknown_or_missing_shards(tmp_path: Path, partition: str) -> None:
    message = "unknown" if partition == "other" else "missing or incomplete"
    with pytest.raises(TransactionPipelineError, match=message):
        load_non_test_partition(dataset_root=tmp_path, partition=partition)


def test_partition_loader_rejects_feature_column_drift(tmp_path: Path) -> None:
    feature_dir = tmp_path / "train" / "features"
    label_dir = tmp_path / "train" / "labels"
    feature_dir.mkdir(parents=True)
    label_dir.mkdir(parents=True)
    pd.DataFrame([{"wrong": 1}]).to_parquet(feature_dir / "part-00000.parquet", index=False)
    pd.DataFrame([{"label_is_fraud": 0}]).to_parquet(label_dir / "part-00000.parquet", index=False)
    with pytest.raises(TransactionPipelineError, match="feature columns drifted"):
        load_non_test_partition(dataset_root=tmp_path, partition="train")


def test_build_report_and_contract_json_contain_no_raw_actor_ids(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    spec = _spec(source)
    output = tmp_path / "private"
    build_transaction_parquet_dataset(source_path=source, output_path=output, spec=spec)
    safe_text = "\n".join(
        (output / name).read_text(encoding="utf-8")
        for name in (
            "build-report.json",
            "split-manifest.json",
            "preprocessor.json",
            "feature-contract.json",
        )
    )
    assert "C0" not in safe_text
    assert "M0" not in safe_text
    assert str(source) not in safe_text
    assert json.loads((output / "build-report.json").read_text())["training_executed"] is False
