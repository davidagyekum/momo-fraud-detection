from __future__ import annotations

import csv
from pathlib import Path

import pytest
from PIL import Image

from momo_fdvs_ml.ghana_dataset import (
    LABEL_COLUMNS,
    GhanaDatasetError,
    build_canonical_manifest,
    init_workspace,
    normalise_ocr_text,
    ocr_fingerprint,
    phash_file,
    phash_hamming,
    redact_image,
    sha256_file,
    validate_dataset,
    write_report,
)
from momo_fdvs_ml.manifest import load_manifest


def _write_rows(root: Path, rows: list[dict[str, str]]) -> None:
    path = root / "metadata" / "labels_adjudicated.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LABEL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _row(
    root: Path, sample_id: str = "GHMM_000001", *, label: str = "fraudulent"
) -> dict[str, str]:
    split = "train"
    image_path = root / "images" / split / f"{sample_id}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (160, 220), (255, 255, 255))
    for x in range(20, 140):
        for y in range(40, 70):
            image.putpixel((x, y), (20, 80, 150))
    image.save(image_path)
    relative_path = image_path.relative_to(root).as_posix()
    sha256 = sha256_file(image_path)
    phash = phash_file(image_path)
    row = {column: "" for column in LABEL_COLUMNS}
    row.update(
        {
            "sample_id": sample_id,
            "local_relative_path": relative_path,
            "source_group_id": f"group-{sample_id}",
            "source_type": "real_authorised",
            "fraud_label": label,
            "provider_code": "MTN_MOMO",
            "provider_alias": "MTN MoMo",
            "scam_subtype": "fake_transfer_alert",
            "social_vector": "sms",
            "impersonation_target": "operator",
            "urgency_cues": "security_emergency",
            "persuasion_cues": "authority",
            "requested_action": "call_number",
            "language_primary": "english",
            "language_secondary": "",
            "media_type": "native_screenshot",
            "quality": "high",
            "ghana_evidence": "strong",
            "geo_evidence_note": "MTN Ghana brand and GHS context in source review",
            "pii_status": "redacted",
            "redaction_version": "manual-box-v1",
            "ocr_text_redacted": "your momo account needs verification",
            "ocr_fingerprint": ocr_fingerprint("your momo account needs verification"),
            "sha256": sha256,
            "phash": phash,
            "campaign_group_id": f"campaign-{sample_id}",
            "source_platform": "official_web",
            "source_account_type": "official_org",
            "source_url": "https://example.org/ghana-momo-source",
            "source_post_id": "",
            "source_date": "2026-08-10",
            "collected_at": "2026-08-10T12:00:00Z",
            "rights_status": "licensed",
            "consent_or_licence_reference": "LICENCE-TEST-001",
            "original_contains_personal_data": "true",
            "release_eligible": "true",
            "annotator_a": "annotator-a",
            "annotator_b": "annotator-b",
            "adjudicated_by": "reviewer",
            "label_confidence": "high",
            "split": split,
            "notes": "test-only redacted fixture",
        }
    )
    return row


