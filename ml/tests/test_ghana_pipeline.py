from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from momo_fdvs_ml.ghana_pipeline import (
    GhanaPrivateError,
    IntakeOutputs,
    advance_review,
    apply_withdrawals,
    assess_private_text_split_readiness,
    assign_private_source_group,
    attest_online_candidate_permission,
    changed_pixels_are_masked,
    create_controlled_edit,
    create_controlled_online_crop,
    deidentify_message_text,
    deidentify_online_candidate,
    export_private_imazing_genuine_corpus,
    export_private_ocr_text_corpus,
    freeze_group_splits,
    generate_private_synthetic_clean_text_corpus,
    index_imazing_messages,
    ingest_private_screenshots,
    initialize_owner_consent,
    load_development_records,
    normalize_android_sms_backups,
    prepare_consented_screenshot_text_only_review,
    prepare_online_candidate_text_only_review,
    quarantine_online_candidate,
    record_private_ocr_ground_truth,
    record_private_qa_annotation,
    record_provisional_annotation,
    record_second_review,
    review_online_candidate,
    review_private_text_corpora,
    revise_private_redaction,
    safe_intake_summary,
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _image(path: Path, *, phase: int = 0, metadata: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (96, 64))
    image.putdata(
        [
            (
                (x * (phase + 3) + y * 2) % 256,
                (y * (phase + 5) + x) % 256,
                ((x + y) * (phase + 7)) % 256,
            )
            for y in range(64)
            for x in range(96)
        ]
    )
    pnginfo = None
    if metadata is not None:
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("private_note", metadata)
    image.save(path, pnginfo=pnginfo)
    return path


def _sms_xml(
    path: Path, rows: list[tuple[str, str, str, str]], *, count: int | None = None
) -> Path:
    attributes = "\n".join(
        f'  <sms address="{address}" date="{date}" type="{direction}" body="{body}" />'
        for address, date, direction, body in rows
    )
    declared_count = count if count is not None else len(rows)
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<smses count="{declared_count}">\n{attributes}\n</smses>\n',
        encoding="utf-8",
    )
    return path


def _record(
    *,
    image_id: str,
    source_path: str,
    participant: str,
    group: str,
    regions: list[list[int]] | None = None,
) -> dict[str, object]:
    return {
        "image_id": image_id,
        "source_group_id": group,
        "participant_id_hash": participant,
        "consent_scope": "internal_only",
        "permission_reference": "PERMISSION_OWNER_001",
        "source_path": source_path,
        "redaction_regions": regions or [],
        "deidentification_status": "complete",
        "provider_family": "momo",
        "template_family": "ios-sms",
        "capture_channel": "sms",
        "device_family": "iphone",
        "theme": "light",
    }


def _request(path: Path, records: list[dict[str, object]]) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "ghana-private-intake-request-v1",
            "dataset_id": "ghana-private",
            "records": records,
        },
    )


def _ingest(tmp_path: Path, records: list[dict[str, object]], *, withdrawn=frozenset()):
    return ingest_private_screenshots(
        request_path=_request(tmp_path / "request.json", records),
        raw_root=tmp_path / "raw",
        working_root=tmp_path / "working",
        index_path=tmp_path / "private-index.json",
        report_path=tmp_path / "safe-report.json",
        repository_root=tmp_path / "repository",
        withdrawn_participants=withdrawn,
    )


def test_private_intake_redacts_strips_metadata_and_quarantines_exact_and_withdrawn(
    tmp_path: Path,
) -> None:
    first = _image(tmp_path / "raw/first.png", phase=1, metadata="PRIVATE")
    duplicate = tmp_path / "raw/duplicate.png"
    duplicate.write_bytes(first.read_bytes())
    _image(tmp_path / "raw/withdrawn.png", phase=11)
    participant = _hash("participant-a")
    withdrawn = _hash("participant-withdrawn")
    records = [
        _record(
            image_id="GHIMG_OWNER_0001",
            source_path="first.png",
            participant=participant,
            group="GHGROUP_OWNER_0001",
            regions=[[2, 3, 20, 10]],
        ),
        _record(
            image_id="GHIMG_OWNER_0002",
            source_path="duplicate.png",
            participant=participant,
            group="GHGROUP_OWNER_0001",
        ),
        _record(
            image_id="GHIMG_OWNER_0003",
            source_path="withdrawn.png",
            participant=withdrawn,
            group="GHGROUP_OWNER_0003",
        ),
    ]

    outputs = _ingest(tmp_path, records, withdrawn=frozenset({withdrawn}))
    index = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))

    assert outputs.record_count == 3
    assert outputs.quarantined_count == 1
    assert [record["workflow_state"] for record in index["records"]] == [
        "needs_transcription",
        "quarantined",
        "withdrawn",
    ]
    assert report["exact_duplicate_count"] == 1
    assert report["withdrawn_count"] == 1
    assert report["raw_images_copied"] is False
    assert report["training_executed"] is False
    working = tmp_path / "working/images/GHIMG_OWNER_0001.png"
    with Image.open(working) as image:
        assert image.getpixel((3, 4)) == (32, 32, 32)
        assert not image.info


def test_owner_consent_record_is_private_pseudonymous_internal_only_and_idempotent(
    tmp_path: Path,
) -> None:
    arguments = {
        "governance_root": tmp_path / "private-governance",
        "repository_root": tmp_path / "repository",
        "acknowledgement": "I_CONFIRM_OWNER_INTERNAL_RESEARCH_CONSENT",
        "withdrawal_operator_id": "OPERATOR_OWNER_001",
    }
    first = initialize_owner_consent(**arguments)
    second = initialize_owner_consent(**arguments)
    record = json.loads(first.record_path.read_text(encoding="utf-8"))
    assert first == second
    assert len(first.participant_id_hash) == 64
    assert record["consent_scope"] == "internal_only"
    assert record["public_release_consent"] is False
    assert record["training_eligible"] is False
    assert "name" not in record and "phone" not in record and "email" not in record
    with pytest.raises(GhanaPrivateError, match="acknowledgement"):
        initialize_owner_consent(**{**arguments, "acknowledgement": "yes"})


def test_private_intake_quarantines_perceptual_duplicate_with_distinct_bytes(
    tmp_path: Path,
) -> None:
    _image(tmp_path / "raw/first.png", phase=2, metadata="A")
    _image(tmp_path / "raw/second.png", phase=2, metadata="B")
    records = [
        _record(
            image_id="GHIMG_OWNER_0011",
            source_path="first.png",
            participant=_hash("one"),
            group="GHGROUP_OWNER_0011",
        ),
        _record(
            image_id="GHIMG_OWNER_0012",
            source_path="second.png",
            participant=_hash("two"),
            group="GHGROUP_OWNER_0012",
        ),
    ]
    outputs = _ingest(tmp_path, records)
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
    assert report["exact_duplicate_count"] == 0
    assert report["near_duplicate_count"] == 1
    assert outputs.quarantined_count == 1


def test_private_intake_perceptual_hash_supports_local_pillow_runtime(tmp_path: Path) -> None:
    _image(tmp_path / "raw/local-runtime.png", phase=3)
    outputs = _ingest(
        tmp_path,
        [
            _record(
                image_id="GHIMG_OWNER_0013",
                source_path="local-runtime.png",
                participant=_hash("local-runtime"),
                group="GHGROUP_OWNER_0013",
            )
        ],
    )

    index = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    assert len(index["records"][0]["perceptual_dhash"]) == 16


def test_pending_deidentification_does_not_write_private_working_copy(tmp_path: Path) -> None:
    _image(tmp_path / "raw/pending.png", phase=4)
    record = _record(
        image_id="GHIMG_OWNER_0014",
        source_path="pending.png",
        participant=_hash("pending"),
        group="GHGROUP_OWNER_0014",
    )
    record["deidentification_status"] = "pending"

    outputs = _ingest(tmp_path, [record])
    index = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))

    assert index["records"][0]["working_relative_path"] is None
    assert report["working_copy_count"] == 0
    assert report["deidentification_pending_count"] == 1


def test_consented_screenshot_text_only_review_preserves_group_and_skips_derivative(
    tmp_path: Path,
) -> None:
    _image(tmp_path / "raw/friend.png", phase=14)
    record = _record(
        image_id="GHIMG_FRIEND_0014",
        source_path="friend.png",
        participant=_hash("unmapped-consented-friend-batch"),
        group="GHGROUP_FRIEND_BATCH_0014",
    )
    record["deidentification_status"] = "pending"
    outputs = _ingest(tmp_path, [record])

    prepare_consented_screenshot_text_only_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        image_id="GHIMG_FRIEND_0014",
        provisional_label="genuine_candidate",
        sender_kind="alphanumeric_label",
        indicators=["branded_sender_context", "normal_transaction_language"],
        reviewer_id="REVIEWER_FRIEND_LABEL_001",
    )
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert indexed["source_group_id"] == "GHGROUP_FRIEND_BATCH_0014"
    assert indexed["working_sha256"] is None
    assert indexed["image_derivative_policy"] == ("excluded_use_private_original_for_ocr_only")
    assert indexed["annotation_state"] == "needs_second_review"
    assert indexed["training_eligible"] is False

    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_FRIEND_0014",
        decision="approve",
        reviewer_id="REVIEWER_FRIEND_LABEL_002",
        reason_code="GENUINE_TRANSACTION_CONFIRMED_001",
    )
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert indexed["final_annotation"]["label"] == "GENUINE"


@pytest.mark.parametrize("case", ["schema", "consent", "quarantine", "derivative"])
def test_consented_screenshot_text_only_review_rejects_unsafe_state(
    tmp_path: Path, case: str
) -> None:
    _image(tmp_path / "raw/friend.png", phase=15)
    record = _record(
        image_id="GHIMG_FRIEND_0015",
        source_path="friend.png",
        participant=_hash("consented-friend"),
        group="GHGROUP_FRIEND_BATCH_0015",
    )
    record["deidentification_status"] = "pending"
    outputs = _ingest(tmp_path, [record])
    index = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    if case == "schema":
        index["schema_version"] = "unknown"
    elif case == "consent":
        index["records"][0]["consent_scope"] = "unknown"
    elif case == "quarantine":
        index["records"][0]["workflow_state"] = "quarantined"
    else:
        index["records"][0]["working_sha256"] = _hash("derivative")
    _write_json(outputs.index_path, index)

    with pytest.raises(GhanaPrivateError):
        prepare_consented_screenshot_text_only_review(
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            image_id="GHIMG_FRIEND_0015",
            provisional_label="genuine_candidate",
            sender_kind="alphanumeric_label",
            indicators=["normal_transaction_language"],
            reviewer_id="REVIEWER_FRIEND_LABEL_001",
        )


