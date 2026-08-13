from __future__ import annotations

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
    attest_online_candidate_permission,
    changed_pixels_are_masked,
    create_controlled_edit,
    create_controlled_online_crop,
    deidentify_message_text,
    deidentify_online_candidate,
    freeze_group_splits,
    index_imazing_messages,
    ingest_private_screenshots,
    initialize_owner_consent,
    load_development_records,
    quarantine_online_candidate,
    record_provisional_annotation,
    record_second_review,
    review_online_candidate,
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
        assert "private_note" not in image.info


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
    )
    second = freeze_group_splits(
        index_path=index_path,
        manifest_path=tmp_path / "split-2.json",
        report_path=tmp_path / "split-report-2.json",
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
        ("none", [], "no approved"),
        (
            "pending",
            [{**_approved_record(1), "workflow_state": "needs_deidentification"}],
            "no approved",
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