def test_init_workspace_creates_governed_templates(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    init_workspace(root)
    assert (
        (root / "metadata" / "labels_adjudicated.csv")
        .read_text(encoding="utf-8")
        .startswith("sample_id,")
    )
    assert (root / "provenance" / "source_registry.csv").is_file()
    assert (root / "images" / "review").is_dir()


def test_empty_workspace_is_explicitly_not_ready(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    report = validate_dataset(root)
    assert report.status == "NOT_READY"
    assert report.ready_count == 0
    assert any(issue.code == "target_not_reached" for issue in report.warnings)


def test_missing_and_malformed_manifests_are_explicitly_not_ready(tmp_path: Path) -> None:
    missing = validate_dataset(tmp_path / "missing")
    assert "missing_manifest" in {issue.code for issue in missing.errors}

    malformed_contents = {
        "no-header": "",
        "duplicate-header": "sample_id,sample_id\n",
        "missing-columns": "sample_id\n",
        "invalid-utf8": b"\xff\xfe",
    }
    for name, content in malformed_contents.items():
        root = tmp_path / name
        init_workspace(root)
        manifest = root / "metadata" / "labels_adjudicated.csv"
        if isinstance(content, bytes):
            manifest.write_bytes(content)
        else:
            manifest.write_text(content, encoding="utf-8")
        report = validate_dataset(root)
        assert "manifest_parse_error" in {issue.code for issue in report.errors}
        payload = report.as_dict()
        assert payload["training_executed"] is False
        output = root / "audits" / "report.json"
        write_report(report, output)
        assert output.is_file()


def test_invalid_metadata_and_paths_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    row = _row(root)
    row.update(
        {
            "sample_id": "not-opaque",
            "source_group_id": "",
            "source_type": "synthetic",
            "fraud_label": "unknown",
            "split": "holdout",
            "provider_code": "not-a-provider",
            "ghana_evidence": "unknown",
            "pii_status": "unknown",
            "rights_status": "unknown",
            "source_url": "",
            "source_platform": "web",
            "source_account_type": "",
            "collected_at": "",
            "consent_or_licence_reference": "",
            "ocr_text_redacted": "",
            "local_relative_path": "other/not-opaque.png",
            "release_eligible": "false",
            "original_contains_personal_data": "false",
        }
    )
    _write_rows(root, [row])
    report = validate_dataset(root)
    codes = {issue.code for issue in report.errors}
    assert {
        "invalid_sample_id",
        "missing_source_group",
        "invalid_source_type",
        "invalid_label",
        "invalid_split",
        "invalid_provider",
        "invalid_ghana_evidence",
        "invalid_pii_status",
        "invalid_rights_status",
        "missing_source_url",
        "missing_source_context",
        "missing_collection_time",
        "missing_permission",
        "unsafe_local_path",
    } <= codes

    row["release_eligible"] = "maybe"
    row["local_relative_path"] = "../outside.png"
    _write_rows(root, [row])
    report = validate_dataset(root)
    assert "invalid_boolean" in {issue.code for issue in report.errors}


def test_release_gates_require_redaction_rights_and_reviewable_labels(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    row = _row(root)
    row.update(
        {
            "fraud_label": "genuine",
            "split": "review",
            "rights_status": "unknown_do_not_release",
            "pii_status": "requires_redaction",
            "ghana_evidence": "weak",
            "redaction_version": "",
        }
    )
    _write_rows(root, [row])
    report = validate_dataset(root)
    codes = {issue.code for issue in report.errors}
    assert {
        "rights_not_releaseable",
        "pii_not_releaseable",
        "ghana_evidence_too_weak",
        "missing_redaction_version",
        "label_not_model_split",
        "invalid_ready_label",
    } <= codes


def test_valid_release_row_passes_with_target_warning(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    _write_rows(root, [_row(root)])
    report = validate_dataset(root, require_ready=True, minimum_ready=1)
    assert report.status == "PASS"
    assert report.ready_count == 1
    assert report.errors == ()
    below_minimum = validate_dataset(root, require_ready=True, minimum_ready=2)
    assert below_minimum.status == "NOT_READY"
    assert "minimum_ready_not_met" in {issue.code for issue in below_minimum.errors}


def test_release_row_rejects_unknown_rights_and_weak_ghana_evidence(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    row = _row(root)
    row["rights_status"] = "unknown_do_not_release"
    row["ghana_evidence"] = "weak"
    _write_rows(root, [row])
    report = validate_dataset(root)
    codes = {issue.code for issue in report.errors}
    assert {"rights_not_releaseable", "ghana_evidence_too_weak"} <= codes
    assert report.status == "NOT_READY"


def test_suspicious_rows_must_stay_in_review(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    row = _row(root, label="suspicious")
    _write_rows(root, [row])
    report = validate_dataset(root)
    assert "suspicious_not_review" in {issue.code for issue in report.errors}


def test_image_path_must_match_declared_split(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    row = _row(root)
    row["local_relative_path"] = "images/validation/GHMM_000001.png"
    _write_rows(root, [row])
    report = validate_dataset(root)
    assert "image_split_path_mismatch" in {issue.code for issue in report.errors}


def test_private_ocr_and_hash_mismatch_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    row = _row(root)
    row["ocr_text_redacted"] = "call 0241234567 for your momo PIN"
    row["ocr_fingerprint"] = ocr_fingerprint(row["ocr_text_redacted"])
    row["sha256"] = "0" * 64
    _write_rows(root, [row])
    report = validate_dataset(root)
    codes = {issue.code for issue in report.errors}
    assert {"private_text_remaining", "hash_mismatch"} <= codes

    row["ocr_text_redacted"] = "safe redacted message"
    row["ocr_fingerprint"] = "0" * 64
    row["sha256"] = "bad"
    _write_rows(root, [row])
    report = validate_dataset(root)
    codes = {issue.code for issue in report.errors}
    assert {"ocr_fingerprint_mismatch", "invalid_sha256"} <= codes


def test_missing_invalid_and_mismatched_phashes_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    missing = _row(root, "GHMM_000001")
    missing["phash"] = ""
    invalid = _row(root, "GHMM_000002")
    invalid["phash"] = "not-a-phash"
    mismatched = _row(root, "GHMM_000003")
    mismatched["phash"] = "0" * 16
    _write_rows(root, [missing, invalid, mismatched])
    report = validate_dataset(root)
    codes = {issue.code for issue in report.errors}
    assert {"missing_phash", "invalid_phash", "phash_mismatch"} <= codes


def test_image_decode_size_exif_and_extension_checks_are_enforced(tmp_path: Path) -> None:
    unsupported_root = tmp_path / "unsupported"
    init_workspace(unsupported_root)
    unsupported = _row(unsupported_root)
    unsupported["local_relative_path"] = "images/train/GHMM_000001.txt"
    _write_rows(unsupported_root, [unsupported])
    report = validate_dataset(unsupported_root)
    assert "unsupported_image_type" in {issue.code for issue in report.errors}

    missing_root = tmp_path / "missing"
    init_workspace(missing_root)
    missing = _row(missing_root)
    (missing_root / missing["local_relative_path"]).unlink()
    _write_rows(missing_root, [missing])
    report = validate_dataset(missing_root)
    assert "missing_image" in {issue.code for issue in report.errors}

    corrupt_root = tmp_path / "corrupt"
    init_workspace(corrupt_root)
    corrupt = _row(corrupt_root)
    (corrupt_root / corrupt["local_relative_path"]).write_bytes(b"not an image")
    _write_rows(corrupt_root, [corrupt])
    report = validate_dataset(corrupt_root)
    assert "corrupt_image" in {issue.code for issue in report.errors}

    small_root = tmp_path / "small"
    init_workspace(small_root)
    small = _row(small_root)
    small_path = small_root / small["local_relative_path"]
    Image.new("RGB", (32, 32), (10, 20, 30)).save(small_path)
    small["sha256"] = sha256_file(small_path)
    small["phash"] = phash_file(small_path)
    _write_rows(small_root, [small])
    report = validate_dataset(small_root)
    assert "image_too_small" in {issue.code for issue in report.issues}

    exif_root = tmp_path / "exif"
    init_workspace(exif_root)
    exif = _row(exif_root)
    exif_path = exif_root / "images" / "train" / "GHMM_000001.jpg"
    exif_data = Image.Exif()
    exif_data[270] = "test metadata"
    Image.new("RGB", (160, 220), (255, 255, 255)).save(exif_path, exif=exif_data)
    exif["local_relative_path"] = "images/train/GHMM_000001.jpg"
    exif["sha256"] = sha256_file(exif_path)
    exif["phash"] = phash_file(exif_path)
    _write_rows(exif_root, [exif])
    report = validate_dataset(exif_root)
    assert "exif_present" in {issue.code for issue in report.errors}


def test_exact_duplicates_and_group_split_leakage_are_rejected(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    first = _row(root)
    second = _row(root, "GHMM_000002", label="genuine")
    second["local_relative_path"] = first["local_relative_path"]
    second["sha256"] = first["sha256"]
    second["phash"] = first["phash"]
    second["source_group_id"] = first["source_group_id"]
    second["split"] = "validation"
    _write_rows(root, [first, second])
    report = validate_dataset(root)
    codes = {issue.code for issue in report.errors}
    assert {"duplicate_sha256", "source_group_leakage", "near_duplicate_split_leakage"} <= codes


def test_near_duplicate_same_split_from_different_groups_is_review_warning(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    first = _row(root)
    second = _row(root, "GHMM_000002", label="genuine")
    second["local_relative_path"] = first["local_relative_path"]
    second["sha256"] = first["sha256"]
    second["phash"] = first["phash"]
    second["source_group_id"] = "different-campaign"
    _write_rows(root, [first, second])
    report = validate_dataset(root)
    assert "near_duplicate_candidate" in {issue.code for issue in report.warnings}


def test_redaction_requires_boxes_and_removes_exif(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "redacted.jpg"
    Image.new("RGB", (200, 200), (255, 255, 255)).save(source, exif=b"Exif\x00\x00test")
    redact_image(source, destination, [(10, 10, 80, 80)])
    with Image.open(destination) as image:
        assert not image.getexif()
        assert image.getpixel((20, 20)) == (0, 0, 0)
    png_destination = tmp_path / "redacted.png"
    redact_image(source, png_destination, [(10, 10, 80, 80)])
    with pytest.raises(GhanaDatasetError, match="outside image bounds"):
        redact_image(source, tmp_path / "invalid.jpg", [(0, 0, 201, 201)])
    with pytest.raises(GhanaDatasetError, match="unable to read source"):
        redact_image(tmp_path / "missing-source.jpg", tmp_path / "missing.jpg", [(1, 1, 2, 2)])
    with pytest.raises(GhanaDatasetError, match="redaction box"):
        redact_image(source, tmp_path / "missing.jpg", [])


def test_phash_and_ocr_normalisation_are_deterministic(tmp_path: Path) -> None:
    image = tmp_path / "image.png"
    Image.new("RGB", (160, 160), (20, 30, 40)).save(image)
    assert phash_hamming(phash_file(image), phash_file(image)) == 0
    assert normalise_ocr_text(" HTTPS://example.test  Your 0241234567 ") == "url your phone"
    with pytest.raises(GhanaDatasetError, match="Unable to calculate"):
        phash_file(tmp_path / "not-an-image.png")


def test_build_canonical_manifest_uses_private_object_ids(tmp_path: Path) -> None:
    root = tmp_path / "ghana"
    init_workspace(root)
    _write_rows(root, [_row(root)])
    output = root / "metadata" / "manifest.csv"
    build_canonical_manifest(root, output)
    manifest = load_manifest(output)
    record = manifest.records[0]
    assert record.source_type == "real_authorised"
    assert record.relative_path == ""
    assert record.private_object_id.startswith("ghana-momo-fraud/object-")
    assert record.label == "fraudulent"


def test_phash_hamming_rejects_malformed_values() -> None:
    with pytest.raises(GhanaDatasetError, match="16 hexadecimal"):
        phash_hamming("bad", "0" * 16)