def test_consented_screenshot_text_review_preserves_near_duplicate_image_quarantine(
    tmp_path: Path,
) -> None:
    first = _image(tmp_path / "raw/first.png", phase=21)
    second = tmp_path / "raw/second.png"
    second.write_bytes(first.read_bytes())
    records = [
        _record(
            image_id="GHIMG_FRIEND_NEAR_0001",
            source_path="first.png",
            participant=_hash("friend-batch"),
            group="GHGROUP_FRIEND_BATCH_0021",
        ),
        _record(
            image_id="GHIMG_FRIEND_NEAR_0002",
            source_path="second.png",
            participant=_hash("friend-batch"),
            group="GHGROUP_FRIEND_BATCH_0021",
        ),
    ]
    for record in records:
        record["deidentification_status"] = "pending"
    outputs = _ingest(tmp_path, records)
    index = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    duplicate = index["records"][1]
    duplicate["quarantine_reason"] = "near_duplicate_of:GHIMG_FRIEND_NEAR_0001"
    _write_json(outputs.index_path, index)

    prepare_consented_screenshot_text_only_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        image_id="GHIMG_FRIEND_NEAR_0002",
        provisional_label="genuine_candidate",
        sender_kind="cropped_unknown",
        indicators=["normal_transaction_language"],
        reviewer_id="REVIEWER_FRIEND_LABEL_001",
    )
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][1]
    assert indexed["workflow_state"] == "quarantined"
    assert indexed["image_quarantine_preserved"] is True
    assert indexed["annotation_state"] == "needs_second_review"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.update(schema_version="old"), "unsupported"),
        (lambda value: value.update(dataset_id="other"), "dataset_id"),
        (lambda value: value.update(records=[]), "requires records"),
        (lambda value: value.update(records=["bad"]), "must be objects"),
    ],
)
def test_intake_rejects_invalid_request_documents(tmp_path: Path, mutation, message: str) -> None:  # type: ignore[no-untyped-def]
    request = {
        "schema_version": "ghana-private-intake-request-v1",
        "dataset_id": "ghana-private",
        "records": [{}],
    }
    mutation(request)
    with pytest.raises(GhanaPrivateError, match=message):
        ingest_private_screenshots(
            request_path=_write_json(tmp_path / "request.json", request),
            raw_root=tmp_path / "raw",
            working_root=tmp_path / "working",
            index_path=tmp_path / "index.json",
            report_path=tmp_path / "report.json",
            repository_root=tmp_path / "repository",
        )


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"image_id": "bad"}, "image_id"),
        ({"participant_id_hash": "bad"}, "participant_id_hash"),
        ({"consent_scope": "missing"}, "consent scope"),
        ({"permission_reference": "bad"}, "permission_reference"),
        ({"source_group_id": "bad"}, "source_group_id"),
        ({"source_path": "../escape.png"}, "escapes"),
        ({"redaction_regions": [[95, 63, 2, 2]]}, "outside"),
    ],
)
def test_intake_fails_closed_on_identity_path_consent_and_region_errors(
    tmp_path: Path, change: dict[str, object], message: str
) -> None:
    _image(tmp_path / "raw/source.png", phase=4)
    record = _record(
        image_id="GHIMG_OWNER_0101",
        source_path="source.png",
        participant=_hash("owner"),
        group="GHGROUP_OWNER_0101",
    )
    record.update(change)
    with pytest.raises(GhanaPrivateError, match=message):
        _ingest(tmp_path, [record])


def test_intake_rejects_pii_filename_duplicate_ids_and_hostile_bytes(tmp_path: Path) -> None:
    _image(tmp_path / "pii/raw/0551234567.png", phase=1)
    record = _record(
        image_id="GHIMG_OWNER_0201",
        source_path="0551234567.png",
        participant=_hash("owner"),
        group="GHGROUP_OWNER_0201",
    )
    with pytest.raises(GhanaPrivateError, match="filename"):
        _ingest(tmp_path / "pii", [record])

    _image(tmp_path / "dupes/raw/source.png", phase=1)
    duplicate_record = _record(
        image_id="GHIMG_OWNER_0202",
        source_path="source.png",
        participant=_hash("owner"),
        group="GHGROUP_OWNER_0202",
    )
    with pytest.raises(GhanaPrivateError, match="IDs must be unique"):
        _ingest(tmp_path / "dupes", [duplicate_record, duplicate_record])

    hostile_root = tmp_path / "hostile"
    (hostile_root / "raw").mkdir(parents=True)
    (hostile_root / "raw/source.png").write_text("not an image", encoding="utf-8")
    hostile = _record(
        image_id="GHIMG_OWNER_0203",
        source_path="source.png",
        participant=_hash("owner"),
        group="GHGROUP_OWNER_0203",
    )
    with pytest.raises(GhanaPrivateError, match="cannot be decoded"):
        _ingest(hostile_root, [hostile])


def test_message_deidentification_preserves_language_signals_and_indexes_sender_kind(
    tmp_path: Path,
) -> None:
    source = tmp_path / "messages.csv"
    source.write_text(
        "Sender,Text\n"
        '0551234567,"Your ballance is GHS 20.00. Ref AB12CD3456 visit https://bad.test"\n'
        'MobileMoney,"Confirmed. Call +233 501 234 567 or a@example.test"\n'
        '1234,"Empty balnce warning"\n',
        encoding="utf-8",
    )
    outputs = index_imazing_messages(
        source_csv=source,
        index_path=tmp_path / "message-index.json",
        report_path=tmp_path / "message-report.json",
        participant_id_hash=_hash("owner"),
        permission_reference="PERMISSION_OWNER_001",
        repository_root=tmp_path / "repository",
    )
    index_text = outputs.index_path.read_text(encoding="utf-8")
    index = json.loads(index_text)
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
    assert outputs.record_count == 3
    assert "0551234567" not in index_text
    assert "+233 501 234 567" not in index_text
    assert "ballance" in index["records"][0]["candidate_transcript"]
    assert "balnce" in index["records"][2]["candidate_transcript"]
    assert report["sender_kind_counts"] == {
        "alphanumeric_label": 1,
        "phone_number": 1,
        "shortcode": 1,
    }
    assert report["raw_sender_values_written"] is False
    assert report["training_eligible"] is False


def test_android_sms_normalization_filters_providers_deduplicates_and_exports(
    tmp_path: Path,
) -> None:
    first = _sms_xml(
        tmp_path / "all.xml",
        [
            ("MobileMoney", "1786384800000", "1", "Payment received GHS 10.00 Ref ABC12345"),
            ("T-CASH", "1786384860000", "1", "Cash received GHS 20.00 Ref XYZ12345"),
            ("Private Person", "1786384920000", "1", "Unrelated private conversation"),
            ("T Cash", "1786384980000", "2", "Outgoing message"),
        ],
    )
    second = _sms_xml(
        tmp_path / "selected.xml",
        [
            ("MobileMoney", "1786384800000", "1", "Payment received GHS 10.00 Ref ABC12345"),
            ("Telecel", "1786385040000", "1", "Account service information"),
        ],
    )
    normalized_path = tmp_path / "private" / "android.csv"
    report_path = tmp_path / "private" / "android-report.json"
    outputs = normalize_android_sms_backups(
        source_paths=[first, second],
        normalized_csv_path=normalized_path,
        report_path=report_path,
        allowed_sender_providers={
            "MobileMoney": "MTN_MOMO",
            "T Cash": "TELECEL_CASH",
            "T-CASH": "TELECEL_CASH",
            "Telecel": "TELECEL_CASH",
        },
        repository_root=tmp_path / "repository",
    )

    with normalized_path.open(encoding="utf-8", newline="") as stream:
        normalized = list(csv.DictReader(stream))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert outputs.parsed_message_count == 6
    assert outputs.selected_message_count == 3
    assert outputs.exact_duplicate_count == 1
    assert {row["sender_identifier"] for row in normalized} == {
        "MobileMoney",
        "T-CASH",
        "Telecel",
    }
    assert {row["source_provenance"] for row in normalized} == {"owner_android_local_backup"}
    assert all(row["direction"] == "incoming" for row in normalized)
    assert report["ignored_sender_message_count"] == 1
    assert report["ignored_direction_message_count"] == 1
    assert report["provider_family_counts"] == {"MTN_MOMO": 1, "TELECEL_CASH": 2}
    assert report["training_eligible"] is False

    index_path = tmp_path / "private" / "index.json"
    message_report_path = tmp_path / "private" / "message-report.json"
    index_imazing_messages(
        source_csv=normalized_path,
        index_path=index_path,
        report_path=message_report_path,
        participant_id_hash=_hash("owner"),
        permission_reference="PERMISSION_OWNER_001",
        repository_root=tmp_path / "repository",
        text_column="message_body",
        sender_column="sender_identifier",
    )
    corpus = export_private_imazing_genuine_corpus(
        source_csv=normalized_path,
        index_path=index_path,
        report_path=message_report_path,
        output_root=tmp_path / "private" / "corpus",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_STEWARD_003",
        expected_sender_labels=frozenset({"MobileMoney", "T Cash", "T-CASH", "Telecel"}),
        expected_source_provenance="owner_android_local_backup",
    )
    with corpus.sanitized_csv_path.open(encoding="utf-8", newline="") as stream:
        sanitized = list(csv.DictReader(stream))
    message_report = json.loads(message_report_path.read_text(encoding="utf-8"))
    assert corpus.raw_record_count == 3
    assert {row["provider_family"] for row in sanitized} == {
        "MTN_MOMO",
        "TELECEL_CASH",
    }
    assert message_report["provider_family_counts"] == {"MTN_MOMO": 1, "TELECEL_CASH": 2}
    assert message_report["training_eligible"] is False


@pytest.mark.parametrize("case", ["doctype", "count", "duplicate_document", "inside_repo"])
def test_android_sms_normalization_rejects_unsafe_sources(tmp_path: Path, case: str) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    source = _sms_xml(
        tmp_path / "source.xml",
        [("MobileMoney", "1786384800000", "1", "Account information")],
        count=2 if case == "count" else None,
    )
    sources = [source, source] if case == "duplicate_document" else [source]
    if case == "doctype":
        source.write_text(
            '<!DOCTYPE smses [<!ENTITY x "unsafe">]><smses count="0"></smses>',
            encoding="utf-8",
        )
    output = repository / "android.csv" if case == "inside_repo" else tmp_path / "android.csv"
    with pytest.raises(GhanaPrivateError):
        normalize_android_sms_backups(
            source_paths=sources,
            normalized_csv_path=output,
            report_path=tmp_path / "report.json",
            allowed_sender_providers={"MobileMoney": "MTN_MOMO"},
            repository_root=repository,
        )


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ("no_source", "at least one"),
        ("bad_provenance", "provenance"),
        ("empty_mapping", "approved sender"),
        ("invalid_sender", "mapping"),
        ("duplicate_sender", "duplicated"),
        ("missing_source", "could not be opened"),
        ("empty_source", "size"),
        ("malformed", "malformed"),
        ("wrong_root", "schema"),
        ("wrong_child", "schema"),
        ("missing_count", "declared count"),
        ("incomplete_row", "incomplete"),
        ("invalid_timestamp", "timestamp is invalid"),
        ("unsafe_timestamp", "safe range"),
        ("no_selected_rows", "selected no incoming"),
    ],
)
def test_android_sms_normalization_fails_closed_for_invalid_contracts(
    tmp_path: Path, case: str, expected: str
) -> None:
    source = tmp_path / "source.xml"
    source.write_text(
        '<smses count="1"><sms address="MobileMoney" date="1786384800000" '
        'type="1" body="Account information" /></smses>',
        encoding="utf-8",
    )
    sources = [source]
    mappings = {"MobileMoney": "MTN_MOMO"}
    provenance = "owner_android_local_backup"
    if case == "no_source":
        sources = []
    elif case == "bad_provenance":
        provenance = "downloaded_online"
    elif case == "empty_mapping":
        mappings = {}
    elif case == "invalid_sender":
        mappings = {"+233501234567": "MTN_MOMO"}
    elif case == "duplicate_sender":
        mappings = {"MobileMoney": "MTN_MOMO", "mobilemoney": "MTN_MOMO"}
    elif case == "missing_source":
        sources = [tmp_path / "missing.xml"]
    elif case == "empty_source":
        source.write_bytes(b"")
    elif case == "malformed":
        source.write_text("<smses>", encoding="utf-8")
    elif case == "wrong_root":
        source.write_text('<messages count="0" />', encoding="utf-8")
    elif case == "wrong_child":
        source.write_text('<smses count="1"><mms /></smses>', encoding="utf-8")
    elif case == "missing_count":
        source.write_text("<smses />", encoding="utf-8")
    elif case == "incomplete_row":
        source.write_text(
            '<smses count="1"><sms address="MobileMoney" date="1786384800000" type="1" /></smses>',
            encoding="utf-8",
        )
    elif case == "invalid_timestamp":
        source.write_text(
            '<smses count="1"><sms address="MobileMoney" date="invalid" '
            'type="1" body="Account information" /></smses>',
            encoding="utf-8",
        )
    elif case == "unsafe_timestamp":
        source.write_text(
            '<smses count="1"><sms address="MobileMoney" date="0" '
            'type="1" body="Account information" /></smses>',
            encoding="utf-8",
        )
    elif case == "no_selected_rows":
        source.write_text(
            '<smses count="1"><sms address="Other" date="1786384800000" '
            'type="1" body="Private conversation" /></smses>',
            encoding="utf-8",
        )

    with pytest.raises(GhanaPrivateError, match=expected):
        normalize_android_sms_backups(
            source_paths=sources,
            normalized_csv_path=tmp_path / "android.csv",
            report_path=tmp_path / "report.json",
            allowed_sender_providers=mappings,
            repository_root=tmp_path / "repository",
            source_provenance=provenance,
        )


