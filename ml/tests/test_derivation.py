from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from momo_fdvs_ml.cli import main
from momo_fdvs_ml.derivation import (
    DerivationError,
    derive_deduplicated_transactions,
    load_deduplication_manifest,
    load_deduplication_request,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
HEADER = ["step", "type", "amount", "sender", "recipient", "isFraud"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "step,type,amount,sender,recipient,isFraud\n"
        "1,PAYMENT,10.0,A,B,0\n"
        "2,TRANSFER,20.0,C,D,1\n"
        "1,PAYMENT,10.0,A,B,0\n"
        "2,TRANSFER,20.0,C,D,1\n"
        "3,CASH_OUT,30.0,E,F,1\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _request(path: Path, source: Path, **updates: object) -> Path:
    payload: dict[str, object] = {
        "schema_version": "transaction-deduplication-request-v1",
        "dataset_id": "momtsim-v2",
        "source_path": str(source.resolve()),
        "expected_source_sha256": _sha256(source),
        "expected_source_size_bytes": source.stat().st_size,
        "source_dataset_version": "2",
        "derived_dataset_version": "2-derived-exact-dedup-v1",
        "required_columns": HEADER,
        "label_column": "isFraud",
        "positive_values": ["1"],
        "created_at": "2026-08-11T09:00:00Z",
        "decision_reference": "ADR-027",
        "transformation_version": "exact-row-first-occurrence-v1",
        "acknowledgements": {
            "preserve_source": True,
            "private_output": True,
            "no_splits": True,
            "no_training": True,
        },
    }
    payload.update(updates)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _derive(tmp_path: Path, *, output_name: str = "derived.csv"):
    private = tmp_path / "private"
    private.mkdir(exist_ok=True)
    source = _source(private / "official.csv")
    request = _request(tmp_path / f"{output_name}.request.json", source)
    return source, derive_deduplicated_transactions(
        request_path=request,
        allowed_source_root=private,
        allowed_output_root=private,
        output_path=(private / output_name).resolve(),
        manifest_path=tmp_path / f"{output_name}.manifest.json",
    )


def test_derivation_preserves_first_occurrence_and_emits_safe_aggregate_manifest(
    tmp_path: Path,
) -> None:
    source, outputs = _derive(tmp_path)
    original = source.read_bytes()
    assert outputs.output_path.read_text(encoding="utf-8").splitlines() == [
        "step,type,amount,sender,recipient,isFraud",
        "1,PAYMENT,10.0,A,B,0",
        "2,TRANSFER,20.0,C,D,1",
        "3,CASH_OUT,30.0,E,F,1",
    ]
    manifest = outputs.manifest
    assert manifest["source_row_count"] == 5
    assert manifest["output_row_count"] == 3
    assert manifest["removed_duplicate_row_count"] == 2
    assert manifest["duplicate_group_count"] == 2
    assert manifest["max_duplicate_group_size"] == 2
    assert manifest["source_positive_count"] == 3
    assert manifest["output_positive_count"] == 2
    assert manifest["removed_positive_count"] == 1
    assert manifest["preserved_row_policy"] == "first_occurrence_in_source_order"
    assert manifest["source_bytes_modified"] is False
    assert manifest["output_bytes_committed"] is False
    assert manifest["splits_created"] is False
    assert manifest["training_executed"] is False
    assert manifest["promotable_for_training"] is False
    assert source.read_bytes() == original


def test_derivation_is_byte_deterministic(tmp_path: Path) -> None:
    source, first = _derive(tmp_path, output_name="first.csv")
    request = _request(tmp_path / "second.request.json", source)
    private = source.parent
    second = derive_deduplicated_transactions(
        request_path=request,
        allowed_source_root=private,
        allowed_output_root=private,
        output_path=(private / "second.csv").resolve(),
        manifest_path=tmp_path / "second.manifest.json",
    )
    assert first.output_path.read_bytes() == second.output_path.read_bytes()
    assert first.manifest == second.manifest


def test_identity_mismatch_fails_before_output(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir()
    source = _source(private / "official.csv")
    request = _request(tmp_path / "request.json", source, expected_source_sha256="0" * 64)
    output = (private / "derived.csv").resolve()
    manifest = tmp_path / "manifest.json"
    with pytest.raises(DerivationError, match="SHA-256"):
        derive_deduplicated_transactions(
            request_path=request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=output,
            manifest_path=manifest,
        )
    assert not output.exists()
    assert not manifest.exists()


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"schema_version": "old"}, "unsupported"),
        ({"decision_reference": "ADR-999"}, "ADR-027"),
        ({"transformation_version": "drop-random-row"}, "unsupported"),
        ({"expected_source_sha256": "bad"}, "lowercase SHA-256"),
        ({"required_columns": ["step", "step"]}, "unique"),
        ({"label_column": "missing"}, "present"),
        ({"positive_values": []}, "non-empty"),
        ({"created_at": "2026-08-11"}, "timezone"),
        (
            {
                "acknowledgements": {
                    "preserve_source": True,
                    "private_output": True,
                    "no_splits": True,
                    "no_training": False,
                }
            },
            "must be true",
        ),
    ],
)
def test_request_validation_is_fail_closed(
    tmp_path: Path, updates: dict[str, object], message: str
) -> None:
    source = _source(tmp_path / "official.csv")
    request = _request(tmp_path / "request.json", source, **updates)
    with pytest.raises(DerivationError, match=message):
        load_deduplication_request(request)


