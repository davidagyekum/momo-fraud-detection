from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from momo_fdvs_ml.acquisition import (
    AcquisitionError,
    acquisition_readiness_report,
    deterministic_subset_ids,
    load_registration_manifest,
    load_registration_request,
    readiness_markdown,
    register_local_source,
    safe_registration_profile,
    source_inventory,
)
from momo_fdvs_ml.cli import main

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPOSITORY_ROOT / "data"
PURPOSE = "fixture_validation"


def _approved_data_root(
    tmp_path: Path,
    *,
    dataset_id: str = "paysim",
    dataset_kind: str = "transaction_csv",
    requires_masks: bool = False,
) -> Path:
    data_root = tmp_path / "repository" / "data"
    data_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(DATA_ROOT, data_root)
    registry_path = data_root / "registry.yaml"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = next(item for item in registry["datasets"] if item["dataset_id"] == dataset_id)
    entry.update(
        permission_status="approved",
        licence_status="verified",
        version="fixture-v1",
        allowed_purposes=[PURPOSE],
    )
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    if dataset_kind == "transaction_csv":
        spec = {
            "schema_version": "dataset-validation-spec-v1",
            "dataset_id": dataset_id,
            "status": "ready",
            "dataset_kind": dataset_kind,
            "required_columns": [
                "step",
                "type",
                "amount",
                "nameOrig",
                "oldbalanceOrg",
                "newbalanceOrig",
                "nameDest",
                "oldbalanceDest",
                "newbalanceDest",
                "isFraud",
                "isFlaggedFraud",
            ],
            "label_column": "isFraud",
            "positive_values": ["1"],
            "step_column": "step",
            "expected_row_count": 2,
            "expected_positive_count": 1,
            "expected_step_count": 2,
            "forbidden_primary_benchmark_columns": [
                "isFlaggedFraud",
                "oldbalanceOrg",
                "newbalanceOrig",
                "oldbalanceDest",
                "newbalanceDest",
            ],
        }
    else:
        spec = {
            "schema_version": "dataset-validation-spec-v1",
            "dataset_id": dataset_id,
            "status": "ready",
            "dataset_kind": dataset_kind,
            "allowed_image_extensions": [".png"],
            "requires_masks": requires_masks,
        }
        if requires_masks:
            spec["mask_suffix"] = "_mask"
    (data_root / "acquisition_specs" / f"{dataset_id}.json").write_text(
        json.dumps(spec), encoding="utf-8"
    )
    return data_root


def _paysim_csv(*, duplicate: bool = False, invalid: bool = False) -> str:
    header = (
        "step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,"
        "oldbalanceDest,newbalanceDest,isFraud,isFlaggedFraud\n"
    )
    first = "1,TRANSFER,100.0,C1,100.0,0.0,C2,0.0,100.0,0,0\n"
    second = (
        "2,CASH_OUT,-5.0,C3,50.0,45.0,C4,0.0,5.0,bad,0\n"
        if invalid
        else "2,CASH_OUT,500.0,C3,500.0,0.0,C4,0.0,500.0,1,0\n"
    )
    return header + first + (first if duplicate else second)