def test_message_index_rejects_missing_file_columns_and_bad_identity(tmp_path: Path) -> None:
    with pytest.raises(GhanaPrivateError, match="does not exist"):
        index_imazing_messages(
            source_csv=tmp_path / "missing.csv",
            index_path=tmp_path / "index.json",
            report_path=tmp_path / "report.json",
            participant_id_hash=_hash("owner"),
            permission_reference="PERMISSION_OWNER_001",
            repository_root=tmp_path / "repository",
        )


def test_owner_message_corpus_deidentifies_deduplicates_and_groups_templates(
    tmp_path: Path,
) -> None:
    source = tmp_path / "owner-messages.csv"
    headers = [
        "sender_identifier",
        "service",
        "direction",
        "sent_at_utc",
        "message_body",
        "source_provenance",
    ]
    rows = [
        {
            "sender_identifier": "MobileMoney",
            "service": "SMS",
            "direction": "incoming",
            "sent_at_utc": "2026-01-01T00:00:00+00:00",
            "message_body": (
                "Payment made for GHS 20.00 to PRIVATE PERSON. "
                "Current Balance GHS 80.00. Transaction ID: 12345678901"
            ),
            "source_provenance": "owner_iphone_local_backup",
        },
        {
            "sender_identifier": "MobileMoney",
            "service": "SMS",
            "direction": "incoming",
            "sent_at_utc": "2026-01-04T00:00:00+00:00",
            "message_body": "Your OTP is 123456. Do not share it.",
            "source_provenance": "owner_iphone_local_backup",
        },
        {
            "sender_identifier": "MobileMoney",
            "service": "SMS",
            "direction": "incoming",
            "sent_at_utc": "2026-01-02T00:00:00+00:00",
            "message_body": (
                "Payment made for GHS 30.00 to PRIVATE PERSON. "
                "Current Balance GHS 50.00. Transaction ID: 22345678901"
            ),
            "source_provenance": "owner_iphone_local_backup",
        },
        {
            "sender_identifier": "MobileMoney",
            "service": "SMS",
            "direction": "incoming",
            "sent_at_utc": "2026-01-03T00:00:00+00:00",
            "message_body": "Keep your account secure and never share your PIN.",
            "source_provenance": "owner_iphone_local_backup",
        },
    ]
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    index_path = tmp_path / "message-index.json"
    report_path = tmp_path / "message-report.json"
    index_imazing_messages(
        source_csv=source,
        index_path=index_path,
        report_path=report_path,
        participant_id_hash=_hash("owner"),
        permission_reference="PERMISSION_OWNER_001",
        repository_root=tmp_path / "repository",
        text_column="message_body",
        sender_column="sender_identifier",
    )
    outputs = export_private_imazing_genuine_corpus(
        source_csv=source,
        index_path=index_path,
        report_path=report_path,
        output_root=tmp_path / "private-corpus",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_STEWARD_003",
    )
    assert outputs.raw_record_count == 3
    assert outputs.deduplicated_record_count == 2
    with outputs.raw_csv_path.open(encoding="utf-8", newline="") as stream:
        raw_rows = list(csv.DictReader(stream))
    with outputs.sanitized_csv_path.open(encoding="utf-8", newline="") as stream:
        sanitized_rows = list(csv.DictReader(stream))
    assert "PRIVATE PERSON" in raw_rows[0]["raw_message_text"]
    transaction = next(
        row for row in sanitized_rows if row["message_category"] == "transaction_confirmation"
    )
    assert "PRIVATE PERSON" not in transaction["sanitized_text"]
    assert "[ENTITY_001]" in transaction["sanitized_text"]
    assert "[AMOUNT_001]" in transaction["sanitized_text"]
    assert "[REFERENCE_001]" in transaction["sanitized_text"]
    assert transaction["duplicate_occurrences"] == "2"
    assert transaction["training_eligible"] == "false"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["raw_record_count"] == 3
    assert report["deduplicated_record_count"] == 2
    assert report["template_group_count"] == 2
    assert report["secret_bearing_message_excluded_count"] == 1
    assert report["splits_frozen"] is False
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert (
        sum(record["workflow_state"] == "needs_second_annotation" for record in index["records"])
        == 3
    )
    assert sum(record["workflow_state"] == "quarantined" for record in index["records"]) == 1
    assert all(record["training_eligible"] is False for record in index["records"])


def test_owner_message_corpus_rejects_changed_source_and_authenticity(tmp_path: Path) -> None:
    source = tmp_path / "owner-messages.csv"
    source.write_text(
        "sender_identifier,service,direction,sent_at_utc,message_body,source_provenance\n"
        "MobileMoney,SMS,incoming,2026-01-01T00:00:00+00:00,Account notice,"
        "owner_iphone_local_backup\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.json"
    report_path = tmp_path / "report.json"
    index_imazing_messages(
        source_csv=source,
        index_path=index_path,
        report_path=report_path,
        participant_id_hash=_hash("owner"),
        permission_reference="PERMISSION_OWNER_001",
        repository_root=tmp_path / "repository",
        text_column="message_body",
        sender_column="sender_identifier",
    )
    source.write_text(source.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(GhanaPrivateError, match="source identity changed"):
        export_private_imazing_genuine_corpus(
            source_csv=source,
            index_path=index_path,
            report_path=report_path,
            output_root=tmp_path / "output",
            repository_root=tmp_path / "repository",
            reviewer_id="REVIEWER_STEWARD_003",
        )


def test_owner_message_corpus_masks_unusual_owner_names_and_excludes_login_codes(
    tmp_path: Path,
) -> None:
    source = tmp_path / "owner-messages.csv"
    headers = [
        "sender_identifier",
        "service",
        "direction",
        "sent_at_utc",
        "message_body",
        "source_provenance",
    ]
    messages = [
        "Y'ello PRIVATE OWNER NAME, Welcome to the service.",
        "Hello, PRIVATE OWNER NAME, you have been registered.",
        "Payment complete. Reference: PRIVATE OWNER NAME,0244000000,1. "
        "Financial Transaction Id: ABC 1234567.",
        "Date: 2026/02/19 22:45:23. Current Balance GHC 17.0004.",
        "<#> Please enter the following code:5501 to complete your login.",
    ]
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        for position, message in enumerate(messages):
            writer.writerow(
                {
                    "sender_identifier": "MobileMoney",
                    "service": "SMS",
                    "direction": "incoming",
                    "sent_at_utc": f"2026-01-0{position + 1}T00:00:00+00:00",
                    "message_body": message,
                    "source_provenance": "owner_iphone_local_backup",
                }
            )
    index_path = tmp_path / "message-index.json"
    report_path = tmp_path / "message-report.json"
    index_imazing_messages(
        source_csv=source,
        index_path=index_path,
        report_path=report_path,
        participant_id_hash=_hash("owner"),
        permission_reference="PERMISSION_OWNER_001",
        repository_root=tmp_path / "repository",
        text_column="message_body",
        sender_column="sender_identifier",
    )
    outputs = export_private_imazing_genuine_corpus(
        source_csv=source,
        index_path=index_path,
        report_path=report_path,
        output_root=tmp_path / "private-corpus",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_STEWARD_003",
    )

    with outputs.sanitized_csv_path.open(encoding="utf-8", newline="") as stream:
        sanitized_rows = list(csv.DictReader(stream))
    sanitized = "\n".join(row["sanitized_text"] for row in sanitized_rows)
    assert "PRIVATE OWNER NAME" not in sanitized
    assert "0244000000" not in sanitized
    assert "1234567" not in sanitized
    assert "5501" not in sanitized
    assert "2026/02/19" not in sanitized
    assert "22:45:23" not in sanitized
    assert "GHC 17.0004" not in sanitized
    assert sanitized.count("[ENTITY_001]") >= 2
    assert "[REFERENCE_TEXT_001]" in sanitized
    assert "[REFERENCE_001]" in sanitized
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["raw_record_count"] == 4
    assert report["secret_bearing_message_excluded_count"] == 1


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("invalid_records", "index records are invalid"),
        ("duplicate_row", "source-row mapping is invalid"),
        ("missing_row", "absent from its index"),
        ("changed_sender", "authenticity boundary changed"),
        ("invalid_message_id", "identifier is invalid"),
        ("extra_index_record", "row counts differ"),
        ("bad_schema", "source schema is invalid"),
    ],
)
def test_owner_message_corpus_rejects_unsafe_private_state(
    tmp_path: Path, case: str, message: str
) -> None:
    source = tmp_path / "owner-messages.csv"
    source.write_text(
        "sender_identifier,service,direction,sent_at_utc,message_body,source_provenance\n"
        "MobileMoney,SMS,incoming,2026-01-01T00:00:00+00:00,Account notice,"
        "owner_iphone_local_backup\n",
        encoding="utf-8",
    )
    index_path = tmp_path / "index.json"
    report_path = tmp_path / "report.json"
    index_imazing_messages(
        source_csv=source,
        index_path=index_path,
        report_path=report_path,
        participant_id_hash=_hash("owner"),
        permission_reference="PERMISSION_OWNER_001",
        repository_root=tmp_path / "repository",
        text_column="message_body",
        sender_column="sender_identifier",
    )
    index = json.loads(index_path.read_text(encoding="utf-8"))
    if case == "invalid_records":
        index["records"] = [None]
    elif case == "duplicate_row":
        index["records"].append(dict(index["records"][0]))
    elif case == "missing_row":
        index["records"][0]["source_row_number"] = 3
    elif case == "changed_sender":
        source.write_text(
            source.read_text(encoding="utf-8").replace("MobileMoney", "Other"), encoding="utf-8"
        )
        index["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    elif case == "invalid_message_id":
        index["records"][0]["message_id"] = None
    elif case == "extra_index_record":
        extra = dict(index["records"][0])
        extra["source_row_number"] = 3
        extra["message_id"] = "GHMSG_EXTRA_RECORD_0001"
        index["records"].append(extra)
    else:
        source.write_text(
            "sender_identifier,message_body\nMobileMoney,Account notice\n", encoding="utf-8"
        )
        index["source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    _write_json(index_path, index)
    with pytest.raises(GhanaPrivateError, match=message):
        export_private_imazing_genuine_corpus(
            source_csv=source,
            index_path=index_path,
            report_path=report_path,
            output_root=tmp_path / "output",
            repository_root=tmp_path / "repository",
            reviewer_id="REVIEWER_STEWARD_003",
        )
    source = tmp_path / "messages.csv"
    source.write_text("Date,Value\nnow,test\n", encoding="utf-8")
    with pytest.raises(GhanaPrivateError, match="columns"):
        index_imazing_messages(
            source_csv=source,
            index_path=tmp_path / "index.json",
            report_path=tmp_path / "report.json",
            participant_id_hash=_hash("owner"),
            permission_reference="PERMISSION_OWNER_001",
            repository_root=tmp_path / "repository",
        )
    with pytest.raises(GhanaPrivateError, match="participant_id_hash"):
        index_imazing_messages(
            source_csv=source,
            index_path=tmp_path / "index.json",
            report_path=tmp_path / "report.json",
            participant_id_hash="bad",
            permission_reference="PERMISSION_OWNER_001",
            repository_root=tmp_path / "repository",
        )


def test_online_candidate_is_private_rights_review_quarantine_and_deduplicated(
    tmp_path: Path,
) -> None:
    source = _image(tmp_path / "download.png", phase=8, metadata="web metadata")
    arguments = {
        "source_path": source,
        "source_page_url": "https://example.test/public-report",
        "quarantine_root": tmp_path / "online-quarantine",
        "index_path": tmp_path / "online-index.json",
        "report_path": tmp_path / "online-report.json",
        "repository_root": tmp_path / "repository",
        "reviewer_id": "REVIEWER_OWNER_001",
    }
    first = quarantine_online_candidate(**arguments)
    second = quarantine_online_candidate(**arguments)
    index = json.loads(first.index_path.read_text(encoding="utf-8"))
    report = json.loads(first.report_path.read_text(encoding="utf-8"))
    assert first.status == "quarantined_pending_rights_review"
    assert second.status == "duplicate_quarantined"
    assert len(index["records"]) == 1
    assert index["records"][0]["training_eligible"] is False
    assert index["records"][0]["rights_state"] == "unreviewed"
    assert report["automated_scraping_executed"] is False
    assert report["training_eligible_count"] == 0


def test_online_candidate_without_source_page_is_retained_non_training(tmp_path: Path) -> None:
    source = _image(tmp_path / "download.png", phase=9)
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url=None,
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )

    index = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
    record = index["records"][0]
    assert outputs.status == "quarantined_missing_source_page"
    assert record["source_page_url"] is None
    assert record["source_domain"] is None
    assert record["rights_state"] == "source_page_missing"
    assert record["training_eligible"] is False
    assert report["missing_source_page_count"] == 1


@pytest.mark.parametrize(
    "content_class", ["ambiguous_requires_adjudication", "mixed_authenticity_thread"]
)
def test_online_content_review_accepts_non_binary_triage_classes(
    tmp_path: Path, content_class: str
) -> None:
    source = _image(tmp_path / f"{content_class}.png", phase=10)
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url=None,
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )
    review_online_candidate(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        content_class=content_class,
        direct_identifier_state="present",
        reviewer_id="REVIEWER_OWNER_002",
    )

    record = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert record["content_state"] == content_class
    assert record["training_eligible"] is False