def test_request_rejects_invalid_shapes_and_timestamps(tmp_path: Path) -> None:
    source = _source(tmp_path / "official.csv")
    request = _request(tmp_path / "request.json", source)
    payload = json.loads(request.read_text(encoding="utf-8"))
    payload["unknown"] = True
    request.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DerivationError, match="unknown"):
        load_deduplication_request(request)
    request.write_text("[]", encoding="utf-8")
    with pytest.raises(DerivationError, match="must contain an object"):
        load_deduplication_request(request)
    request.write_text("{", encoding="utf-8")
    with pytest.raises(DerivationError, match="unable to load"):
        load_deduplication_request(request)
    request = _request(tmp_path / "request.json", source, dataset_id="")
    with pytest.raises(DerivationError, match="non-empty string"):
        load_deduplication_request(request)
    request = _request(tmp_path / "request.json", source, expected_source_size_bytes=False)
    with pytest.raises(DerivationError, match="positive integer"):
        load_deduplication_request(request)
    request = _request(
        tmp_path / "request.json",
        source,
        source_dataset_version="2",
        derived_dataset_version="2",
    )
    with pytest.raises(DerivationError, match="must differ"):
        load_deduplication_request(request)
    request = _request(tmp_path / "request.json", source, created_at="not-a-date")
    with pytest.raises(DerivationError, match="ISO-8601"):
        load_deduplication_request(request)
    request = _request(tmp_path / "request.json", source, acknowledgements=[])
    with pytest.raises(DerivationError, match="must contain an object"):
        load_deduplication_request(request)


def test_path_identity_header_and_noop_failures_leave_no_derived_output(
    tmp_path: Path,
) -> None:
    private = tmp_path / "private"
    private.mkdir()
    source = _source(private / "official.csv")
    output = (private / "derived.csv").resolve()

    relative_request = _request(tmp_path / "relative.json", source, source_path="official.csv")
    with pytest.raises(DerivationError, match="must be absolute"):
        derive_deduplicated_transactions(
            request_path=relative_request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=output,
            manifest_path=tmp_path / "relative.manifest.json",
        )

    outside = _source(tmp_path / "outside.csv")
    outside_request = _request(tmp_path / "outside.json", outside)
    with pytest.raises(DerivationError, match="approved private root"):
        derive_deduplicated_transactions(
            request_path=outside_request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=output,
            manifest_path=tmp_path / "outside.manifest.json",
        )

    directory_request = _request(tmp_path / "directory.json", source, source_path=str(private))
    with pytest.raises(DerivationError, match="regular file"):
        derive_deduplicated_transactions(
            request_path=directory_request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=output,
            manifest_path=tmp_path / "directory.manifest.json",
        )

    request = _request(tmp_path / "request.json", source)
    with pytest.raises(DerivationError, match="output_path must be absolute"):
        derive_deduplicated_transactions(
            request_path=request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=Path("derived.csv"),
            manifest_path=tmp_path / "relative-output.manifest.json",
        )
    with pytest.raises(DerivationError, match="approved private root"):
        derive_deduplicated_transactions(
            request_path=request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=(tmp_path / "outside" / "derived.csv").resolve(),
            manifest_path=tmp_path / "outside-output.manifest.json",
        )
    with pytest.raises(DerivationError, match=r"\.csv extension"):
        derive_deduplicated_transactions(
            request_path=request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=(private / "derived.txt").resolve(),
            manifest_path=tmp_path / "extension.manifest.json",
        )

    size_request = _request(
        tmp_path / "size.json",
        source,
        expected_source_size_bytes=source.stat().st_size + 1,
    )
    with pytest.raises(DerivationError, match="byte size"):
        derive_deduplicated_transactions(
            request_path=size_request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=output,
            manifest_path=tmp_path / "size.manifest.json",
        )

    header_request = _request(
        tmp_path / "header.json", source, required_columns=list(reversed(HEADER))
    )
    with pytest.raises(DerivationError, match="header"):
        derive_deduplicated_transactions(
            request_path=header_request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=output,
            manifest_path=tmp_path / "header.manifest.json",
        )
    assert not output.exists()

    unique = private / "unique.csv"
    unique.write_text(
        "step,type,amount,sender,recipient,isFraud\n1,PAYMENT,1,A,B,0\n",
        encoding="utf-8",
    )
    unique_request = _request(tmp_path / "unique.json", unique)
    with pytest.raises(DerivationError, match="no exact duplicate"):
        derive_deduplicated_transactions(
            request_path=unique_request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=output,
            manifest_path=tmp_path / "unique.manifest.json",
        )
    assert not output.exists()


