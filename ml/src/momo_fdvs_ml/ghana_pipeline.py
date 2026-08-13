"""Private Ghana screenshot/message intake, review, withdrawal and split controls."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import uuid
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, cast
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

GHANA_PIPELINE_VERSION: Final = "ghana-private-pipeline-v1"
PRIVATE_INDEX_VERSION: Final = "ghana-private-index-v1"
MESSAGE_INDEX_VERSION: Final = "ghana-message-index-v1"
FROZEN_SPLIT_VERSION: Final = "ghana-private-frozen-split-v1"
WITHDRAWAL_RECEIPT_VERSION: Final = "ghana-withdrawal-receipt-v1"
EDIT_MANIFEST_VERSION: Final = "ghana-controlled-edit-v1"
ONLINE_CANDIDATE_INDEX_VERSION: Final = "ghana-online-candidate-index-v1"
OWNER_CONSENT_ACKNOWLEDGEMENT: Final = "I_CONFIRM_OWNER_INTERNAL_RESEARCH_CONSENT"
ALLOWED_IMAGE_EXTENSIONS: Final = frozenset({".jpg", ".jpeg", ".png", ".webp"})
ALLOWED_IMAGE_FORMATS: Final = frozenset({"JPEG", "PNG", "WEBP"})
MAX_IMAGE_BYTES: Final = 20 * 1024 * 1024
MAX_IMAGE_PIXELS: Final = 40_000_000
NEAR_DUPLICATE_DISTANCE: Final = 6
WORKFLOW_STATES: Final = (
    "ingested",
    "needs_deidentification",
    "needs_transcription",
    "needs_field_annotation",
    "needs_mask_review",
    "needs_second_annotation",
    "needs_adjudication",
    "approved_internal",
    "release_review_pending",
    "release_approved",
    "withdrawn",
    "quarantined",
)
APPROVED_STATES: Final = frozenset({"approved_internal", "release_approved"})
TRANSITIONS: Final = {
    "ingested": frozenset({"needs_deidentification", "quarantined", "withdrawn"}),
    "needs_deidentification": frozenset({"needs_transcription", "quarantined", "withdrawn"}),
    "needs_transcription": frozenset({"needs_field_annotation", "quarantined", "withdrawn"}),
    "needs_field_annotation": frozenset(
        {"needs_mask_review", "needs_second_annotation", "quarantined", "withdrawn"}
    ),
    "needs_mask_review": frozenset({"needs_second_annotation", "quarantined", "withdrawn"}),
    "needs_second_annotation": frozenset(
        {"needs_adjudication", "approved_internal", "quarantined", "withdrawn"}
    ),
    "needs_adjudication": frozenset({"approved_internal", "quarantined", "withdrawn"}),
    "approved_internal": frozenset({"release_review_pending", "withdrawn", "quarantined"}),
    "release_review_pending": frozenset(
        {"release_approved", "approved_internal", "withdrawn", "quarantined"}
    ),
    "release_approved": frozenset({"withdrawn", "quarantined"}),
    "withdrawn": frozenset(),
    "quarantined": frozenset(),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ID = re.compile(r"^[A-Z][A-Z0-9_-]{11,79}$")
_PII_FILENAME = re.compile(
    r"(?:\+?233|0(?:2|5))[\s_-]?\d{3}[\s_-]?\d{4}|@|\b\d{8,}\b", re.IGNORECASE
)
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\d)(?:\+?233[\s-]?|0)(?:2|5)\d(?:[\s-]?\d){7}(?!\d)")
_MONEY = re.compile(r"(?i)(?:GH[₵¢S]|GHS)\s*\d[\d,]*(?:\.\d{1,2})?")
_LONG_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9])(?=[A-Za-z0-9-]{8,}\b)(?=[A-Za-z0-9-]*\d)[A-Za-z0-9-]+"
)


class GhanaPrivateError(RuntimeError):
    """Raised when private intake cannot proceed safely."""


@dataclass(frozen=True)
class IntakeOutputs:
    """Private index and public-safe aggregate report locations."""

    index_path: Path
    report_path: Path
    record_count: int
    quarantined_count: int


@dataclass(frozen=True)
class SplitOutputs:
    """Frozen private split manifest and safe report locations."""

    manifest_path: Path
    report_path: Path
    manifest_sha256: str


@dataclass(frozen=True)
class OnlineCandidateOutputs:
    """One quarantined web candidate and its private queue locations."""

    candidate_id: str
    status: str
    index_path: Path
    report_path: Path


@dataclass(frozen=True)
class OwnerConsentOutputs:
    """Private pseudonymous owner-consent record identifiers."""

    record_path: Path
    participant_id_hash: str
    permission_reference: str


def _expect_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise GhanaPrivateError(f"{label} must be a lowercase SHA-256 value")
    return value


def _expect_opaque_id(value: object, label: str) -> str:
    if not isinstance(value, str) or _OPAQUE_ID.fullmatch(value) is None:
        raise GhanaPrivateError(f"{label} must be an opaque uppercase identifier")
    return value


def _load_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GhanaPrivateError(f"unable to read {path.name}") from exc
    if not isinstance(value, dict):
        raise GhanaPrivateError(f"{path.name} must contain an object")
    return value


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    os.replace(temporary, path)


def _require_outside_repository(path: Path, repository_root: Path, label: str) -> None:
    if path.resolve().is_relative_to(repository_root.resolve()):
        raise GhanaPrivateError(f"{label} must be written outside the repository")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise GhanaPrivateError("private source could not be read") from exc
    return digest.hexdigest()


def initialize_owner_consent(
    *,
    governance_root: Path,
    repository_root: Path,
    acknowledgement: str,
    withdrawal_operator_id: str,
) -> OwnerConsentOutputs:
    """Create a restricted self-owner internal-use record without direct identity fields."""

    if acknowledgement != OWNER_CONSENT_ACKNOWLEDGEMENT:
        raise GhanaPrivateError("exact owner internal-research consent acknowledgement is required")
    operator = _expect_opaque_id(withdrawal_operator_id, "withdrawal_operator_id")
    _require_outside_repository(governance_root, repository_root, "private governance root")
    record_path = governance_root.resolve() / "owner-consent-record.json"
    if record_path.exists():
        record = _load_object(record_path)
        participant = _expect_sha256(record.get("participant_id_hash"), "participant_id_hash")
        permission = _expect_opaque_id(record.get("permission_reference"), "permission_reference")
        return OwnerConsentOutputs(record_path, participant, permission)
    private_token = uuid.uuid4().hex
    participant = _sha256_bytes(private_token.encode())
    permission = f"PERMISSION_OWNER_{uuid.uuid4().hex[:16].upper()}"
    record = {
        "schema_version": "ghana-owner-consent-record-v1",
        "participant_private_token": private_token,
        "participant_id_hash": participant,
        "permission_reference": permission,
        "consent_scope": "internal_only",
        "controlled_derivative_consent": True,
        "public_release_consent": False,
        "source_ownership_asserted": True,
        "withdrawal_operator_id": operator,
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "institutional_or_supervisor_approval": "pending_or_not_applicable",
        "training_eligible": False,
    }
    _atomic_json(record_path, record)
    return OwnerConsentOutputs(record_path, participant, permission)


def _confined_path(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise GhanaPrivateError("source_path must be a non-empty relative path")
    candidate = (root.resolve() / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise GhanaPrivateError("source_path escapes the approved private root")
    if not candidate.is_file():
        raise GhanaPrivateError("private source file does not exist")
    return candidate


def _decode_private_image(path: Path) -> Image.Image:
    if path.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        raise GhanaPrivateError("private image extension is not allowed")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise GhanaPrivateError("private image exceeds the byte limit")
    try:
        with Image.open(path) as opened:
            opened.verify()
        with Image.open(path) as opened:
            if opened.format not in ALLOWED_IMAGE_FORMATS:
                raise GhanaPrivateError("decoded private image format is not allowed")
            if opened.width * opened.height > MAX_IMAGE_PIXELS:
                raise GhanaPrivateError("private image exceeds the pixel limit")
            return ImageOps.exif_transpose(opened).convert("RGB")
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise GhanaPrivateError("private image cannot be decoded") from exc


def _dhash(image: Image.Image) -> str:
    reduced = image.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
    # Pillow added ``get_flattened_data`` after the minimum version supported by
    # the local Python 3.12 development environment. ``getdata`` remains
    # available across both that environment and the pinned Colab runtime.
    if hasattr(reduced, "get_flattened_data"):
        pixels = cast(Sequence[int], reduced.get_flattened_data())
    else:  # pragma: no cover - exercised only by the older workstation Pillow
        pixels = cast(Sequence[int], list(reduced.getdata()))
    bits = 0
    for row in range(8):
        for column in range(8):
            bits = (bits << 1) | int(pixels[row * 9 + column] > pixels[row * 9 + column + 1])
    return f"{bits:016x}"


def _hamming(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def _regions(value: object, *, width: int, height: int) -> tuple[tuple[int, int, int, int], ...]:
    if not isinstance(value, list):
        raise GhanaPrivateError("redaction_regions must be a list")
    regions: list[tuple[int, int, int, int]] = []
    for region in value:
        if (
            not isinstance(region, list)
            or len(region) != 4
            or any(isinstance(item, bool) or not isinstance(item, int) for item in region)
        ):
            raise GhanaPrivateError("redaction regions must be integer [x, y, width, height]")
        x, y, region_width, region_height = region
        if (
            x < 0
            or y < 0
            or region_width < 1
            or region_height < 1
            or x + region_width > width
            or y + region_height > height
        ):
            raise GhanaPrivateError("redaction region is outside the image")
        regions.append((x, y, region_width, region_height))
    return tuple(regions)


def _redacted_derivative(
    image: Image.Image, regions: Sequence[tuple[int, int, int, int]]
) -> Image.Image:
    derivative = image.copy()
    draw = ImageDraw.Draw(derivative)
    for x, y, width, height in regions:
        draw.rectangle((x, y, x + width - 1, y + height - 1), fill=(32, 32, 32))
    return derivative


def _validate_intake_request(value: Mapping[str, object]) -> list[dict[str, object]]:
    if value.get("schema_version") != "ghana-private-intake-request-v1":
        raise GhanaPrivateError("unsupported Ghana private intake request")
    if value.get("dataset_id") != "ghana-private":
        raise GhanaPrivateError("private intake dataset_id must be ghana-private")
    records = value.get("records")
    if not isinstance(records, list) or not records:
        raise GhanaPrivateError("private intake request requires records")
    if not all(isinstance(record, dict) for record in records):
        raise GhanaPrivateError("private intake records must be objects")
    return records


def ingest_private_screenshots(
    *,
    request_path: Path,
    raw_root: Path,
    working_root: Path,
    index_path: Path,
    report_path: Path,
    repository_root: Path,
    withdrawn_participants: frozenset[str] = frozenset(),
) -> IntakeOutputs:
    """Create metadata-stripped, redacted working copies and a restricted private index."""

    records = _validate_intake_request(_load_object(request_path))
    _require_outside_repository(index_path, repository_root, "private index")
    _require_outside_repository(working_root, repository_root, "private working images")
    identifiers: set[str] = set()
    originals: dict[str, str] = {}
    perceptual: dict[str, tuple[str, str]] = {}
    indexed: list[dict[str, object]] = []
    working_images = working_root.resolve() / "images"
    working_images.mkdir(parents=True, exist_ok=True)
    for raw_record in records:
        image_id = _expect_opaque_id(raw_record.get("image_id"), "image_id")
        if image_id in identifiers:
            raise GhanaPrivateError("image IDs must be unique")
        identifiers.add(image_id)
        participant = _expect_sha256(raw_record.get("participant_id_hash"), "participant_id_hash")
        consent_scope = raw_record.get("consent_scope")
        if consent_scope not in {"internal_only", "release_approved"}:
            raise GhanaPrivateError("controlled-real intake requires recorded consent scope")
        permission = _expect_opaque_id(
            raw_record.get("permission_reference"), "permission_reference"
        )
        group_id = _expect_opaque_id(raw_record.get("source_group_id"), "source_group_id")
        source = _confined_path(raw_root, raw_record.get("source_path"))
        if _PII_FILENAME.search(source.name):
            raise GhanaPrivateError("private source filename contains a direct identifier pattern")
        source_hash = _sha256_file(source)
        image = _decode_private_image(source)
        redactions = _regions(
            raw_record.get("redaction_regions", []), width=image.width, height=image.height
        )
        deidentification_status = raw_record.get("deidentification_status")
        if deidentification_status not in {"pending", "complete"}:
            raise GhanaPrivateError("deidentification_status must be pending or complete")
        state = "needs_deidentification"
        quarantine_reason: str | None = None
        if participant in withdrawn_participants:
            state = "withdrawn"
            quarantine_reason = "participant_withdrawn"
        elif source_hash in originals:
            state = "quarantined"
            quarantine_reason = f"exact_duplicate_of:{originals[source_hash]}"
        derivative = _redacted_derivative(image, redactions)
        perceptual_hash = _dhash(derivative)
        if quarantine_reason is None:
            for prior_id, prior_hash in perceptual.values():
                if _hamming(perceptual_hash, prior_hash) <= NEAR_DUPLICATE_DISTANCE:
                    state = "quarantined"
                    quarantine_reason = f"near_duplicate_of:{prior_id}"
                    break
        originals.setdefault(source_hash, image_id)
        perceptual[image_id] = (image_id, perceptual_hash)
        working_relative: str | None = None
        working_hash: str | None = None
        if state not in {"withdrawn", "quarantined"} and deidentification_status == "complete":
            output = working_images / f"{image_id}.png"
            derivative.save(output, format="PNG", optimize=False)
            working_relative = output.relative_to(working_root.resolve()).as_posix()
            working_hash = _sha256_file(output)
        indexed.append(
            {
                "image_id": image_id,
                "source_group_id": group_id,
                "participant_id_hash": participant,
                "consent_scope": consent_scope,
                "permission_reference": permission,
                "source_locator_sha256": _sha256_bytes(
                    str(raw_record.get("source_path")).encode("utf-8")
                ),
                "original_sha256": source_hash,
                "working_relative_path": working_relative,
                "working_sha256": working_hash,
                "perceptual_dhash": perceptual_hash,
                "redaction_region_count": len(redactions),
                "deidentification_status": deidentification_status,
                "provider_family": str(raw_record.get("provider_family", "unknown")),
                "template_family": str(raw_record.get("template_family", "unknown")),
                "capture_channel": str(raw_record.get("capture_channel", "sms")),
                "device_family": str(raw_record.get("device_family", "unknown")),
                "theme": str(raw_record.get("theme", "unknown")),
                "provenance": "controlled_real",
                "workflow_state": state,
                "quarantine_reason": quarantine_reason,
                "review_history": [],
            }
        )
    index = {
        "schema_version": PRIVATE_INDEX_VERSION,
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "dataset_id": "ghana-private",
        "records": indexed,
    }
    _atomic_json(index_path, index)
    state_counts = Counter(str(record["workflow_state"]) for record in indexed)
    report = {
        "schema_version": "ghana-private-intake-report-v1",
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "dataset_id": "ghana-private",
        "record_count": len(indexed),
        "workflow_state_counts": dict(sorted(state_counts.items())),
        "exact_duplicate_count": sum(
            str(record.get("quarantine_reason", "")).startswith("exact_duplicate_of:")
            for record in indexed
        ),
        "near_duplicate_count": sum(
            str(record.get("quarantine_reason", "")).startswith("near_duplicate_of:")
            for record in indexed
        ),
        "withdrawn_count": state_counts["withdrawn"],
        "working_copy_count": sum(record["working_sha256"] is not None for record in indexed),
        "deidentification_pending_count": sum(
            record["deidentification_status"] == "pending" for record in indexed
        ),
        "direct_identifiers_written": False,
        "raw_images_copied": False,
        "training_executed": False,
        "splits_frozen": False,
    }
    _atomic_json(report_path, report)
    return IntakeOutputs(
        index_path=index_path,
        report_path=report_path,
        record_count=len(indexed),
        quarantined_count=state_counts["quarantined"],
    )


def deidentify_message_text(value: str) -> tuple[str, dict[str, int]]:
    """Tokenise high-risk values while preserving wording and spelling signals."""

    text = value.replace("\x00", " ").strip()
    counts: Counter[str] = Counter()
    for label, pattern in (
        ("URL_TOKEN", _URL),
        ("EMAIL_TOKEN", _EMAIL),
        ("PHONE_TOKEN", _PHONE),
        ("AMOUNT_TOKEN", _MONEY),
        ("REFERENCE_TOKEN", _LONG_REFERENCE),
    ):
        text, count = pattern.subn(label, text)
        counts[label] += count
    return text, dict(sorted(counts.items()))


def _sender_kind(value: str) -> str:
    compact = re.sub(r"[\s()+-]", "", value)
    if compact.isdigit() and 3 <= len(compact) <= 6:
        return "shortcode"
    if _PHONE.fullmatch(value.strip()) or (compact.isdigit() and len(compact) >= 9):
        return "phone_number"
    if value.strip() and any(character.isalpha() for character in value):
        return "alphanumeric_label"
    return "unknown"


def index_imazing_messages(
    *,
    source_csv: Path,
    index_path: Path,
    report_path: Path,
    participant_id_hash: str,
    permission_reference: str,
    repository_root: Path,
    text_column: str | None = None,
    sender_column: str | None = None,
) -> IntakeOutputs:
    """Index an owner-supplied iMazing CSV without retaining raw senders in output."""

    participant = _expect_sha256(participant_id_hash, "participant_id_hash")
    permission = _expect_opaque_id(permission_reference, "permission_reference")
    if not source_csv.is_file():
        raise GhanaPrivateError("iMazing CSV does not exist")
    _require_outside_repository(index_path, repository_root, "private message index")
    try:
        stream = source_csv.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise GhanaPrivateError("iMazing CSV could not be opened") from exc
    with stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        normalised = {header.strip().casefold(): header for header in headers}
        body_name = text_column or next(
            (
                normalised[name]
                for name in ("text", "message", "body", "content")
                if name in normalised
            ),
            None,
        )
        sender_name = sender_column or next(
            (
                normalised[name]
                for name in ("sender", "from", "contact", "address")
                if name in normalised
            ),
            None,
        )
        if body_name not in headers or sender_name not in headers:
            raise GhanaPrivateError("iMazing CSV requires identifiable message and sender columns")
        indexed: list[dict[str, object]] = []
        sender_counts: Counter[str] = Counter()
        token_counts: Counter[str] = Counter()
        source_hash = _sha256_file(source_csv)
        for row_number, row in enumerate(reader, start=2):
            raw_text = row.get(body_name, "")
            raw_sender = row.get(sender_name, "")
            if not raw_text or not raw_text.strip():
                continue
            candidate_text, replacements = deidentify_message_text(raw_text)
            kind = _sender_kind(raw_sender or "")
            sender_counts[kind] += 1
            token_counts.update(replacements)
            indexed.append(
                {
                    "message_id": "GHMSG_"
                    + _sha256_bytes(f"{source_hash}:{row_number}".encode())[:24].upper(),
                    "participant_id_hash": participant,
                    "permission_reference": permission,
                    "source_row_number": row_number,
                    "sender_kind": kind,
                    "candidate_transcript": candidate_text,
                    "workflow_state": "needs_deidentification",
                    "manual_identity_review_required": True,
                    "review_history": [],
                }
            )
    index = {
        "schema_version": MESSAGE_INDEX_VERSION,
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "source_sha256": source_hash,
        "records": indexed,
    }
    _atomic_json(index_path, index)
    report = {
        "schema_version": "ghana-message-intake-report-v1",
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "source_sha256": source_hash,
        "message_count": len(indexed),
        "sender_kind_counts": dict(sorted(sender_counts.items())),
        "replacement_counts": dict(sorted(token_counts.items())),
        "raw_sender_values_written": False,
        "manual_identity_review_required": True,
        "training_eligible": False,
        "training_executed": False,
    }
    _atomic_json(report_path, report)
    return IntakeOutputs(index_path, report_path, len(indexed), 0)


def quarantine_online_candidate(
    *,
    source_path: Path,
    source_page_url: str | None,
    quarantine_root: Path,
    index_path: Path,
    report_path: Path,
    repository_root: Path,
    reviewer_id: str,
) -> OnlineCandidateOutputs:
    """Admit one manually acquired web image to a rights-review-only private quarantine."""

    reviewer = _expect_opaque_id(reviewer_id, "reviewer_id")
    source_domain: str | None = None
    rights_state = "source_page_missing"
    status = "quarantined_missing_source_page"
    if source_page_url is not None:
        parsed = urlparse(source_page_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise GhanaPrivateError("online candidate requires a credential-free HTTPS source page")
        source_domain = parsed.hostname.casefold()
        rights_state = "unreviewed"
        status = "quarantined_pending_rights_review"
    _require_outside_repository(quarantine_root, repository_root, "online quarantine")
    _require_outside_repository(index_path, repository_root, "online candidate index")
    image = _decode_private_image(source_path)
    source_hash = _sha256_file(source_path)
    candidate_id = f"GHCAND_{source_hash[:24].upper()}"
    if index_path.exists():
        index = _load_object(index_path)
        if index.get("schema_version") != ONLINE_CANDIDATE_INDEX_VERSION:
            raise GhanaPrivateError("unsupported online candidate index")
        records = index.get("records")
        if not isinstance(records, list):
            raise GhanaPrivateError("online candidate records are invalid")
    else:
        records = []
        index = {
            "schema_version": ONLINE_CANDIDATE_INDEX_VERSION,
            "pipeline_version": GHANA_PIPELINE_VERSION,
            "records": records,
        }
    existing = next(
        (
            record
            for record in records
            if isinstance(record, dict) and record.get("source_sha256") == source_hash
        ),
        None,
    )
    if existing is not None:
        status = "duplicate_quarantined"
    else:
        quarantine_root.mkdir(parents=True, exist_ok=True)
        output_path = quarantine_root.resolve() / f"{candidate_id}.png"
        image.save(output_path, format="PNG", optimize=False)
        records.append(
            {
                "candidate_id": candidate_id,
                "source_sha256": source_hash,
                "quarantine_sha256": _sha256_file(output_path),
                "perceptual_dhash": _dhash(image),
                "source_page_url": source_page_url,
                "source_domain": source_domain,
                "source_page_state": "recorded" if source_page_url is not None else "missing",
                "reviewer_id": reviewer,
                "rights_state": rights_state,
                "content_state": "unreviewed",
                "deidentification_state": "not_started",
                "training_eligible": False,
                "status": status,
            }
        )
        _atomic_json(index_path, index)
    state_counts = Counter(
        str(record.get("status")) for record in records if isinstance(record, dict)
    )
    report = {
        "schema_version": "ghana-online-candidate-report-v1",
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "candidate_count": len(records),
        "status_counts": dict(sorted(state_counts.items())),
        "rights_review_complete_count": 0,
        "missing_source_page_count": sum(
            record.get("source_page_state") == "missing"
            or ("source_page_state" not in record and record.get("source_page_url") is None)
            for record in records
            if isinstance(record, dict)
        ),
        "training_eligible_count": 0,
        "network_acquisition_executed": False,
        "automated_scraping_executed": False,
        "training_executed": False,
    }
    _atomic_json(report_path, report)
    return OnlineCandidateOutputs(candidate_id, status, index_path, report_path)


def attest_online_candidate_permission(
    *,
    index_path: Path,
    report_path: Path,
    candidate_id: str,
    permission_reference: str,
    reviewer_id: str,
    permission_scope: str,
) -> None:
    """Record project-owner permission attestation without bypassing later ML gates."""

    reviewer = _expect_opaque_id(reviewer_id, "reviewer_id")
    permission = _expect_opaque_id(permission_reference, "permission_reference")
    if permission_scope != "internal_model_development":
        raise GhanaPrivateError("online candidate permission scope is invalid")
    index = _load_object(index_path)
    records = index.get("records")
    if not isinstance(records, list):
        raise GhanaPrivateError("online candidate records are invalid")
    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("candidate_id") == candidate_id
    ]
    if len(matches) != 1:
        raise GhanaPrivateError("online candidate was not found uniquely")
    record = matches[0]
    record["rights_state"] = "project_owner_attested_permission"
    record["permission_reference"] = permission
    record["permission_scope"] = permission_scope
    record["rights_reviewer_id"] = reviewer
    record["training_eligible"] = False
    _atomic_json(index_path, index)
    report = {
        "schema_version": "ghana-online-candidate-report-v1",
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "candidate_count": len(records),
        "owner_attested_permission_count": sum(
            item.get("rights_state") == "project_owner_attested_permission"
            for item in records
            if isinstance(item, dict)
        ),
        "missing_source_page_count": sum(
            item.get("source_page_state") == "missing"
            or ("source_page_state" not in item and item.get("source_page_url") is None)
            for item in records
            if isinstance(item, dict)
        ),
        "training_eligible_count": 0,
        "network_acquisition_executed": False,
        "automated_scraping_executed": False,
        "training_executed": False,
    }
    _atomic_json(report_path, report)


def review_online_candidate(
    *,
    index_path: Path,
    report_path: Path,
    candidate_id: str,
    content_class: str,
    direct_identifier_state: str,
    reviewer_id: str,
) -> None:
    """Record content triage without granting rights or training eligibility."""

    reviewer = _expect_opaque_id(reviewer_id, "reviewer_id")
    if content_class not in {
        "primary_ghana_momo_fraud",
        "adjacent_financial_phishing",
        "awareness_composite",
        "ambiguous_requires_adjudication",
        "mixed_authenticity_thread",
        "not_relevant",
    }:
        raise GhanaPrivateError("online candidate content class is invalid")
    if direct_identifier_state not in {"present", "none_visible", "uncertain"}:
        raise GhanaPrivateError("online candidate identifier state is invalid")
    index = _load_object(index_path)
    records = index.get("records")
    if not isinstance(records, list):
        raise GhanaPrivateError("online candidate records are invalid")
    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("candidate_id") == candidate_id
    ]
    if len(matches) != 1:
        raise GhanaPrivateError("online candidate was not found uniquely")
    record = matches[0]
    record["content_state"] = content_class
    record["direct_identifier_state"] = direct_identifier_state
    record["content_reviewer_id"] = reviewer
    record["deidentification_state"] = (
        "required" if direct_identifier_state != "none_visible" else "manual_review_required"
    )
    record["training_eligible"] = False
    _atomic_json(index_path, index)
    content_counts = Counter(
        str(item.get("content_state")) for item in records if isinstance(item, dict)
    )
    report = {
        "schema_version": "ghana-online-candidate-report-v1",
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "candidate_count": len(records),
        "content_state_counts": dict(sorted(content_counts.items())),
        "rights_review_complete_count": sum(
            item.get("rights_state") in {"permission_confirmed", "licence_confirmed"}
            for item in records
            if isinstance(item, dict)
        ),
        "missing_source_page_count": sum(
            item.get("source_page_state") == "missing"
            or ("source_page_state" not in item and item.get("source_page_url") is None)
            for item in records
            if isinstance(item, dict)
        ),
        "owner_attested_permission_count": sum(
            item.get("rights_state") == "project_owner_attested_permission"
            for item in records
            if isinstance(item, dict)
        ),
        "training_eligible_count": 0,
        "network_acquisition_executed": False,
        "automated_scraping_executed": False,
        "training_executed": False,
    }
    _atomic_json(report_path, report)


def advance_review(
    *,
    index_path: Path,
    image_id: str,
    expected_state: str,
    next_state: str,
    reviewer_id: str,
    reason_code: str,
) -> None:
    """Apply one auditable, fail-closed workflow transition to a private record."""

    reviewer = _expect_opaque_id(reviewer_id, "reviewer_id")
    reason = _expect_opaque_id(reason_code, "reason_code")
    if expected_state not in WORKFLOW_STATES or next_state not in WORKFLOW_STATES:
        raise GhanaPrivateError("unknown private review state")
    if next_state not in TRANSITIONS[expected_state]:
        raise GhanaPrivateError("private review transition is not allowed")
    index = _load_object(index_path)
    records = index.get("records")
    if not isinstance(records, list):
        raise GhanaPrivateError("private index records are invalid")
    matches = [
        record
        for record in records
        if isinstance(record, dict) and record.get("image_id") == image_id
    ]
    if len(matches) != 1:
        raise GhanaPrivateError("private image record was not found uniquely")
    record = matches[0]
    if record.get("workflow_state") != expected_state:
        raise GhanaPrivateError("private review state changed before transition")
    history = record.get("review_history")
    if not isinstance(history, list):
        raise GhanaPrivateError("private review history is invalid")
    if next_state in APPROVED_STATES and not history:
        raise GhanaPrivateError("approval requires prior independent review history")
    history.append(
        {
            "from": expected_state,
            "to": next_state,
            "reviewer_id": reviewer,
            "reason_code": reason,
        }
    )
    record["workflow_state"] = next_state
    _atomic_json(index_path, index)


def _group_key(record: Mapping[str, object]) -> str:
    if record.get("provenance") == "controlled_real":
        return _expect_sha256(record.get("participant_id_hash"), "participant_id_hash")
    return _expect_opaque_id(record.get("source_group_id"), "source_group_id")


def _quota(total: int, ratios: Sequence[float]) -> tuple[int, ...]:
    raw = [total * ratio for ratio in ratios]
    quotas = [int(value) for value in raw]
    remaining = total - sum(quotas)
    order = sorted(range(len(ratios)), key=lambda item: (-(raw[item] - quotas[item]), item))
    for position in order[:remaining]:
        quotas[position] += 1
    return tuple(quotas)


def freeze_group_splits(
    *, index_path: Path, manifest_path: Path, report_path: Path, seed: int = 20260813
) -> SplitOutputs:
    """Freeze approved records by participant/source group before later preprocessing."""

    index = _load_object(index_path)
    records = index.get("records")
    if not isinstance(records, list):
        raise GhanaPrivateError("private index records are invalid")
    approved = [
        record
        for record in records
        if isinstance(record, dict) and record.get("workflow_state") in APPROVED_STATES
    ]
    if not approved:
        raise GhanaPrivateError("no approved private records are available for splitting")
    group_records: dict[str, list[dict[str, object]]] = {}
    for record in approved:
        if record.get("working_sha256") is None:
            raise GhanaPrivateError("approved record is missing a de-identified working image")
        group_records.setdefault(_group_key(record), []).append(record)
    controlled_groups = sorted(
        (
            key
            for key, value in group_records.items()
            if value[0].get("provenance") == "controlled_real"
        ),
        key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest(),
    )
    synthetic_groups = sorted(
        (
            key
            for key, value in group_records.items()
            if value[0].get("provenance") != "controlled_real"
        ),
        key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest(),
    )
    assignments: dict[str, str] = {}
    for groups, ratios in (
        (controlled_groups, (0.70, 0.15, 0.15)),
        (synthetic_groups, (0.80, 0.20, 0.0)),
    ):
        train_count, validation_count, _ = _quota(len(groups), ratios)
        for position, group in enumerate(groups):
            assignments[group] = (
                "train"
                if position < train_count
                else "validation"
                if position < train_count + validation_count
                else "test"
            )
    manifest_records = [
        {
            "image_id": record["image_id"],
            "source_group_id": record["source_group_id"],
            "participant_id_hash": record["participant_id_hash"],
            "provenance": record["provenance"],
            "working_relative_path": record["working_relative_path"],
            "working_sha256": record["working_sha256"],
            "split": assignments[_group_key(record)],
            "consent_scope": record["consent_scope"],
        }
        for record in approved
    ]
    manifest = {
        "schema_version": FROZEN_SPLIT_VERSION,
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "seed": seed,
        "locked_test": True,
        "records": sorted(manifest_records, key=lambda record: str(record["image_id"])),
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest_hash = _sha256_bytes(canonical)
    manifest["manifest_sha256"] = manifest_hash
    _atomic_json(manifest_path, manifest)
    split_counts = Counter(str(record["split"]) for record in manifest_records)
    report = {
        "schema_version": "ghana-private-split-report-v1",
        "manifest_sha256": manifest_hash,
        "record_count": len(manifest_records),
        "group_count": len(group_records),
        "split_counts": dict(sorted(split_counts.items())),
        "group_intersections": {"train_validation": [], "train_test": [], "validation_test": []},
        "locked_test": True,
        "training_executed": False,
    }
    _atomic_json(report_path, report)
    return SplitOutputs(manifest_path, report_path, manifest_hash)


def load_development_records(manifest_path: Path) -> tuple[dict[str, object], ...]:
    """Load train/validation only; the PR16 training loader cannot expose locked test rows."""

    manifest = _load_object(manifest_path)
    if (
        manifest.get("schema_version") != FROZEN_SPLIT_VERSION
        or manifest.get("locked_test") is not True
    ):
        raise GhanaPrivateError("Ghana split manifest is not a locked PR16 manifest")
    records = manifest.get("records")
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise GhanaPrivateError("Ghana split records are invalid")
    return tuple(record for record in records if record.get("split") in {"train", "validation"})


def apply_withdrawals(
    *,
    index_path: Path,
    withdrawn_participants: frozenset[str],
    working_root: Path,
    quarantine_root: Path,
    receipt_path: Path,
) -> int:
    """Quarantine indexed derivatives and produce a private deletion-propagation receipt."""

    index = _load_object(index_path)
    records = index.get("records")
    if not isinstance(records, list):
        raise GhanaPrivateError("private index records are invalid")
    affected: list[str] = []
    quarantine_root.mkdir(parents=True, exist_ok=True)
    for record in records:
        if (
            not isinstance(record, dict)
            or record.get("participant_id_hash") not in withdrawn_participants
        ):
            continue
        image_id = str(record.get("image_id"))
        relative = record.get("working_relative_path")
        if isinstance(relative, str):
            source = (working_root.resolve() / relative).resolve()
            if not source.is_relative_to(working_root.resolve()):
                raise GhanaPrivateError("indexed working path escapes the approved root")
            if source.exists():
                destination = quarantine_root.resolve() / f"{image_id}.png"
                shutil.move(str(source), str(destination))
        record["working_relative_path"] = None
        record["working_sha256"] = None
        record["workflow_state"] = "withdrawn"
        record["quarantine_reason"] = "participant_withdrawn"
        affected.append(image_id)
    _atomic_json(index_path, index)
    receipt = {
        "schema_version": WITHDRAWAL_RECEIPT_VERSION,
        "affected_record_count": len(affected),
        "affected_image_ids": sorted(affected),
        "derivatives_quarantined": True,
        "split_rebuild_required": bool(affected),
        "dependent_artifacts_invalidated": bool(affected),
    }
    _atomic_json(receipt_path, receipt)
    return len(affected)


def create_controlled_edit(
    *,
    source_path: Path,
    output_path: Path,
    mask_path: Path,
    target: str,
    method: str,
    bbox: tuple[int, int, int, int],
    replacement_token: str,
    edit_id: str,
    source_image_id: str,
    derived_image_id: str,
) -> dict[str, object]:
    """Generate one deterministic, mask-aligned fictitious controlled edit."""

    if target not in {"amount", "recipient", "reference", "datetime", "status", "header"}:
        raise GhanaPrivateError("controlled edit target is invalid")
    if method not in {
        "replacement",
        "splicing",
        "removal_insertion",
        "copy_move",
        "inpainting",
        "composite",
    }:
        raise GhanaPrivateError("controlled edit method is invalid")
    _expect_opaque_id(edit_id, "edit_id")
    _expect_opaque_id(source_image_id, "source_image_id")
    _expect_opaque_id(derived_image_id, "derived_image_id")
    if not replacement_token.startswith("SYNTHETIC_"):
        raise GhanaPrivateError("controlled edits must use an explicit synthetic token")
    image = _decode_private_image(source_path)
    x, y, width, height = _regions([list(bbox)], width=image.width, height=image.height)[0]
    edited = image.copy()
    replacement = Image.new("RGB", (width, height), (255, 255, 255))
    ImageDraw.Draw(replacement).text((2, 2), replacement_token, fill=(0, 0, 0))
    edited.paste(replacement, (x, y))
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rectangle((x, y, x + width - 1, y + height - 1), fill=255)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    edited.save(output_path, format="PNG", optimize=False)
    mask.save(mask_path, format="PNG", optimize=False)
    return {
        "schema_version": EDIT_MANIFEST_VERSION,
        "edit_id": edit_id,
        "source_image_id": source_image_id,
        "derived_image_id": derived_image_id,
        "source_sha256": _sha256_file(source_path),
        "output_sha256": _sha256_file(output_path),
        "mask_sha256": _sha256_file(mask_path),
        "target": target,
        "method": method,
        "replacement_token": replacement_token,
        "bbox": list(bbox),
        "generator_version": GHANA_PIPELINE_VERSION,
        "review_state": "needs_mask_review",
    }


def changed_pixels_are_masked(source_path: Path, edited_path: Path, mask_path: Path) -> bool:
    """Prove every changed pixel is covered by a non-empty binary edit mask."""

    source = _decode_private_image(source_path)
    edited = _decode_private_image(edited_path)
    try:
        with Image.open(mask_path) as opened:
            mask = opened.convert("L")
    except (OSError, UnidentifiedImageError) as exc:
        raise GhanaPrivateError("controlled edit mask cannot be decoded") from exc
    if source.size != edited.size or source.size != mask.size:
        raise GhanaPrivateError("controlled edit and mask dimensions must match")
    source_pixels = list(source.get_flattened_data())
    edited_pixels = list(edited.get_flattened_data())
    mask_pixels = list(mask.get_flattened_data())
    changed = [
        index
        for index, pair in enumerate(zip(source_pixels, edited_pixels, strict=True))
        if pair[0] != pair[1]
    ]
    return bool(changed) and all(mask_pixels[index] == 255 for index in changed)


def safe_intake_summary(outputs: Iterable[IntakeOutputs]) -> dict[str, object]:
    """Combine safe run counts without opening private indexes."""

    values = tuple(outputs)
    return {
        "schema_version": "ghana-private-pilot-summary-v1",
        "pipeline_version": GHANA_PIPELINE_VERSION,
        "run_count": len(values),
        "record_count": sum(value.record_count for value in values),
        "quarantined_count": sum(value.quarantined_count for value in values),
        "private_bytes_in_git": False,
        "training_executed": False,
    }