@pytest.mark.parametrize(
    "url", ["http://example.test/image", "https://user:pass@example.test/image", "not-a-url"]
)
def test_online_candidate_rejects_unsafe_source_urls(tmp_path: Path, url: str) -> None:
    source = _image(tmp_path / "download.png", phase=8)
    with pytest.raises(GhanaPrivateError, match="HTTPS"):
        quarantine_online_candidate(
            source_path=source,
            source_page_url=url,
            quarantine_root=tmp_path / "online-quarantine",
            index_path=tmp_path / "online-index.json",
            report_path=tmp_path / "online-report.json",
            repository_root=tmp_path / "repository",
            reviewer_id="REVIEWER_OWNER_001",
        )


def test_online_content_review_never_grants_rights_or_training_eligibility(tmp_path: Path) -> None:
    source = _image(tmp_path / "download.png", phase=8)
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url="https://example.test/report",
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )
    review_online_candidate(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        content_class="primary_ghana_momo_fraud",
        direct_identifier_state="present",
        reviewer_id="REVIEWER_OWNER_002",
    )
    record = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
    assert record["content_state"] == "primary_ghana_momo_fraud"
    assert record["rights_state"] == "unreviewed"
    assert record["deidentification_state"] == "required"
    assert record["training_eligible"] is False
    assert report["rights_review_complete_count"] == 0
    assert report["training_eligible_count"] == 0
    with pytest.raises(GhanaPrivateError, match="content class"):
        review_online_candidate(
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            candidate_id=outputs.candidate_id,
            content_class="fraud",
            direct_identifier_state="present",
            reviewer_id="REVIEWER_OWNER_002",
        )


def test_online_permission_attestation_does_not_bypass_training_gates(tmp_path: Path) -> None:
    source = _image(tmp_path / "permission.png", phase=11)
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url=None,
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )
    attest_online_candidate_permission(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        permission_reference="PERMISSION_SITE_20260813",
        reviewer_id="REVIEWER_OWNER_002",
        permission_scope="internal_model_development",
    )

    record = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
    assert record["rights_state"] == "project_owner_attested_permission"
    assert record["permission_scope"] == "internal_model_development"
    assert record["training_eligible"] is False
    assert report["owner_attested_permission_count"] == 1
    assert report["missing_source_page_count"] == 1
    with pytest.raises(GhanaPrivateError, match="permission scope"):
        attest_online_candidate_permission(
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            candidate_id=outputs.candidate_id,
            permission_reference="PERMISSION_SITE_20260813",
            reviewer_id="REVIEWER_OWNER_002",
            permission_scope="public_release",
        )


def test_online_deidentification_requires_permission_identity_and_regions(tmp_path: Path) -> None:
    source = _image(tmp_path / "permission.png", phase=12, metadata="PRIVATE")
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url=None,
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )
    arguments = {
        "source_path": source,
        "index_path": outputs.index_path,
        "candidate_id": outputs.candidate_id,
        "working_root": tmp_path / "working",
        "redaction_regions": [[2, 3, 20, 10]],
        "repository_root": tmp_path / "repository",
        "reviewer_id": "REVIEWER_OWNER_002",
    }
    with pytest.raises(GhanaPrivateError, match="permission"):
        deidentify_online_candidate(**arguments)
    attest_online_candidate_permission(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        permission_reference="PERMISSION_SITE_20260813",
        reviewer_id="REVIEWER_OWNER_002",
        permission_scope="internal_model_development",
    )
    derivative = deidentify_online_candidate(**arguments)
    record = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    with Image.open(derivative.working_path) as image:
        assert image.getpixel((3, 4)) == (32, 32, 32)
        assert "private_note" not in image.info
    assert record["deidentification_state"] == "complete_pending_second_review"
    assert record["training_eligible"] is False
    with pytest.raises(GhanaPrivateError, match="redaction regions"):
        deidentify_online_candidate(**{**arguments, "redaction_regions": []})
    changed = _image(tmp_path / "changed.png", phase=13)
    with pytest.raises(GhanaPrivateError, match="identity changed"):
        deidentify_online_candidate(**{**arguments, "source_path": changed})


def test_online_text_only_review_requires_permission_and_skips_image_derivative(
    tmp_path: Path,
) -> None:
    source = _image(tmp_path / "text-only.png", phase=31)
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url=None,
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )
    review_online_candidate(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        content_class="primary_ghana_momo_fraud",
        direct_identifier_state="present",
        reviewer_id="REVIEWER_OWNER_002",
    )
    arguments = {
        "index_path": outputs.index_path,
        "report_path": outputs.report_path,
        "candidate_id": outputs.candidate_id,
        "source_group_id": "GHGROUP_ONLINE_BATCH_001",
        "provisional_label": "fraud_candidate",
        "sender_kind": "phone_number",
        "indicators": ["numeric_sender", "grammar_or_spelling_errors"],
        "reviewer_id": "REVIEWER_OWNER_003",
    }
    with pytest.raises(GhanaPrivateError, match="permission"):
        prepare_online_candidate_text_only_review(**arguments)
    attest_online_candidate_permission(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        permission_reference="PERMISSION_SITE_20260814",
        reviewer_id="REVIEWER_OWNER_002",
        permission_scope="internal_model_development",
    )
    prepare_online_candidate_text_only_review(**arguments)
    record = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert record["source_group_id"] == "GHGROUP_ONLINE_BATCH_001"
    assert record["annotation_state"] == "needs_second_review"
    assert record["image_derivative_policy"] == "excluded_use_private_original_for_ocr_only"
    assert "working_sha256" not in record
    assert record["training_eligible"] is False
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id=outputs.candidate_id,
        decision="approve",
        reviewer_id="REVIEWER_OWNER_004",
        reason_code="SECOND_REVIEW_CONFIRMED_001",
    )
    record = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert record["final_annotation"]["label"] == "FRAUDULENT"


def test_provisional_annotation_requires_derivative_and_never_approves_training(
    tmp_path: Path,
) -> None:
    source = _image(tmp_path / "permission.png", phase=14)
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url=None,
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )
    arguments = {
        "index_path": outputs.index_path,
        "record_id": outputs.candidate_id,
        "provisional_label": "fraud_candidate",
        "sender_kind": "phone_number",
        "indicators": ["numeric_sender", "grammar_or_spelling_errors"],
        "reviewer_id": "REVIEWER_OWNER_002",
    }
    with pytest.raises(GhanaPrivateError, match="de-identified"):
        record_provisional_annotation(**arguments)
    attest_online_candidate_permission(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        permission_reference="PERMISSION_SITE_20260813",
        reviewer_id="REVIEWER_OWNER_002",
        permission_scope="internal_model_development",
    )
    deidentify_online_candidate(
        source_path=source,
        index_path=outputs.index_path,
        candidate_id=outputs.candidate_id,
        working_root=tmp_path / "working",
        redaction_regions=[[1, 1, 10, 10]],
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_002",
    )
    record_provisional_annotation(**arguments)

    record = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert record["provisional_annotation"]["label"] == "fraud_candidate"
    assert record["annotation_state"] == "needs_second_review"
    assert record["training_eligible"] is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"provisional_label": "fraud"}, "provisional label"),
        ({"sender_kind": "mobile"}, "sender kind"),
        ({"indicators": []}, "fraud indicators"),
        ({"indicators": ["guess"]}, "fraud indicators"),
        ({"record_id": "MISSING_RECORD_001"}, "not found"),
    ],
)
def test_provisional_annotation_rejects_invalid_values(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0030",
        source_path="first.png",
        participant=_hash("annotation"),
        group="GHGROUP_OWNER_0030",
    )
    _image(tmp_path / "raw/first.png", phase=15)
    outputs = _ingest(tmp_path, [record])
    arguments: dict[str, object] = {
        "index_path": outputs.index_path,
        "record_id": "GHIMG_OWNER_0030",
        "provisional_label": "fraud_candidate",
        "sender_kind": "phone_number",
        "indicators": ["numeric_sender"],
        "reviewer_id": "REVIEWER_OWNER_002",
    }
    arguments.update(mutation)
    with pytest.raises(GhanaPrivateError, match=message):
        record_provisional_annotation(**arguments)  # type: ignore[arg-type]