def test_committed_manifest_loader_rejects_unsafe_or_inconsistent_evidence(
    tmp_path: Path,
) -> None:
    _, outputs = _derive(tmp_path)
    assert load_deduplication_manifest(outputs.manifest_path) == outputs.manifest
    mutations = [
        (lambda value: value.update(schema_version="old"), "unsupported"),
        (lambda value: value.update(source_sha256="bad"), "lowercase SHA-256"),
        (lambda value: value.update(training_executed=True), "unsafe"),
        (lambda value: value.update(output_size_bytes=-1), "non-negative"),
        (lambda value: value.update(output_row_count=5), "row counts"),
        (lambda value: value.update(duplicate_group_count=0), "duplicate counts"),
        (lambda value: value.update(removed_positive_count=99), "positive counts"),
    ]
    for index, (mutation, message) in enumerate(mutations):
        payload = dict(outputs.manifest)
        mutation(payload)
        path = tmp_path / f"bad-{index}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(DerivationError, match=message):
            load_deduplication_manifest(path)
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(DerivationError, match="unable to load"):
        load_deduplication_manifest(malformed)
    malformed.write_text("[]", encoding="utf-8")
    with pytest.raises(DerivationError, match="must contain an object"):
        load_deduplication_manifest(malformed)


def test_derivation_refuses_existing_output_and_source_overwrite(tmp_path: Path) -> None:
    private = tmp_path / "private"
    private.mkdir()
    source = _source(private / "official.csv")
    request = _request(tmp_path / "request.json", source)
    with pytest.raises(DerivationError, match="official source"):
        derive_deduplicated_transactions(
            request_path=request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=source.resolve(),
            manifest_path=tmp_path / "source.manifest.json",
        )
    existing = private / "existing.csv"
    existing.write_text("occupied", encoding="utf-8")
    with pytest.raises(DerivationError, match="already exist"):
        derive_deduplicated_transactions(
            request_path=request,
            allowed_source_root=private,
            allowed_output_root=private,
            output_path=existing.resolve(),
            manifest_path=tmp_path / "existing.manifest.json",
        )


def test_cli_derivation_reports_only_safe_summary(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    private = tmp_path / "private"
    private.mkdir()
    source = _source(private / "official.csv")
    request = _request(tmp_path / "request.json", source)
    output = (private / "derived.csv").resolve()
    manifest = tmp_path / "manifest.json"
    assert (
        main(
            [
                "derive-deduplicated-transactions",
                "--request",
                str(request),
                "--allowed-source-root",
                str(private),
                "--allowed-output-root",
                str(private),
                "--output",
                str(output),
                "--manifest-output",
                str(manifest),
            ]
        )
        == 0
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["removed_duplicate_row_count"] == 2
    assert summary["source_bytes_modified"] is False
    assert summary["splits_created"] is False
    assert summary["training_executed"] is False
    assert str(source) not in json.dumps(summary)


def test_derivation_contracts_are_strict_json_schema_2020_12() -> None:
    for name in (
        "transaction-deduplication-request-v1.schema.json",
        "transaction-deduplication-manifest-v1.schema.json",
    ):
        contract = json.loads((REPOSITORY_ROOT / "ml/contracts" / name).read_text())
        assert contract["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert contract["additionalProperties"] is False
        assert set(contract["required"]) == set(contract["properties"])


def test_committed_momtsim_v2_derivation_manifest_is_safe_and_content_addressed() -> None:
    path = REPOSITORY_ROOT / "data/manifests/momtsim-v2-dedup-v1.derivation.json"
    manifest = load_deduplication_manifest(path)
    assert manifest["source_sha256"] == (
        "99fd07c3a9d3c4bd6d3462240058ca19d0d9e9284683f78bf77542ff7fcc05e7"
    )
    assert manifest["output_sha256"] == (
        "642fcb2ba7c9cbfffb933729d118f426fefddcbaabbf002793807be169fe80cd"
    )
    assert manifest["source_row_count"] == 4225958
    assert manifest["output_row_count"] == 4225938
    assert manifest["removed_duplicate_row_count"] == 20
    assert manifest["duplicate_group_count"] == 20
    assert manifest["max_duplicate_group_size"] == 2
    assert manifest["removed_positive_count"] == 0
    assert manifest["source_bytes_modified"] is False
    assert manifest["splits_created"] is False
    assert manifest["training_executed"] is False