def _zip_csv(path: Path, content: str, *, member: str = "paysim.csv") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    info = zipfile.ZipInfo(member, date_time=(2026, 8, 11, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, content)


def _request(
    path: Path,
    *,
    dataset_id: str,
    source: Path,
    source_kind: str,
    version: str = "fixture-v1",
    entrypoint: str | None = None,
    expected_hash: str | None = None,
    expected_size: int | None = None,
) -> Path:
    inventory = source_inventory(source, source_kind=source_kind)
    payload = {
        "schema_version": "acquisition-request-v1",
        "dataset_id": dataset_id,
        "purpose": PURPOSE,
        "reviewer_id": "REVIEWER_A1B2C3D4E5F6",
        "permission_reference": "PERMISSION_A1B2C3D4E5F6",
        "licence_reference": "LICENCE_A1B2C3D4E5F6",
        "source_kind": source_kind,
        "source_path": str(source.resolve()),
        "entrypoint": entrypoint,
        "expected_sha256": expected_hash or inventory.source_sha256,
        "expected_size_bytes": expected_size or inventory.source_size_bytes,
        "expected_version": version,
        "created_at": "2026-08-11T00:00:00Z",
        "acknowledgements": {
            "terms_reviewed": True,
            "no_redistribution": True,
            "private_storage": True,
            "version_verified": True,
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _register(
    tmp_path: Path,
    *,
    data_root: Path,
    request_path: Path,
    source_root: Path,
):
    return register_local_source(
        data_root=data_root,
        request_path=request_path,
        allowed_source_root=source_root,
        manifest_path=tmp_path / "out" / "manifest.json",
        profile_path=tmp_path / "out" / "profile.json",
    )


def test_committed_readiness_matches_recorded_report_without_opening_bytes() -> None:
    report = acquisition_readiness_report(DATA_ROOT)
    recorded = json.loads(
        (DATA_ROOT / "acquisition_readiness_report.json").read_text(encoding="utf-8")
    )
    assert report == recorded
    assert report["source_count"] == 6
    assert report["eligible_source_count"] == 4
    assert report["blocked_source_count"] == 2
    assert report["network_acquisition_executed"] is False
    assert report["source_bytes_opened"] is False
    assert report["training_executed"] is False
    assert "No source bytes were opened" in readiness_markdown(report)
    assert (REPOSITORY_ROOT / "reports/generated/dataset_inventory.md").read_text(
        encoding="utf-8"
    ) == readiness_markdown(report)


def test_paysim_spec_matches_observed_canonical_archive_profile() -> None:
    spec = json.loads((DATA_ROOT / "acquisition_specs/paysim.json").read_text(encoding="utf-8"))
    assert spec["approved_source"] == {
        "canonical_locator": "kaggle:ealaxi/paysim1",
        "kaggle_dataset_version": 2,
        "archive_filename": "paysim-ealaxi-v2-f7eef9ffad5c.zip",
        "archive_sha256": ("f7eef9ffad5cfa64a034143a5c9b30491d189420b273d5ad5723ca40b596613d"),
        "archive_size_bytes": 186385561,
        "entrypoint": "PS_20174392719_1491204439457_log.csv",
        "entrypoint_size_bytes": 493534783,
    }
    assert spec["expected_row_count"] == 6362620
    assert spec["expected_positive_count"] == 8213
    assert spec["expected_step_count"] == 743


def test_momtsim_specs_freeze_official_identity_and_observed_profiles() -> None:
    v1 = json.loads((DATA_ROOT / "acquisition_specs/momtsim-v1.json").read_text(encoding="utf-8"))
    v2 = json.loads((DATA_ROOT / "acquisition_specs/momtsim-v2.json").read_text(encoding="utf-8"))
    assert (v1["status"], v1["expected_step_count"]) == ("ready", 144)
    assert v1["approved_source"]["file_sha256"] == (
        "da951eb95735da96271740a3e66b676b342d3831ce3111cd19dbfa020d3bd0a7"
    )
    assert (v2["status"], v2["expected_step_count"]) == ("ready", 193)
    assert v2["approved_source"]["file_sha256"] == (
        "99fd07c3a9d3c4bd6d3462240058ca19d0d9e9284683f78bf77542ff7fcc05e7"
    )
    assert v2["expected_row_count"] == 4225938
    assert v2["derived_candidate"]["output_sha256"] == (
        "642fcb2ba7c9cbfffb933729d118f426fefddcbaabbf002793807be169fe80cd"
    )


def test_stfd_spec_is_ready_with_conservative_train_only_grouping() -> None:
    spec = json.loads((DATA_ROOT / "acquisition_specs/stfd.json").read_text(encoding="utf-8"))
    registry = json.loads((DATA_ROOT / "registry.yaml").read_text(encoding="utf-8"))
    entry = next(item for item in registry["datasets"] if item["dataset_id"] == "stfd")
    source = spec["approved_source_metadata"]
    assert spec["status"] == "ready"
    assert source["repository_revision"] == "9edebed2109052a77e9a5581c2ea7ce33d685da0"
    assert source["archive_size_bytes"] == 2941753426
    assert source["archive_lfs_sha256"] == (
        "6159a6611caaf71f40acf181b404af5a5dd0547f3d2d8d819bb640e3fb5de18c"
    )
    assert spec["pairing_rule"] == "same_filename_within_tampering_directory"
    assert spec["pairing_strategy"] == "parallel_category_directories"
    assert sum(spec["expected_pair_counts"].values()) == 3932
    assert spec["expected_soft_mask_count"] == 3
    assert spec["expected_soft_mask_pixel_count"] == 12860
    assert spec["soft_mask_threshold"] == 128
    assert spec["grouping_strategy"] == "single_external_pretraining_corpus_group"
    assert len(spec["tampering_directories"]) == 5
    assert entry["acquisition_status"] == "registered"
    assert entry["permission_status"] == "approved"
    assert entry["enabled"] is False


def test_committed_stfd_registration_evidence_is_safe_and_train_only() -> None:
    evidence = json.loads(
        (REPOSITORY_ROOT / "docs/evidence/PR13_STFD_REGISTRATION.json").read_text(encoding="utf-8")
    )
    summary = evidence["validation_summary"]
    grouping = evidence["grouping"]
    assert evidence["status"] == "registered"
    assert summary["paired_image_mask_count"] == 3932
    assert summary["soft_mask_count"] == 3
    assert summary["soft_mask_pixel_count"] == 12860
    assert summary["source_masks_modified"] is False
    assert grouping["source_group_count"] == 1
    assert grouping["split_usage"] == "external_pretraining_train_only"
    assert grouping["internal_evaluation_allowed"] is False
    assert evidence["promotable_for_training"] is False
    assert evidence["training_executed"] is False
    assert evidence["contains_member_names"] is False
    assert evidence["contains_source_paths"] is False
    assert evidence["contains_password"] is False


def test_committed_momtsim_v1_evidence_is_safe_and_matches_registry() -> None:
    dataset_id = "momtsim-v1"
    manifest = load_registration_manifest(DATA_ROOT / "manifests/momtsim-v1.manifest.json")
    profile = json.loads(
        (
            REPOSITORY_ROOT
            / "reports/generated/dataset_profiles"
            / f"{dataset_id}-safe-summary.json"
        ).read_text(encoding="utf-8")
    )
    registry = json.loads((DATA_ROOT / "registry.yaml").read_text(encoding="utf-8"))
    entry = next(item for item in registry["datasets"] if item["dataset_id"] == dataset_id)
    assert manifest["status"] == profile["status"] == entry["acquisition_status"]
    assert manifest["status"] == "registered"
    assert manifest["validation_summary"]["duplicate_row_count"] == 0
    assert profile["contains_source_paths"] is False
    assert profile["contains_member_names"] is False
    assert profile["promotable_for_training"] is False


def test_committed_momtsim_v2_preserves_quarantine_and_registers_derivative() -> None:
    official = load_registration_manifest(DATA_ROOT / "manifests/momtsim-v2.manifest.json")
    derived = load_registration_manifest(DATA_ROOT / "manifests/momtsim-v2-dedup-v1.manifest.json")
    profile = json.loads(
        (
            REPOSITORY_ROOT
            / "reports/generated/dataset_profiles/momtsim-v2-dedup-v1-safe-summary.json"
        ).read_text(encoding="utf-8")
    )
    registry = json.loads((DATA_ROOT / "registry.yaml").read_text(encoding="utf-8"))
    entry = next(item for item in registry["datasets"] if item["dataset_id"] == "momtsim-v2")
    assert official["status"] == "quarantined"
    assert official["validation_summary"]["duplicate_row_count"] == 20
    assert derived["status"] == profile["status"] == entry["acquisition_status"] == "registered"
    assert derived["dataset_version"] == entry["version"] == "2-derived-exact-dedup-v1"
    assert derived["validation_summary"]["duplicate_row_count"] == 0
    assert profile["contains_source_paths"] is False
    assert profile["promotable_for_training"] is False


def test_acquisition_contracts_are_strict_json_schema_2020_12() -> None:
    contract_root = REPOSITORY_ROOT / "ml/contracts"
    for name in (
        "acquisition-request-v1.schema.json",
        "dataset-registration-manifest-v1.schema.json",
    ):
        contract = json.loads((contract_root / name).read_text(encoding="utf-8"))
        assert contract["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert contract["type"] == "object"
        assert contract["additionalProperties"] is False
        assert set(contract["required"]) == set(contract["properties"])


def test_readiness_names_each_source_specific_blocker() -> None:
    report = acquisition_readiness_report(DATA_ROOT)
    sources = {source["dataset_id"]: source for source in report["sources"]}
    assert sources["paysim"]["blockers"] == []
    assert sources["paysim"]["eligible_for_local_registration"] is True
    assert sources["momtsim-v1"]["blockers"] == []
    assert sources["momtsim-v2"]["blockers"] == []
    assert "written_access_approval_missing" not in sources["stfd"]["blockers"]
    assert "permission_status:access_request_required" not in sources["stfd"]["blockers"]
    assert "licence_status:unverified" not in sources["stfd"]["blockers"]
    assert sources["stfd"]["blockers"] == []
    assert sources["stfd"]["eligible_for_local_registration"] is True
    assert "participant_consent_evidence_missing" in sources["ghana-private"]["blockers"]
    assert sources["fsts"]["required"] is False


def test_authorized_fake_archive_registers_idempotently_without_promotion(
    tmp_path: Path,
) -> None:
    data_root = _approved_data_root(tmp_path)
    source_root = tmp_path / "private"
    archive = source_root / "paysim.zip"
    _zip_csv(archive, _paysim_csv())
    request = _request(
        tmp_path / "request.json",
        dataset_id="paysim",
        source=archive,
        source_kind="file",
        entrypoint="paysim.csv",
    )
    first = _register(tmp_path, data_root=data_root, request_path=request, source_root=source_root)
    first_bytes = first.manifest_path.read_bytes()
    second = _register(tmp_path, data_root=data_root, request_path=request, source_root=source_root)
    assert second.manifest_path.read_bytes() == first_bytes
    manifest = load_registration_manifest(first.manifest_path)
    assert manifest["status"] == "registered"
    assert manifest["quarantine_reasons"] == []
    assert manifest["network_acquisition_executed"] is False
    assert manifest["source_bytes_committed"] is False
    assert manifest["promotable_for_training"] is False
    validation = manifest["validation_summary"]
    assert validation["row_count"] == 2
    assert validation["positive_count"] == 1
    assert validation["duplicate_row_count"] == 0
    profile_text = first.profile_path.read_text(encoding="utf-8")
    assert str(source_root) not in profile_text
    assert "paysim.csv" not in profile_text


@pytest.mark.parametrize(
    ("content", "expected_reason"),
    [
        (_paysim_csv(duplicate=True), "duplicate_rows_present"),
        (_paysim_csv(invalid=True), "invalid_target_values"),
    ],
)
def test_validation_failures_quarantine_without_mutating_source(
    tmp_path: Path, content: str, expected_reason: str
) -> None:
    data_root = _approved_data_root(tmp_path)
    source_root = tmp_path / "private"
    archive = source_root / "paysim.zip"
    _zip_csv(archive, content)
    original = archive.read_bytes()
    request = _request(
        tmp_path / "request.json",
        dataset_id="paysim",
        source=archive,
        source_kind="file",
        entrypoint="paysim.csv",
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "quarantined"
    assert expected_reason in outputs.manifest["quarantine_reasons"]
    assert archive.read_bytes() == original


def test_identity_mismatch_quarantines_with_safe_profile(tmp_path: Path) -> None:
    data_root = _approved_data_root(tmp_path)
    source_root = tmp_path / "private"
    archive = source_root / "paysim.zip"
    _zip_csv(archive, _paysim_csv())
    request = _request(
        tmp_path / "request.json",
        dataset_id="paysim",
        source=archive,
        source_kind="file",
        entrypoint="paysim.csv",
        expected_hash="0" * 64,
        expected_size=archive.stat().st_size + 1,
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "quarantined"
    assert set(outputs.manifest["quarantine_reasons"]) >= {
        "source_sha256_mismatch",
        "source_size_mismatch",
    }


def test_unready_spec_blocks_before_any_source_access(tmp_path: Path) -> None:
    data_root = tmp_path / "repository" / "data"
    data_root.parent.mkdir(parents=True)
    shutil.copytree(DATA_ROOT, data_root)
    spec_path = data_root / "acquisition_specs/momtsim-v1.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["status"] = "pending_exact_file_identity"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    request_path = tmp_path / "request.json"
    payload = {
        "schema_version": "acquisition-request-v1",
        "dataset_id": "momtsim-v1",
        "purpose": "academic_research_after_terms_review",
        "reviewer_id": "REVIEWER_A1B2C3D4E5F6",
        "permission_reference": "PERMISSION_A1B2C3D4E5F6",
        "licence_reference": "LICENCE_A1B2C3D4E5F6",
        "source_kind": "file",
        "source_path": str((tmp_path / "missing.zip").resolve()),
        "entrypoint": "momtsim.csv",
        "expected_sha256": "a" * 64,
        "expected_size_bytes": 1,
        "expected_version": "1",
        "created_at": "2026-08-11T00:00:00Z",
        "acknowledgements": {
            "terms_reviewed": True,
            "no_redistribution": True,
            "private_storage": True,
            "version_verified": True,
        },
    }
    request_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AcquisitionError, match="validation specification is not ready"):
        register_local_source(
            data_root=data_root,
            request_path=request_path,
            allowed_source_root=tmp_path,
            manifest_path=tmp_path / "manifest.json",
            profile_path=tmp_path / "profile.json",
        )
    assert not (tmp_path / "manifest.json").exists()


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(schema_version="old"), "unsupported"),
        (lambda value: value.update(reviewer_id="David"), "opaque reviewer"),
        (lambda value: value.update(permission_reference="raw approval"), "must be opaque"),
        (lambda value: value.update(licence_reference="url"), "must be opaque"),
        (lambda value: value.update(expected_sha256="bad"), "lowercase SHA-256"),
        (lambda value: value.update(expected_size_bytes=0), "positive integer"),
        (lambda value: value.update(created_at="2026-08-11"), "timezone"),
        (lambda value: value.update(acknowledgements={}), "exact required fields"),
    ],
)
def test_registration_request_rejects_unsafe_or_incomplete_fields(
    tmp_path: Path,
    mutation,
    message: str,  # type: ignore[no-untyped-def]
) -> None:
    source_root = tmp_path / "private"
    archive = source_root / "paysim.zip"
    _zip_csv(archive, _paysim_csv())
    path = _request(
        tmp_path / "request.json",
        dataset_id="paysim",
        source=archive,
        source_kind="file",
        entrypoint="paysim.csv",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutation(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AcquisitionError, match=message):
        load_registration_request(path)


def test_registration_request_rejects_unknown_field(tmp_path: Path) -> None:
    source_root = tmp_path / "private"
    archive = source_root / "paysim.zip"
    _zip_csv(archive, _paysim_csv())
    path = _request(
        tmp_path / "request.json",
        dataset_id="paysim",
        source=archive,
        source_kind="file",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["token"] = "prohibited"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(AcquisitionError, match="unknown token"):
        load_registration_request(path)


def test_source_must_stay_inside_approved_root(tmp_path: Path) -> None:
    data_root = _approved_data_root(tmp_path)
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir()
    outside = tmp_path / "outside.zip"
    _zip_csv(outside, _paysim_csv())
    request = _request(
        tmp_path / "request.json",
        dataset_id="paysim",
        source=outside,
        source_kind="file",
        entrypoint="paysim.csv",
    )
    with pytest.raises(AcquisitionError, match="approved private root"):
        _register(tmp_path, data_root=data_root, request_path=request, source_root=allowed_root)


def test_archive_traversal_and_ambiguous_csv_are_rejected(tmp_path: Path) -> None:
    unsafe = tmp_path / "unsafe.zip"
    _zip_csv(unsafe, _paysim_csv(), member="../escape.csv")
    with pytest.raises(AcquisitionError, match="unsafe member"):
        source_inventory(unsafe, source_kind="file")

    ambiguous = tmp_path / "ambiguous.zip"
    with zipfile.ZipFile(ambiguous, "w") as archive:
        archive.writestr("one.csv", _paysim_csv())
        archive.writestr("two.csv", _paysim_csv())
    data_root = _approved_data_root(tmp_path / "second")
    request = _request(
        tmp_path / "ambiguous-request.json",
        dataset_id="paysim",
        source=ambiguous,
        source_kind="file",
    )
    with pytest.raises(AcquisitionError, match="unambiguous CSV"):
        _register(
            tmp_path,
            data_root=data_root,
            request_path=request,
            source_root=tmp_path,
        )


def test_image_directory_registers_and_member_export_is_refused(tmp_path: Path) -> None:
    data_root = _approved_data_root(tmp_path, dataset_id="fsts", dataset_kind="image_collection")
    source_root = tmp_path / "private"
    image_root = source_root / "images"
    image_root.mkdir(parents=True)
    Image.new("RGB", (8, 6), "white").save(image_root / "one.png")
    Image.new("RGB", (8, 6), "black").save(image_root / "two.png")
    request = _request(
        tmp_path / "request.json",
        dataset_id="fsts",
        source=image_root,
        source_kind="directory",
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "registered"
    summary = outputs.manifest["validation_summary"]
    assert summary["image_count"] == 2
    assert summary["decode_failure_count"] == 0
    registry = json.loads((data_root / "registry.yaml").read_text(encoding="utf-8"))
    entry = next(item for item in registry["datasets"] if item["dataset_id"] == "fsts")
    with pytest.raises(AcquisitionError, match="member-level export"):
        safe_registration_profile(outputs.manifest, entry, include_members=True)
    profile = safe_registration_profile(outputs.manifest, entry)
    assert profile["contains_source_paths"] is False
    assert profile["contains_member_names"] is False


def test_image_decode_and_mask_gate_quarantine(tmp_path: Path) -> None:
    data_root = _approved_data_root(
        tmp_path,
        dataset_id="fsts",
        dataset_kind="image_collection",
        requires_masks=True,
    )
    source_root = tmp_path / "private"
    image_root = source_root / "images"
    image_root.mkdir(parents=True)
    (image_root / "broken.png").write_bytes(b"not-an-image")
    Image.new("RGB", (8, 6), "white").save(image_root / "original.png")
    request = _request(
        tmp_path / "request.json",
        dataset_id="fsts",
        source=image_root,
        source_kind="directory",
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "quarantined"
    assert set(outputs.manifest["quarantine_reasons"]) >= {
        "image_decode_failures",
        "missing_masks",
    }


def test_image_mask_pair_dimensions_are_enforced(tmp_path: Path) -> None:
    data_root = _approved_data_root(
        tmp_path,
        dataset_id="fsts",
        dataset_kind="image_collection",
        requires_masks=True,
    )
    source_root = tmp_path / "private"
    image_root = source_root / "images"
    image_root.mkdir(parents=True)
    Image.new("RGB", (8, 6), "white").save(image_root / "sample.png")
    Image.new("L", (7, 6), 255).save(image_root / "sample_mask.png")
    request = _request(
        tmp_path / "request.json",
        dataset_id="fsts",
        source=image_root,
        source_kind="directory",
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "quarantined"
    assert "mask_dimension_mismatch" in outputs.manifest["quarantine_reasons"]
    summary = outputs.manifest["validation_summary"]
    assert summary["original_image_count"] == 1
    assert summary["mask_count"] == 1


def test_parallel_mask_collection_registers_with_soft_mask_and_train_only_group(
    tmp_path: Path,
) -> None:
    data_root = _approved_data_root(
        tmp_path,
        dataset_id="stfd",
        dataset_kind="image_collection",
        requires_masks=True,
    )
    spec_path = data_root / "acquisition_specs/stfd.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec.pop("mask_suffix")
    spec.update(
        pairing_strategy="parallel_category_directories",
        tampering_directories=["1_Copy-move"],
        image_directory_name="tamper",
        mask_directory_name="masks",
        expected_pair_counts={"1_Copy-move": 1},
        expected_soft_mask_count=1,
        expected_soft_mask_pixel_count=1,
        soft_mask_threshold=128,
        grouping_strategy="single_external_pretraining_corpus_group",
    )
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    source_root = tmp_path / "private"
    category_root = source_root / "stfd" / "1_Copy-move"
    image_root = category_root / "tamper"
    mask_root = category_root / "masks"
    image_root.mkdir(parents=True)
    mask_root.mkdir(parents=True)
    (mask_root / "1_Copy-move" / "masks").mkdir(parents=True)
    Image.new("RGB", (8, 6), "white").save(image_root / "opaque-source.png")
    mask = Image.new("L", (8, 6), 0)
    mask.putpixel((1, 1), 255)
    mask.putpixel((2, 1), 127)
    mask.save(mask_root / "opaque-source.png")
    request = _request(
        tmp_path / "request.json",
        dataset_id="stfd",
        source=source_root / "stfd",
        source_kind="directory",
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "registered"
    summary = outputs.manifest["validation_summary"]
    assert summary["paired_image_mask_count"] == 1
    assert summary["soft_mask_count"] == 1
    assert summary["soft_mask_pixel_count"] == 1
    assert summary["source_masks_modified"] is False
    assert summary["source_group_count"] == 1
    assert summary["split_usage"] == "external_pretraining_train_only"
    assert summary["internal_evaluation_allowed"] is False


def test_parallel_mask_collection_quarantines_soft_mask_contract_drift(
    tmp_path: Path,
) -> None:
    data_root = _approved_data_root(
        tmp_path,
        dataset_id="stfd",
        dataset_kind="image_collection",
        requires_masks=True,
    )
    spec_path = data_root / "acquisition_specs/stfd.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec.pop("mask_suffix")
    spec.update(
        pairing_strategy="parallel_category_directories",
        tampering_directories=["1_Copy-move"],
        image_directory_name="tamper",
        mask_directory_name="masks",
        expected_pair_counts={"1_Copy-move": 1},
        expected_soft_mask_count=1,
        expected_soft_mask_pixel_count=2,
        soft_mask_threshold=128,
        grouping_strategy="single_external_pretraining_corpus_group",
    )
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    source_root = tmp_path / "private"
    category_root = source_root / "stfd" / "1_Copy-move"
    image_root = category_root / "tamper"
    mask_root = category_root / "masks"
    image_root.mkdir(parents=True)
    mask_root.mkdir(parents=True)
    Image.new("RGB", (8, 6), "white").save(image_root / "opaque-source.png")
    mask = Image.new("L", (8, 6), 0)
    mask.putpixel((1, 1), 255)
    mask.putpixel((2, 1), 127)
    mask.save(mask_root / "opaque-source.png")
    request = _request(
        tmp_path / "request.json",
        dataset_id="stfd",
        source=source_root / "stfd",
        source_kind="directory",
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "quarantined"
    assert "soft_mask_pixel_count_mismatch" in outputs.manifest["quarantine_reasons"]


def test_image_size_cap_quarantines_without_decoding_payload(tmp_path: Path) -> None:
    data_root = _approved_data_root(tmp_path, dataset_id="fsts", dataset_kind="image_collection")
    spec_path = data_root / "acquisition_specs/fsts.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["max_image_bytes"] = 1
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    source_root = tmp_path / "private"
    image_root = source_root / "images"
    image_root.mkdir(parents=True)
    Image.new("RGB", (8, 6), "white").save(image_root / "sample.png")
    request = _request(
        tmp_path / "request.json",
        dataset_id="fsts",
        source=image_root,
        source_kind="directory",
    )
    outputs = _register(
        tmp_path, data_root=data_root, request_path=request, source_root=source_root
    )
    assert outputs.manifest["status"] == "quarantined"
    assert "oversized_image_files" in outputs.manifest["quarantine_reasons"]


def test_deterministic_subset_is_stable_and_hides_member_names() -> None:
    names = ["participant-a.png", "participant-b.png", "participant-c.png"]
    first = deterministic_subset_ids(names, seed=123, count=2)
    second = deterministic_subset_ids(list(reversed(names)), seed=123, count=2)
    assert first == second
    assert all(len(value) == 64 for value in first)
    assert all(name not in json.dumps(first) for name in names)
    with pytest.raises(AcquisitionError, match="count"):
        deterministic_subset_ids(names, seed=123, count=4)


def test_cli_readiness_and_fail_closed_registration(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "acquisition-readiness",
                "--data-root",
                str(DATA_ROOT),
                "--recorded-report",
                str(DATA_ROOT / "acquisition_readiness_report.json"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["eligible_source_count"] == 4

    request_path = tmp_path / "invalid-request.json"
    request_path.write_text("{}", encoding="utf-8")
    assert (
        main(
            [
                "register-dataset",
                "--data-root",
                str(DATA_ROOT),
                "--request",
                str(request_path),
                "--allowed-source-root",
                str(tmp_path),
                "--manifest-output",
                str(tmp_path / "manifest.json"),
                "--profile-output",
                str(tmp_path / "profile.json"),
            ]
        )
        == 1
    )
    assert "registration request fields invalid" in capsys.readouterr().out


def test_acquisition_module_contains_no_network_client() -> None:
    source = (REPOSITORY_ROOT / "ml/src/momo_fdvs_ml/acquisition.py").read_text(encoding="utf-8")
    prohibited = ("requests", "urllib", "httpx", "urlopen", "subprocess")
    assert not any(value in source for value in prohibited)