def test_second_review_approves_label_but_keeps_later_gates_closed(tmp_path: Path) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0031",
        source_path="first.png",
        participant=_hash("second-review"),
        group="GHGROUP_OWNER_0031",
    )
    _image(tmp_path / "raw/first.png", phase=16)
    outputs = _ingest(tmp_path, [record])
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id="GHIMG_OWNER_0031",
        provisional_label="fraud_candidate",
        sender_kind="phone_number",
        indicators=["numeric_sender"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    with pytest.raises(GhanaPrivateError, match="independent reviewer"):
        record_second_review(
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            record_id="GHIMG_OWNER_0031",
            decision="approve",
            reviewer_id="REVIEWER_OWNER_001",
            reason_code="SECOND_REVIEW_CONFIRMED_001",
        )
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0031",
        decision="approve",
        reviewer_id="REVIEWER_OWNER_002",
        reason_code="SECOND_REVIEW_CONFIRMED_001",
    )
    reviewed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
    assert reviewed["final_annotation"]["label"] == "FRAUDULENT"
    assert reviewed["annotation_state"] == "label_approved_pending_field_review"
    assert reviewed["training_eligible"] is False
    assert report["final_label_counts"] == {"FRAUDULENT": 1}
    assert report["training_eligible_count"] == 0
    assert report["training_executed"] is False


def test_second_review_excludes_ambiguous_content(tmp_path: Path) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0032",
        source_path="first.png",
        participant=_hash("ambiguous-review"),
        group="GHGROUP_OWNER_0032",
    )
    _image(tmp_path / "raw/first.png", phase=17)
    outputs = _ingest(tmp_path, [record])
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id="GHIMG_OWNER_0032",
        provisional_label="ambiguous",
        sender_kind="unknown",
        indicators=["cropped_context"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0032",
        decision="exclude",
        reviewer_id="REVIEWER_OWNER_002",
        reason_code="AMBIGUOUS_CONTENT_EXCLUDED_001",
    )
    reviewed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert reviewed["final_annotation"]["label"] is None
    assert reviewed["annotation_state"] == "excluded_from_training"
    assert reviewed["training_eligible"] is False


def test_controlled_online_crops_preserve_group_and_redact(tmp_path: Path) -> None:
    source = _image(tmp_path / "mixed.png", phase=18)
    outputs = quarantine_online_candidate(
        source_path=source,
        source_page_url=None,
        quarantine_root=tmp_path / "online-quarantine",
        index_path=tmp_path / "online-index.json",
        report_path=tmp_path / "online-report.json",
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_001",
    )
    attest_online_candidate_permission(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        candidate_id=outputs.candidate_id,
        permission_reference="PERMISSION_SITE_20260813",
        reviewer_id="REVIEWER_OWNER_002",
        permission_scope="internal_model_development",
    )
    deidentify_online_candidate(
        source_path=source,
        index_path=outputs.index_path,
        candidate_id=outputs.candidate_id,
        working_root=tmp_path / "working",
        redaction_regions=[[1, 1, 10, 10]],
        repository_root=tmp_path / "repository",
        reviewer_id="REVIEWER_OWNER_002",
    )
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id=outputs.candidate_id,
        provisional_label="mixed",
        sender_kind="alphanumeric_label",
        indicators=["mixed_message_context"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    arguments = {
        "source_path": source,
        "index_path": outputs.index_path,
        "report_path": outputs.report_path,
        "source_candidate_id": outputs.candidate_id,
        "source_group_id": "GHGROUP_ONLINE_MIXED_001",
        "working_root": tmp_path / "working",
        "crop_box": [10, 8, 60, 40],
        "redaction_regions": [[2, 3, 10, 5]],
        "sender_kind": "alphanumeric_label",
        "indicators": ["normal_transaction_language"],
        "reviewer_id": "REVIEWER_OWNER_001",
        "repository_root": tmp_path / "repository",
    }
    first = create_controlled_online_crop(
        **arguments,
        candidate_id="GHCROP_ONLINE_MIXED_NORMAL_001",
        provisional_label="genuine_candidate",
    )
    create_controlled_online_crop(
        **{
            **arguments,
            "candidate_id": "GHCROP_ONLINE_MIXED_SUSPICIOUS_001",
            "provisional_label": "suspicious_candidate",
            "indicators": ["suspicious_link_or_call_to_action"],
        }
    )
    index = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    derived = [record for record in index["records"] if record.get("derivative_type")]
    with Image.open(first.working_path) as image:
        assert image.size == (60, 40)
        assert image.getpixel((3, 4)) == (32, 32, 32)
        assert not image.info
    assert len(derived) == 2
    assert {record["source_group_id"] for record in derived} == {"GHGROUP_ONLINE_MIXED_001"}
    assert index["records"][0]["annotation_state"] == "superseded_by_controlled_crops"
    assert all(record["training_eligible"] is False for record in derived)


def test_private_redaction_revision_is_audited_and_identity_bound(tmp_path: Path) -> None:
    source = _image(tmp_path / "raw/first.png", phase=19)
    record = _record(
        image_id="GHIMG_OWNER_0033",
        source_path="first.png",
        participant=_hash("redaction-revision"),
        group="GHGROUP_OWNER_0033",
    )
    outputs = _ingest(tmp_path, [record])
    before = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0][
        "working_sha256"
    ]
    revised = revise_private_redaction(
        source_path=source,
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        image_id="GHIMG_OWNER_0033",
        working_root=tmp_path / "working",
        redaction_regions=[[8, 9, 25, 12]],
        reviewer_id="REVIEWER_STEWARD_003",
        reason_code="MASK_PRIVACY_UTILITY_REVISION_001",
        repository_root=tmp_path / "repository",
    )
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert revised.working_sha256 != before
    assert indexed["working_sha256"] == revised.working_sha256
    assert indexed["redaction_revision_history"][0]["reason_code"] == (
        "MASK_PRIVACY_UTILITY_REVISION_001"
    )
    changed = _image(tmp_path / "changed.png", phase=20)
    with pytest.raises(GhanaPrivateError, match="identity changed"):
        revise_private_redaction(
            source_path=changed,
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            image_id="GHIMG_OWNER_0033",
            working_root=tmp_path / "working",
            redaction_regions=[[8, 9, 25, 12]],
            reviewer_id="REVIEWER_STEWARD_003",
            reason_code="MASK_PRIVACY_UTILITY_REVISION_001",
            repository_root=tmp_path / "repository",
        )


def test_private_qa_records_tokenized_fields_and_keeps_training_closed(tmp_path: Path) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0034",
        source_path="first.png",
        participant=_hash("private-qa"),
        group="GHGROUP_OWNER_0034",
    )
    _image(tmp_path / "raw/first.png", phase=21)
    outputs = _ingest(tmp_path, [record])
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id="GHIMG_OWNER_0034",
        provisional_label="genuine_candidate",
        sender_kind="alphanumeric_label",
        indicators=["normal_transaction_language"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0034",
        decision="approve",
        reviewer_id="REVIEWER_OWNER_002",
        reason_code="SECOND_REVIEW_CONFIRMED_001",
    )
    record_private_qa_annotation(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0034",
        working_root=tmp_path / "working",
        transcript="GHS 50.00 received from 0241234567",
        fields_present=["amount", "sender"],
        provider_family="mtn_momo",
        template_family="ios_sms",
        capture_channel="sms",
        device_family="iphone",
        os_family="ios",
        theme="light",
        transcript_quality="complete",
        label_cues_preserved=True,
        reviewer_id="REVIEWER_STEWARD_003",
        repository_root=tmp_path / "repository",
    )
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert indexed["private_qa"]["deidentified_transcript"] == (
        "AMOUNT_TOKEN received from PHONE_TOKEN"
    )
    assert indexed["private_qa"]["fields_present"] == ["amount", "sender"]
    assert indexed["private_qa"]["resolution"] == [96, 64]
    assert indexed["private_qa"]["mask_review"]["metadata_stripped"] is True
    assert indexed["workflow_state"] == "approved_internal"
    assert indexed["annotation_state"] == "qa_approved_pending_dataset_minimum"
    assert indexed["training_eligible"] is False
    assign_private_source_group(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0034",
        source_group_id="GHGROUP_OWNER_0034",
        reviewer_id="REVIEWER_STEWARD_003",
        reason_code="SOURCE_GROUP_CONFIRMED_001",
    )
    with pytest.raises(GhanaPrivateError, match="immutable"):
        assign_private_source_group(
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            record_id="GHIMG_OWNER_0034",
            source_group_id="GHGROUP_OWNER_DIFFERENT_0034",
            reviewer_id="REVIEWER_STEWARD_003",
            reason_code="SOURCE_GROUP_CONFIRMED_001",
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"transcript": ""}, "transcript is invalid"),
        ({"fields_present": []}, "fields are invalid"),
        ({"capture_channel": "email"}, "capture channel"),
        ({"os_family": "windows"}, "OS family"),
        ({"theme": "blue"}, "theme"),
        ({"transcript_quality": "unusable"}, "transcript quality"),
        ({"label_cues_preserved": "yes"}, "label-cue decision"),
        ({"provider_family": ""}, "provider family"),
    ],
)
def test_private_qa_rejects_invalid_review_values(
    tmp_path: Path, mutation: dict[str, object], message: str
) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0035",
        source_path="first.png",
        participant=_hash("private-qa-invalid"),
        group="GHGROUP_OWNER_0035",
    )
    _image(tmp_path / "raw/first.png", phase=22)
    outputs = _ingest(tmp_path, [record])
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id="GHIMG_OWNER_0035",
        provisional_label="fraud_candidate",
        sender_kind="phone_number",
        indicators=["numeric_sender"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0035",
        decision="approve",
        reviewer_id="REVIEWER_OWNER_002",
        reason_code="SECOND_REVIEW_CONFIRMED_001",
    )
    arguments: dict[str, object] = {
        "index_path": outputs.index_path,
        "report_path": outputs.report_path,
        "record_id": "GHIMG_OWNER_0035",
        "working_root": tmp_path / "working",
        "transcript": "Account blocked",
        "fields_present": ["status"],
        "provider_family": "mtn_momo",
        "template_family": "ios_sms",
        "capture_channel": "sms",
        "device_family": "iphone",
        "os_family": "ios",
        "theme": "light",
        "transcript_quality": "complete",
        "label_cues_preserved": True,
        "reviewer_id": "REVIEWER_STEWARD_003",
        "repository_root": tmp_path / "repository",
    }
    arguments.update(mutation)
    with pytest.raises(GhanaPrivateError, match=message):
        record_private_qa_annotation(**arguments)  # type: ignore[arg-type]


def test_private_qa_can_reject_low_utility_without_advancing_workflow(tmp_path: Path) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0036",
        source_path="first.png",
        participant=_hash("private-qa-utility"),
        group="GHGROUP_OWNER_0036",
    )
    _image(tmp_path / "raw/first.png", phase=23)
    outputs = _ingest(tmp_path, [record])
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id="GHIMG_OWNER_0036",
        provisional_label="fraud_candidate",
        sender_kind="cropped_unknown",
        indicators=["cropped_context"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0036",
        decision="approve",
        reviewer_id="REVIEWER_OWNER_002",
        reason_code="SECOND_REVIEW_CONFIRMED_001",
    )
    record_private_qa_annotation(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0036",
        working_root=tmp_path / "working",
        transcript="Payment received",
        fields_present=["status"],
        provider_family="unknown",
        template_family="cropped_sms",
        capture_channel="sms",
        device_family="unknown_phone",
        os_family="other",
        theme="light",
        transcript_quality="partial",
        label_cues_preserved=False,
        reviewer_id="REVIEWER_STEWARD_003",
        repository_root=tmp_path / "repository",
    )
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert indexed["annotation_state"] == "qa_rejected_low_utility"
    assert indexed["workflow_state"] == "needs_transcription"
    with pytest.raises(GhanaPrivateError, match="QA-approved"):
        assign_private_source_group(
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            record_id="GHIMG_OWNER_0036",
            source_group_id="GHGROUP_OWNER_0036",
            reviewer_id="REVIEWER_STEWARD_003",
            reason_code="SOURCE_GROUP_CONFIRMED_001",
        )


def test_private_ocr_truth_exports_raw_and_deidentified_text_without_image_derivative(
    tmp_path: Path,
) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0037",
        source_path="first.png",
        participant=_hash("private-ocr-truth"),
        group="GHGROUP_OWNER_0037",
        regions=[[2, 3, 20, 10]],
    )
    source = _image(tmp_path / "raw/first.png", phase=24, metadata="PRIVATE")
    outputs = _ingest(tmp_path, [record])
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id="GHIMG_OWNER_0037",
        provisional_label="genuine_candidate",
        sender_kind="alphanumeric_label",
        indicators=["normal_transaction_language"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0037",
        decision="approve",
        reviewer_id="REVIEWER_OWNER_002",
        reason_code="SECOND_REVIEW_CONFIRMED_001",
    )
    result = record_private_ocr_ground_truth(
        source_path=source,
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0037",
        truth_root=tmp_path / "private-truth",
        transcript="Available Balance GHS 50.00 Transaction ID ABC12345 Reference 1",
        fields=[
            {
                "name": "balance",
                "raw": "GHS 50.00",
                "normalized": "50.00",
                "bbox": [10, 12, 25, 10],
                "sensitive": True,
            },
            {
                "name": "status",
                "raw": "Available Balance",
                "normalized": "available balance",
                "bbox": [40, 12, 40, 10],
                "sensitive": False,
            },
            {
                "name": "reference",
                "raw": "ABC12345",
                "normalized": "ABC12345",
                "bbox": [40, 30, 40, 10],
                "sensitive": True,
            },
            {
                "name": "reference",
                "raw": "1",
                "normalized": "1",
                "bbox": [80, 30, 10, 10],
                "sensitive": True,
            },
        ],
        reviewer_id="REVIEWER_STEWARD_003",
        repository_root=tmp_path / "repository",
    )
    truth = json.loads(result.truth_path.read_text(encoding="utf-8"))
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert truth["full_transcript"].endswith("Reference 1")
    assert truth["localization_quality"] == "field_verified"
    assert indexed["ocr_ground_truth"]["contains_private_values"] is True
    assert "full_transcript" not in indexed["ocr_ground_truth"]
    assert indexed["annotation_state"] == "ocr_truth_pending_second_review"
    assert indexed["training_eligible"] is False
    assert "minimal_derivative" not in indexed
    index_document = json.loads(outputs.index_path.read_text(encoding="utf-8"))
    index_document["records"].append(
        {
            "image_id": "GHIMG_OWNER_0039",
            "annotation_state": "needs_transcription",
            "training_eligible": False,
        }
    )
    _write_json(outputs.index_path, index_document)
    exported = export_private_ocr_text_corpus(
        index_report_pairs=[(outputs.index_path, outputs.report_path)],
        truth_root=tmp_path / "private-truth",
        output_root=tmp_path / "private-text-corpus",
        reviewer_id="REVIEWER_STEWARD_003",
        repository_root=tmp_path / "repository",
    )
    with exported.raw_csv_path.open(encoding="utf-8", newline="") as stream:
        raw_row = next(csv.DictReader(stream))
    with exported.sanitized_csv_path.open(encoding="utf-8", newline="") as stream:
        sanitized_row = next(csv.DictReader(stream))
    assert raw_row["raw_ocr_text"].endswith("Reference 1")
    assert "GHS 50.00" not in sanitized_row["sanitized_text"]
    assert "ABC12345" not in sanitized_row["sanitized_text"]
    assert "Available Balance" in sanitized_row["sanitized_text"]
    assert "[BALANCE_001]" in sanitized_row["sanitized_text"]
    assert "[REFERENCE_001]" in sanitized_row["sanitized_text"]
    assert "[REFERENCE_002]" in sanitized_row["sanitized_text"]
    assert "[REFERENCE_00[" not in sanitized_row["sanitized_text"]
    assert sanitized_row["training_eligible"] == "false"
    indexed = json.loads(outputs.index_path.read_text(encoding="utf-8"))["records"][0]
    assert indexed["annotation_state"] == "ocr_text_pending_second_review"
    assert indexed["image_derivative_policy"] == "excluded_use_private_original_for_ocr_only"


def test_private_ocr_text_export_requires_private_roots_and_an_index(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    repository_root.mkdir()
    with pytest.raises(GhanaPrivateError, match="truth must be written outside"):
        export_private_ocr_text_corpus(
            index_report_pairs=[],
            truth_root=repository_root / "truth",
            output_root=tmp_path / "output",
            reviewer_id="REVIEWER_STEWARD_003",
            repository_root=repository_root,
        )
    with pytest.raises(GhanaPrivateError, match="CSV corpus must be written outside"):
        export_private_ocr_text_corpus(
            index_report_pairs=[],
            truth_root=tmp_path / "truth",
            output_root=repository_root / "output",
            reviewer_id="REVIEWER_STEWARD_003",
            repository_root=repository_root,
        )
    with pytest.raises(GhanaPrivateError, match="requires at least one index"):
        export_private_ocr_text_corpus(
            index_report_pairs=[],
            truth_root=tmp_path / "truth",
            output_root=tmp_path / "output",
            reviewer_id="REVIEWER_STEWARD_003",
            repository_root=repository_root,
        )
    with pytest.raises(GhanaPrivateError, match=r"unable to read missing-index\.json"):
        export_private_ocr_text_corpus(
            index_report_pairs=[(tmp_path / "missing-index.json", tmp_path / "report.json")],
            truth_root=tmp_path / "truth",
            output_root=tmp_path / "output",
            reviewer_id="REVIEWER_STEWARD_003",
            repository_root=repository_root,
        )


def test_private_text_second_review_is_complete_independent_and_non_training(
    tmp_path: Path,
) -> None:
    source = tmp_path / "deidentified.csv"
    fieldnames = [
        "record_id",
        "source_group_id",
        "label",
        "sender_kind",
        "message_category",
        "sanitized_text",
        "duplicate_occurrences",
        "training_eligible",
    ]
    with source.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(
            [
                {
                    "record_id": "GHMSG_REVIEW_0001",
                    "source_group_id": "GHMSG_GROUP_0001",
                    "label": "GENUINE",
                    "sender_kind": "alphanumeric_label",
                    "message_category": "transaction_confirmation",
                    "sanitized_text": "Payment received for [AMOUNT_001].",
                    "duplicate_occurrences": "2",
                    "training_eligible": "false",
                },
                {
                    "record_id": "GHMSG_REVIEW_0002",
                    "source_group_id": "GHMSG_GROUP_0002",
                    "label": "GENUINE",
                    "sender_kind": "alphanumeric_label",
                    "message_category": "official_service_message",
                    "sanitized_text": "Account information message.",
                    "duplicate_occurrences": "1",
                    "training_eligible": "false",
                },
            ]
        )
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    outputs = review_private_text_corpora(
        corpora=[("owner_messages", source, source_hash)],
        approved_record_ids=frozenset({"GHMSG_REVIEW_0001"}),
        excluded_record_ids=frozenset({"GHMSG_REVIEW_0002"}),
        output_root=tmp_path / "reviewed",
        first_reviewer_id="REVIEWER_STEWARD_003",
        second_reviewer_id="REVIEWER_STEWARD_004",
        repository_root=tmp_path / "repository",
    )

    with outputs.reviewed_csv_path.open(encoding="utf-8", newline="") as stream:
        reviewed = list(csv.DictReader(stream))
    manifest = json.loads(outputs.manifest_path.read_text(encoding="utf-8"))
    assert outputs.approved_record_count == 1
    assert outputs.excluded_record_count == 1
    assert {row["review_decision"] for row in reviewed} == {"approve", "exclude"}
    assert all(row["training_eligible"] == "false" for row in reviewed)
    assert manifest["approved_label_counts"] == {"GENUINE": 1}
    assert manifest["contains_raw_values"] is False
    assert manifest["splits_frozen"] is False


@pytest.mark.parametrize("case", ["same_reviewer", "incomplete", "unsafe", "changed"])
def test_private_text_second_review_rejects_unsafe_state(tmp_path: Path, case: str) -> None:
    source = tmp_path / "deidentified.csv"
    text = "Payment received for [AMOUNT_001]."
    if case == "unsafe":
        text = "Call 0244000000 for help."
    source.write_text(
        "record_id,source_group_id,label,sender_kind,sanitized_text,training_eligible\n"
        f"GHMSG_REVIEW_0001,GHMSG_GROUP_0001,GENUINE,alphanumeric_label,{text},false\n",
        encoding="utf-8",
    )
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if case == "changed":
        source_hash = _hash("different")
    approved = frozenset() if case == "incomplete" else frozenset({"GHMSG_REVIEW_0001"})
    second_reviewer = "REVIEWER_STEWARD_003" if case == "same_reviewer" else "REVIEWER_STEWARD_004"
    with pytest.raises(GhanaPrivateError):
        review_private_text_corpora(
            corpora=[("owner_messages", source, source_hash)],
            approved_record_ids=approved,
            excluded_record_ids=frozenset(),
            output_root=tmp_path / "reviewed",
            first_reviewer_id="REVIEWER_STEWARD_003",
            second_reviewer_id=second_reviewer,
            repository_root=tmp_path / "repository",
        )


def test_synthetic_clean_text_pilot_is_balanced_deterministic_and_non_training(
    tmp_path: Path,
) -> None:
    first = generate_private_synthetic_clean_text_corpus(
        output_root=tmp_path / "synthetic-first",
        repository_root=tmp_path / "repository",
    )
    second = generate_private_synthetic_clean_text_corpus(
        output_root=tmp_path / "synthetic-second",
        repository_root=tmp_path / "repository",
    )

    with first.corpus_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert first.record_count == 90
    assert first.source_group_count == 30
    assert first.corpus_sha256 == second.corpus_sha256
    assert manifest["label_counts"] == {
        "FRAUDULENT": 30,
        "GENUINE": 30,
        "SUSPICIOUS": 30,
    }
    assert len({row["source_group_id"] for row in rows}) == 30
    assert len({row["sanitized_text"] for row in rows}) == 90
    assert all(row["source_kind"] == "synthetic_clean" for row in rows)
    assert all(row["provider_family"] == "CONTROLLED_SYNTHETIC" for row in rows)
    assert all(
        "Payment made" not in row["sanitized_text"] or " to [ENTITY_001]" in row["sanitized_text"]
        for row in rows
        if row["label"] == "GENUINE"
    )
    assert {
        action
        for action in ("Payment received", "Cash In received", "Payment made", "Transfer received")
        if any(action in row["sanitized_text"] for row in rows if row["label"] == "GENUINE")
    } == {"Payment received", "Cash In received", "Payment made", "Transfer received"}
    assert all(row["fictitious_values_only"] == "true" for row in rows)
    assert all(row["training_eligible"] == "false" for row in rows)
    assert manifest["second_review_required"] is True
    assert manifest["splits_frozen"] is False


def test_private_text_split_readiness_counts_groups_and_fails_closed(
    tmp_path: Path,
) -> None:
    reviewed = tmp_path / "private" / "reviewed.csv"
    reviewed.parent.mkdir(parents=True)
    fields = [
        "record_id",
        "source_group_id",
        "source_corpus",
        "label",
        "review_decision",
        "training_eligible",
    ]
    labels = ("FRAUDULENT", "GENUINE", "SUSPICIOUS")
    rows: list[dict[str, str]] = []
    for number in range(12):
        rows.append(
            {
                "record_id": f"GHCONTROLLED_{number:04d}",
                "source_group_id": f"GHGROUP_CONTROLLED_{number:04d}",
                "source_corpus": "screenshot_ocr",
                "label": labels[number % len(labels)],
                "review_decision": "approve",
                "training_eligible": "false",
            }
        )
    for number in range(30):
        rows.append(
            {
                "record_id": f"GHSYNTHETIC_{number:04d}",
                "source_group_id": f"GHGROUP_SYNTHETIC_{number:04d}",
                "source_corpus": "synthetic_clean",
                "label": labels[number % len(labels)],
                "review_decision": "approve",
                "training_eligible": "false",
            }
        )
    rows.append(
        {
            "record_id": "GHOWNER_RECORD_0001",
            "source_group_id": "GHGROUP_OWNER_LINEAGE_0001",
            "source_corpus": "owner_iphone_messages",
            "label": "GENUINE",
            "review_decision": "approve",
            "training_eligible": "false",
        }
    )
    with reviewed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    reviewed_hash = hashlib.sha256(reviewed.read_bytes()).hexdigest()
    manifest = _write_json(
        tmp_path / "private" / "review-manifest.json",
        {
            "schema_version": "ghana-private-reviewed-text-corpus-v1",
            "reviewed_csv_sha256": reviewed_hash,
            "approved_record_count": len(rows),
            "training_eligible": False,
            "splits_frozen": False,
        },
    )

    outputs = assess_private_text_split_readiness(
        reviewed_csv_path=reviewed,
        review_manifest_path=manifest,
        report_path=tmp_path / "private" / "readiness.json",
        repository_root=tmp_path / "repository",
    )
    report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
    assert outputs.ready_to_freeze is False
    assert outputs.controlled_real_group_count == 12
    assert outputs.synthetic_clean_group_count == 30
    assert report["blockers"] == ["controlled_real_group_minimum"]
    assert report["record_counts"] == {
        "controlled_real": 12,
        "owner_train_only": 1,
        "synthetic_clean": 30,
    }
    assert report["splits_frozen"] is False
    assert report["training_eligible"] is False

    ready = assess_private_text_split_readiness(
        reviewed_csv_path=reviewed,
        review_manifest_path=manifest,
        report_path=tmp_path / "private" / "ready.json",
        repository_root=tmp_path / "repository",
        minimum_controlled_groups=12,
    )
    assert ready.ready_to_freeze is True


@pytest.mark.parametrize("case", ["minimum", "schema", "hash", "manifest_gate"])
def test_private_text_split_readiness_rejects_invalid_contracts(tmp_path: Path, case: str) -> None:
    reviewed = tmp_path / "private" / "reviewed.csv"
    reviewed.parent.mkdir(parents=True)
    reviewed.write_text(
        "record_id,source_group_id,source_corpus,label,review_decision,training_eligible\n"
        "GHCONTROLLED_0001,GHGROUP_CONTROLLED_0001,screenshot_ocr,FRAUDULENT,approve,false\n",
        encoding="utf-8",
    )
    manifest_value = {
        "schema_version": "ghana-private-reviewed-text-corpus-v1",
        "reviewed_csv_sha256": hashlib.sha256(reviewed.read_bytes()).hexdigest(),
        "approved_record_count": 1,
        "training_eligible": False,
        "splits_frozen": False,
    }
    if case == "schema":
        manifest_value["schema_version"] = "unknown"
    elif case == "hash":
        manifest_value["reviewed_csv_sha256"] = _hash("changed")
    elif case == "manifest_gate":
        manifest_value["training_eligible"] = True
    manifest = _write_json(tmp_path / "private" / "manifest.json", manifest_value)
    with pytest.raises(GhanaPrivateError):
        assess_private_text_split_readiness(
            reviewed_csv_path=reviewed,
            review_manifest_path=manifest,
            report_path=tmp_path / "private" / "readiness.json",
            repository_root=tmp_path / "repository",
            minimum_controlled_groups=0 if case == "minimum" else 30,
        )


@pytest.mark.parametrize(
    "case",
    ["duplicate", "approval_gate", "source", "cross_bucket", "label", "count", "blockers"],
)
def test_private_text_split_readiness_rejects_malformed_rows_and_reports_blockers(
    tmp_path: Path, case: str
) -> None:
    reviewed = tmp_path / "private" / "reviewed.csv"
    reviewed.parent.mkdir(parents=True)
    fields = [
        "record_id",
        "source_group_id",
        "source_corpus",
        "label",
        "review_decision",
        "training_eligible",
    ]
    rows = [
        {
            "record_id": "GHCONTROLLED_0001",
            "source_group_id": "GHGROUP_CONTROLLED_0001",
            "source_corpus": "screenshot_ocr",
            "label": "FRAUDULENT",
            "review_decision": "approve",
            "training_eligible": "false",
        }
    ]
    if case == "duplicate":
        rows.append({**rows[0], "source_group_id": "GHGROUP_CONTROLLED_0002"})
    elif case == "approval_gate":
        rows[0]["review_decision"] = "exclude"
    elif case == "source":
        rows[0]["source_corpus"] = "unsupported_source"
    elif case == "cross_bucket":
        rows.append(
            {
                **rows[0],
                "record_id": "GHSYNTHETIC_0001",
                "source_corpus": "synthetic_clean",
            }
        )
    elif case == "label":
        rows[0]["label"] = "UNKNOWN"
    elif case == "blockers":
        rows.append(
            {
                **rows[0],
                "record_id": "GHSYNTHETIC_0001",
                "source_group_id": "GHGROUP_SYNTHETIC_0001",
                "source_corpus": "synthetic_clean",
            }
        )
    with reviewed.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    manifest = _write_json(
        tmp_path / "private" / "manifest.json",
        {
            "schema_version": "ghana-private-reviewed-text-corpus-v1",
            "reviewed_csv_sha256": hashlib.sha256(reviewed.read_bytes()).hexdigest(),
            "approved_record_count": len(rows) + (1 if case == "count" else 0),
            "training_eligible": False,
            "splits_frozen": False,
        },
    )
    arguments = {
        "reviewed_csv_path": reviewed,
        "review_manifest_path": manifest,
        "report_path": tmp_path / "private" / "readiness.json",
        "repository_root": tmp_path / "repository",
    }
    if case == "blockers":
        outputs = assess_private_text_split_readiness(**arguments)
        report = json.loads(outputs.report_path.read_text(encoding="utf-8"))
        assert report["blockers"] == [
            "controlled_real_group_minimum",
            "synthetic_clean_group_minimum",
            "controlled_real_class_coverage",
        ]
    else:
        with pytest.raises(GhanaPrivateError):
            assess_private_text_split_readiness(**arguments)


def test_synthetic_clean_text_pilot_enforces_private_root_and_group_minimum(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    with pytest.raises(GhanaPrivateError, match="outside"):
        generate_private_synthetic_clean_text_corpus(
            output_root=repository / "synthetic",
            repository_root=repository,
        )
    with pytest.raises(GhanaPrivateError, match="safe range"):
        generate_private_synthetic_clean_text_corpus(
            output_root=tmp_path / "synthetic",
            repository_root=repository,
            source_group_count=19,
        )


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ([], "requires field annotations"),
        (
            [
                {
                    "name": "unknown",
                    "raw": "value",
                    "normalized": "value",
                    "bbox": [1, 1, 10, 10],
                    "sensitive": True,
                }
            ],
            "field name",
        ),
        (
            [
                {
                    "name": "status",
                    "raw": "blocked",
                    "normalized": "blocked",
                    "bbox": [1, 1, 10, 10],
                    "sensitive": "yes",
                }
            ],
            "privacy flag",
        ),
    ],
)
def test_private_ocr_truth_rejects_unsafe_fields(
    tmp_path: Path, fields: list[dict[str, object]], message: str
) -> None:
    record = _record(
        image_id="GHIMG_OWNER_0038",
        source_path="first.png",
        participant=_hash("private-ocr-invalid"),
        group="GHGROUP_OWNER_0038",
    )
    source = _image(tmp_path / "raw/first.png", phase=25)
    outputs = _ingest(tmp_path, [record])
    record_provisional_annotation(
        index_path=outputs.index_path,
        record_id="GHIMG_OWNER_0038",
        provisional_label="fraud_candidate",
        sender_kind="phone_number",
        indicators=["numeric_sender"],
        reviewer_id="REVIEWER_OWNER_001",
    )
    record_second_review(
        index_path=outputs.index_path,
        report_path=outputs.report_path,
        record_id="GHIMG_OWNER_0038",
        decision="approve",
        reviewer_id="REVIEWER_OWNER_002",
        reason_code="SECOND_REVIEW_CONFIRMED_001",
    )
    with pytest.raises(GhanaPrivateError, match=message):
        record_private_ocr_ground_truth(
            source_path=source,
            index_path=outputs.index_path,
            report_path=outputs.report_path,
            record_id="GHIMG_OWNER_0038",
            truth_root=tmp_path / "private-truth",
            transcript="Account blocked",
            fields=fields,
            reviewer_id="REVIEWER_STEWARD_003",
            repository_root=tmp_path / "repository",
        )


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("records_not_list", "index records"),
        ("record_not_object", "record is invalid"),
        ("duplicate_id", "identifier is invalid"),
        ("missing_truth_path", "truth path is invalid"),
        ("truth_path_escape", "escaped its root"),
        ("truth_hash_changed", "truth identity changed"),
        ("truth_content_invalid", "truth content is invalid"),
        ("no_sensitive_fields", "no de-identification fields"),
        ("invalid_sensitive_field", "cannot be de-identified"),
        ("sensitive_value_absent", "absent from its transcript"),
        ("label_not_approved", "requires approved labels"),
        ("invalid_label", "label or source group"),
        ("invalid_indicators", "indicators are invalid"),
        ("no_ocr_records", "found no OCR truth records"),
    ],
)
def test_private_ocr_text_export_rejects_unsafe_state(
    tmp_path: Path, case: str, message: str
) -> None:
    truth_root = tmp_path / "truth"
    truth_path = _write_json(
        truth_root / "GHIMG_OWNER_0040.json",
        {
            "full_transcript": "Call 0550000000 now",
            "fields": [
                {
                    "name": "sender_phone",
                    "raw": "0550000000",
                    "normalized": "0550000000",
                    "bbox": [1, 1, 10, 10],
                    "sensitive": True,
                }
            ],
        },
    )
    record: dict[str, object] = {
        "image_id": "GHIMG_OWNER_0040",
        "source_group_id": "GHGROUP_OWNER_0040",
        "final_annotation": {"decision": "approve", "label": "FRAUDULENT"},
        "provisional_annotation": {"sender_kind": "phone_number", "indicators": ["numeric_sender"]},
        "ocr_ground_truth": {
            "truth_relative_path": truth_path.name,
            "truth_sha256": _hash(truth_path.read_text(encoding="utf-8")),
        },
    }
    records: object = [record]
    if case == "records_not_list":
        records = {}
    elif case == "record_not_object":
        records = [None]
    elif case == "duplicate_id":
        records = [record, dict(record)]
    elif case == "missing_truth_path":
        record["ocr_ground_truth"] = {"truth_sha256": _hash("missing")}
    elif case == "truth_path_escape":
        record["ocr_ground_truth"] = {
            "truth_relative_path": "../outside.json",
            "truth_sha256": _hash("outside"),
        }
    elif case == "truth_hash_changed":
        cast_metadata = record["ocr_ground_truth"]
        assert isinstance(cast_metadata, dict)
        cast_metadata["truth_sha256"] = _hash("changed")
    elif case in {
        "truth_content_invalid",
        "no_sensitive_fields",
        "invalid_sensitive_field",
        "sensitive_value_absent",
    }:
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        if case == "truth_content_invalid":
            truth["fields"] = "invalid"
        elif case == "no_sensitive_fields":
            truth["fields"][0]["sensitive"] = False
        elif case == "invalid_sensitive_field":
            truth["fields"][0]["name"] = "unknown"
        else:
            truth["fields"][0]["raw"] = "0551111111"
        _write_json(truth_path, truth)
        cast_metadata = record["ocr_ground_truth"]
        assert isinstance(cast_metadata, dict)
        cast_metadata["truth_sha256"] = _hash(truth_path.read_text(encoding="utf-8"))
    elif case == "label_not_approved":
        record["final_annotation"] = {"decision": "exclude", "label": "FRAUDULENT"}
    elif case == "invalid_label":
        record["final_annotation"] = {"decision": "approve", "label": "UNKNOWN"}
    elif case == "invalid_indicators":
        record["provisional_annotation"] = {"indicators": "numeric_sender"}
    elif case == "no_ocr_records":
        record.pop("ocr_ground_truth")

    index_path = _write_json(tmp_path / "index.json", {"records": records})
    with pytest.raises(GhanaPrivateError, match=message):
        export_private_ocr_text_corpus(
            index_report_pairs=[(index_path, tmp_path / "report.json")],
            truth_root=truth_root,
            output_root=tmp_path / "output",
            reviewer_id="REVIEWER_STEWARD_003",
            repository_root=tmp_path / "repository",
        )


def test_review_workflow_is_ordered_auditable_and_fail_closed(tmp_path: Path) -> None:
    index_path = _write_json(
        tmp_path / "index.json",
        {
            "schema_version": "ghana-private-index-v1",
            "records": [
                {
                    "image_id": "GHIMG_OWNER_0301",
                    "workflow_state": "needs_deidentification",
                    "review_history": [],
                }
            ],
        },
    )
    advance_review(
        index_path=index_path,
        image_id="GHIMG_OWNER_0301",
        expected_state="needs_deidentification",
        next_state="needs_transcription",
        reviewer_id="REVIEWER_OWNER_001",
        reason_code="REDACTION_CHECKED_001",
    )
    record = json.loads(index_path.read_text(encoding="utf-8"))["records"][0]
    assert record["workflow_state"] == "needs_transcription"
    assert record["review_history"][0]["reviewer_id"] == "REVIEWER_OWNER_001"
    with pytest.raises(GhanaPrivateError, match="changed"):
        advance_review(
            index_path=index_path,
            image_id="GHIMG_OWNER_0301",
            expected_state="needs_deidentification",
            next_state="needs_transcription",
            reviewer_id="REVIEWER_OWNER_001",
            reason_code="REDACTION_CHECKED_001",
        )
    with pytest.raises(GhanaPrivateError, match="not allowed"):
        advance_review(
            index_path=index_path,
            image_id="GHIMG_OWNER_0301",
            expected_state="needs_transcription",
            next_state="approved_internal",
            reviewer_id="REVIEWER_OWNER_001",
            reason_code="REDACTION_CHECKED_001",
        )


def _approved_record(position: int) -> dict[str, object]:
    return {
        "image_id": f"GHIMG_APPROVED_{position:04d}",
        "source_group_id": f"GHGROUP_APPROVED_{position:04d}",
        "participant_id_hash": _hash(f"participant-{position}"),
        "provenance": "controlled_real",
        "working_relative_path": f"images/GHIMG_APPROVED_{position:04d}.png",
        "working_sha256": _hash(f"image-{position}"),
        "consent_scope": "internal_only",
        "workflow_state": "approved_internal",
        "training_eligible": True,
    }


def test_group_split_is_deterministic_leakage_safe_and_test_sealed(tmp_path: Path) -> None:
    records = [_approved_record(position) for position in range(20)]
    index_path = _write_json(
        tmp_path / "index.json",
        {"schema_version": "ghana-private-index-v1", "records": records},
    )
    first = freeze_group_splits(
        index_path=index_path,
        manifest_path=tmp_path / "split.json",
        report_path=tmp_path / "split-report.json",
        minimum_controlled_groups=20,
        minimum_synthetic_groups=0,
    )
    second = freeze_group_splits(
        index_path=index_path,
        manifest_path=tmp_path / "split-2.json",
        report_path=tmp_path / "split-report-2.json",
        minimum_controlled_groups=20,
        minimum_synthetic_groups=0,
    )
    report = json.loads(first.report_path.read_text(encoding="utf-8"))
    development = load_development_records(first.manifest_path)
    assert first.manifest_sha256 == second.manifest_sha256
    assert report["split_counts"] == {"test": 3, "train": 14, "validation": 3}
    assert report["group_intersections"] == {
        "train_test": [],
        "train_validation": [],
        "validation_test": [],
    }
    assert len(development) == 17
    assert all(record["split"] != "test" for record in development)


def test_split_rejects_empty_unapproved_and_missing_working_image(tmp_path: Path) -> None:
    for name, records, message in (
        ("none", [], "no training-eligible"),
        (
            "pending",
            [{**_approved_record(1), "workflow_state": "needs_deidentification"}],
            "no training-eligible",
        ),
        ("missing", [{**_approved_record(2), "working_sha256": None}], "missing"),
    ):
        index_path = _write_json(
            tmp_path / f"{name}.json",
            {"schema_version": "ghana-private-index-v1", "records": records},
        )
        with pytest.raises(GhanaPrivateError, match=message):
            freeze_group_splits(
                index_path=index_path,
                manifest_path=tmp_path / f"{name}-split.json",
                report_path=tmp_path / f"{name}-report.json",
                minimum_controlled_groups=0,
                minimum_synthetic_groups=0,
            )


def test_split_enforces_pilot_group_minimums(tmp_path: Path) -> None:
    index_path = _write_json(
        tmp_path / "minimum.json",
        {"schema_version": "ghana-private-index-v1", "records": [_approved_record(1)]},
    )
    with pytest.raises(GhanaPrivateError, match="controlled-real group count"):
        freeze_group_splits(
            index_path=index_path,
            manifest_path=tmp_path / "minimum-split.json",
            report_path=tmp_path / "minimum-report.json",
            minimum_controlled_groups=2,
            minimum_synthetic_groups=0,
        )


def test_withdrawal_quarantines_derivative_and_requires_split_rebuild(tmp_path: Path) -> None:
    participant = _hash("withdraw-me")
    working = _image(tmp_path / "working/images/GHIMG_OWNER_0401.png", phase=7)
    index_path = _write_json(
        tmp_path / "index.json",
        {
            "schema_version": "ghana-private-index-v1",
            "records": [
                {
                    "image_id": "GHIMG_OWNER_0401",
                    "participant_id_hash": participant,
                    "working_relative_path": "images/GHIMG_OWNER_0401.png",
                    "working_sha256": _hash("working"),
                    "workflow_state": "approved_internal",
                }
            ],
        },
    )
    count = apply_withdrawals(
        index_path=index_path,
        withdrawn_participants=frozenset({participant}),
        working_root=tmp_path / "working",
        quarantine_root=tmp_path / "quarantine",
        receipt_path=tmp_path / "withdrawal-receipt.json",
    )
    receipt = json.loads((tmp_path / "withdrawal-receipt.json").read_text(encoding="utf-8"))
    record = json.loads(index_path.read_text(encoding="utf-8"))["records"][0]
    assert count == 1
    assert not working.exists()
    assert (tmp_path / "quarantine/GHIMG_OWNER_0401.png").exists()
    assert record["workflow_state"] == "withdrawn"
    assert record["working_sha256"] is None
    assert receipt["split_rebuild_required"] is True
    assert receipt["dependent_artifacts_invalidated"] is True


def test_controlled_edit_has_aligned_mask_and_rejects_unsafe_parameters(tmp_path: Path) -> None:
    source = _image(tmp_path / "source.png", phase=9)
    output = tmp_path / "edited.png"
    mask = tmp_path / "mask.png"
    manifest = create_controlled_edit(
        source_path=source,
        output_path=output,
        mask_path=mask,
        target="amount",
        method="replacement",
        bbox=(5, 6, 60, 20),
        replacement_token="SYNTHETIC_GHS_10",
        edit_id="EDIT_GHANA_0001",
        source_image_id="GHIMG_SOURCE_0001",
        derived_image_id="GHIMG_DERIVED_0001",
    )
    assert manifest["review_state"] == "needs_mask_review"
    assert changed_pixels_are_masked(source, output, mask) is True
    with pytest.raises(GhanaPrivateError, match="synthetic token"):
        create_controlled_edit(
            source_path=source,
            output_path=output,
            mask_path=mask,
            target="amount",
            method="replacement",
            bbox=(5, 6, 60, 20),
            replacement_token="REAL_VALUE",
            edit_id="EDIT_GHANA_0002",
            source_image_id="GHIMG_SOURCE_0002",
            derived_image_id="GHIMG_DERIVED_0002",
        )


def test_changed_pixel_check_rejects_incomplete_mask(tmp_path: Path) -> None:
    source = _image(tmp_path / "source.png", phase=3)
    edited = _image(tmp_path / "edited.png", phase=4)
    Image.new("L", (96, 64), 0).save(tmp_path / "mask.png")
    assert changed_pixels_are_masked(source, edited, tmp_path / "mask.png") is False


def test_safe_summary_contains_counts_only() -> None:
    summary = safe_intake_summary(
        (
            IntakeOutputs(Path("private-a"), Path("report-a"), 10, 2),
            IntakeOutputs(Path("private-b"), Path("report-b"), 5, 1),
        )
    )
    assert summary == {
        "schema_version": "ghana-private-pilot-summary-v1",
        "pipeline_version": "ghana-private-pipeline-v1",
        "run_count": 2,
        "record_count": 15,
        "quarantined_count": 3,
        "private_bytes_in_git": False,
        "training_executed": False,
    }


def test_standalone_text_deidentifier_handles_empty_and_multiple_values() -> None:
    text, counts = deidentify_message_text(
        "  Send GHS 2.00 to 0501234567, ref ZXCV123456 and GHS 3.50.\x00  "
    )
    assert "0501234567" not in text
    assert "ZXCV123456" not in text
    assert counts["AMOUNT_TOKEN"] == 2
    assert counts["PHONE_TOKEN"] == 1
    assert counts["REFERENCE_TOKEN"] == 1
