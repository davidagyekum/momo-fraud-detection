"""Governed metadata and image checks for the Ghana MoMo fraud corpus.

This module deliberately treats the Ghana fraud-message corpus as a separate
dataset profile from the P12 controlled-tamper fixtures.  It validates local
redacted working copies, while the canonical repository manifest continues to
refer to authorised real data through private object IDs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Final

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from momo_fdvs_ml.manifest import (
    ManifestRecord,
    scan_text_for_private_identifiers,
    write_manifest,
)

GHANA_DATASET_VERSION: Final = "ghana-mobile-money-fraud-message-v1"
GHANA_MANIFEST_SCHEMA_VERSION: Final = "ghana-momo-fraud-manifest-v1"
GHANA_SAMPLE_PATTERN: Final = re.compile(r"GHMM_[0-9]{6}")
GHANA_SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")
IMAGE_SUFFIXES: Final = {".jpg", ".jpeg", ".png", ".webp"}
MODEL_SPLITS: Final = {"train", "validation", "test"}
ALL_SPLITS: Final = MODEL_SPLITS | {"review"}
LABELS: Final = {"fraudulent", "genuine", "suspicious"}
PROVIDER_CODES: Final = {
    "MTN_MOMO",
    "TELECEL_CASH",
    "ATMONEY",
    "GENERIC_MOMO",
    "MULTI_PROVIDER",
    "UNKNOWN",
}
GHANA_EVIDENCE_LEVELS: Final = {"strong", "moderate", "weak"}
PII_STATUSES: Final = {"none_visible", "redacted", "requires_redaction"}
RIGHTS_STATUSES: Final = {
    "consented",
    "licensed",
    "official_publication",
    "research_restricted",
    "unknown_do_not_release",
}
RELEASE_RIGHTS: Final = {"consented", "licensed", "official_publication"}
RELEASE_PII: Final = {"none_visible", "redacted"}

LABEL_COLUMNS: Final = (
    "sample_id",
    "local_relative_path",
    "source_group_id",
    "source_type",
    "fraud_label",
    "provider_code",
    "provider_alias",
    "scam_subtype",
    "social_vector",
    "impersonation_target",
    "urgency_cues",
    "persuasion_cues",
    "requested_action",
    "language_primary",
    "language_secondary",
    "media_type",
    "quality",
    "ghana_evidence",
    "geo_evidence_note",
    "pii_status",
    "redaction_version",
    "ocr_text_redacted",
    "ocr_fingerprint",
    "sha256",
    "phash",
    "campaign_group_id",
    "source_platform",
    "source_account_type",
    "source_url",
    "source_post_id",
    "source_date",
    "collected_at",
    "rights_status",
    "consent_or_licence_reference",
    "original_contains_personal_data",
    "release_eligible",
    "annotator_a",
    "annotator_b",
    "adjudicated_by",
    "label_confidence",
    "split",
    "notes",
)

PRIVATE_PROVENANCE_COLUMNS: Final = (
    "sample_id",
    "source_url",
    "source_post_id",
    "source_account_name",
    "source_account_type",
    "source_date",
    "collected_at",
    "rights_status",
    "consent_or_licence_reference",
    "takedown_contact",
    "original_object_id",
    "original_contains_personal_data",
    "retention_review_date",
    "notes",
)

SOURCE_REGISTRY_COLUMNS: Final = (
    "source_id",
    "source_family",
    "organisation",
    "provider_scope",
    "source_platform",
    "source_url",
    "access_method",
    "status",
    "rights_status",
    "ghana_evidence",
    "image_training_candidate",
    "reviewed_at",
    "notes",
)


class GhanaDatasetError(ValueError):
    """Raised when the Ghana corpus cannot be processed safely."""


@dataclass(frozen=True)
class GhanaDatasetIssue:
    """One machine-readable finding from the corpus validator."""

    severity: str
    code: str
    message: str
    sample_id: str | None = None


@dataclass(frozen=True)
class GhanaDatasetReport:
    """Stable validation output for the local redacted corpus."""

    dataset_version: str
    manifest_schema_version: str
    status: str
    row_count: int
    ready_count: int
    group_count: int
    split_counts: Mapping[str, int]
    label_counts: Mapping[str, int]
    provider_counts: Mapping[str, int]
    platform_counts: Mapping[str, int]
    rights_counts: Mapping[str, int]
    manifest_hash: str
    split_hash: str
    issues: tuple[GhanaDatasetIssue, ...]

    @property
    def errors(self) -> tuple[GhanaDatasetIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[GhanaDatasetIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    def as_dict(self) -> dict[str, object]:
        return {
            "dataset_version": self.dataset_version,
            "manifest_schema_version": self.manifest_schema_version,
            "status": self.status,
            "row_count": self.row_count,
            "ready_count": self.ready_count,
            "group_count": self.group_count,
            "split_counts": dict(sorted(self.split_counts.items())),
            "label_counts": dict(sorted(self.label_counts.items())),
            "provider_counts": dict(sorted(self.provider_counts.items())),
            "platform_counts": dict(sorted(self.platform_counts.items())),
            "rights_counts": dict(sorted(self.rights_counts.items())),
            "manifest_hash": self.manifest_hash,
            "split_hash": self.split_hash,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "training_executed": False,
            "model_metrics": None,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _add_issue(
    issues: list[GhanaDatasetIssue],
    code: str,
    message: str,
    sample_id: str | None = None,
    *,
    severity: str = "error",
) -> None:
    issues.append(GhanaDatasetIssue(severity, code, message, sample_id))


def _read_csv(path: Path, required_columns: Iterable[str]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise GhanaDatasetError(f"CSV has no header: {path}")
            fields = [field.strip() for field in reader.fieldnames]
            if len(fields) != len(set(fields)):
                raise GhanaDatasetError(f"CSV has duplicate columns: {path}")
            missing = sorted(set(required_columns) - set(fields))
            if missing:
                raise GhanaDatasetError(f"CSV is missing columns: {', '.join(missing)}")
            return [
                {key: (value or "").strip() for key, value in row.items() if key is not None}
                for row in reader
            ]
    except UnicodeDecodeError as exc:
        raise GhanaDatasetError(f"CSV must be UTF-8: {path}") from exc
    except OSError as exc:
        raise GhanaDatasetError(f"Unable to read CSV: {path}") from exc


def load_label_rows(root: Path) -> list[dict[str, str]]:
    """Load adjudicated image rows from the local private workspace."""

    return _read_csv(root / "metadata" / "labels_adjudicated.csv", LABEL_COLUMNS)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalise_ocr_text(text: str) -> str:
    """Normalise already-redacted OCR text for stable campaign fingerprints."""

    value = unicodedata.normalize("NFKC", text).lower()
    value = re.sub(r"https?://\S+|www\.\S+", " url ", value)
    value = re.sub(r"\b(?:\+?233|0)[235]\d{8}\b", " phone ", value)
    value = re.sub(r"\b\d{4,}\b", " number ", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def ocr_fingerprint(text: str) -> str:
    normalised = normalise_ocr_text(text)
    return _canonical_hash({"ocr_schema": "redacted-ocr-v1", "text": normalised})


def _safe_path(root: Path, relative_path: str) -> Path | None:
    pure = PurePosixPath(relative_path.replace("\\", "/"))
    if not relative_path or pure.is_absolute() or ".." in pure.parts:
        return None
    if not pure.parts or pure.parts[0] != "images":
        return None
    candidate = (root / Path(*pure.parts)).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        return None
    return candidate


def _phash_from_image(image: Image.Image) -> str:
    resized = image.convert("L").resize((32, 32), Image.Resampling.BILINEAR)
    pixels = [float(value) for value in resized.tobytes()]
    coefficients: list[float] = []
    for u in range(8):
        for v in range(8):
            if u == 0 and v == 0:
                continue
            total = 0.0
            for x in range(32):
                for y in range(32):
                    total += (
                        pixels[x * 32 + y]
                        * math.cos(math.pi * (2 * x + 1) * u / 64)
                        * math.cos(math.pi * (2 * y + 1) * v / 64)
                    )
            coefficients.append(total)
    median = sorted(coefficients)[len(coefficients) // 2]
    bits = "".join("1" if coefficient > median else "0" for coefficient in coefficients)
    return f"{int(bits, 2):016x}"


def phash_file(path: Path) -> str:
    try:
        with Image.open(path) as source:
            source.load()
            return _phash_from_image(ImageOps.exif_transpose(source))
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise GhanaDatasetError(f"Unable to calculate perceptual hash: {path}") from exc


def phash_hamming(left: str, right: str) -> int:
    if not re.fullmatch(r"[0-9a-fA-F]{16}", left) or not re.fullmatch(r"[0-9a-fA-F]{16}", right):
        raise GhanaDatasetError("pHash values must contain exactly 16 hexadecimal characters")
    return (int(left, 16) ^ int(right, 16)).bit_count()


def _parse_bool(value: str, field: str, sample_id: str) -> bool:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise GhanaDatasetError(f"{sample_id}: {field} must be true or false")


def _validate_image(path: Path, sample_id: str, issues: list[GhanaDatasetIssue]) -> str | None:
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        _add_issue(issues, "unsupported_image_type", "image extension is not allowed", sample_id)
        return None
    if not path.is_file():
        _add_issue(issues, "missing_image", "redacted image is missing", sample_id)
        return None
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            width, height = image.size
            if width < 128 or height < 128:
                _add_issue(
                    issues, "image_too_small", "image must be at least 128 by 128", sample_id
                )
            if image.getexif():
                _add_issue(
                    issues, "exif_present", "released image must have EXIF removed", sample_id
                )
            return sha256_file(path)
    except (OSError, UnidentifiedImageError) as exc:
        _add_issue(issues, "corrupt_image", f"image cannot be decoded: {exc}", sample_id)
        return None


def _row_hash(rows: Sequence[Mapping[str, str]]) -> str:
    canonical = [{key: row.get(key, "") for key in LABEL_COLUMNS} for row in rows]
    return _canonical_hash({"schema": GHANA_MANIFEST_SCHEMA_VERSION, "rows": canonical})


def _split_hash(rows: Sequence[Mapping[str, str]]) -> str:
    mapping = sorted({(row.get("source_group_id", ""), row.get("split", "")) for row in rows})
    return _canonical_hash({"schema": GHANA_MANIFEST_SCHEMA_VERSION, "groups": mapping})


def validate_dataset(
    root: Path,
    *,
    minimum_ready: int = 0,
    require_ready: bool = False,
) -> GhanaDatasetReport:
    """Validate redacted images, provenance, rights, privacy and split isolation."""

    issues: list[GhanaDatasetIssue] = []
    manifest_path = root / "metadata" / "labels_adjudicated.csv"
    if not manifest_path.is_file():
        _add_issue(issues, "missing_manifest", f"missing {manifest_path}")
        return GhanaDatasetReport(
            GHANA_DATASET_VERSION,
            GHANA_MANIFEST_SCHEMA_VERSION,
            "NOT_READY",
            0,
            0,
            0,
            {},
            {},
            {},
            {},
            {},
            "",
            "",
            tuple(issues),
        )

    try:
        rows = load_label_rows(root)
    except GhanaDatasetError as exc:
        _add_issue(issues, "manifest_parse_error", str(exc))
        return GhanaDatasetReport(
            GHANA_DATASET_VERSION,
            GHANA_MANIFEST_SCHEMA_VERSION,
            "NOT_READY",
            0,
            0,
            0,
            {},
            {},
            {},
            {},
            {},
            "",
            "",
            tuple(issues),
        )

    seen_ids: set[str] = set()
    hashes: dict[str, list[str]] = defaultdict(list)
    phash_records: list[tuple[str, str, str, str]] = []
    group_splits: dict[str, set[str]] = defaultdict(set)
    split_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    platform_counts: Counter[str] = Counter()
    rights_counts: Counter[str] = Counter()
    ready_count = 0

    for row in rows:
        sample_id = row.get("sample_id", "")
        fraud_label = row.get("fraud_label", "")
        split = row.get("split", "")
        release_eligible = False
        try:
            release_eligible = _parse_bool(
                row.get("release_eligible", ""), "release_eligible", sample_id
            )
            original_pii = _parse_bool(
                row.get("original_contains_personal_data", ""),
                "original_contains_personal_data",
                sample_id,
            )
        except GhanaDatasetError as exc:
            _add_issue(issues, "invalid_boolean", str(exc), sample_id)
            original_pii = False

        if not GHANA_SAMPLE_PATTERN.fullmatch(sample_id):
            _add_issue(issues, "invalid_sample_id", "sample ID must match GHMM_000000", sample_id)
        if sample_id in seen_ids:
            _add_issue(issues, "duplicate_sample_id", "sample ID is repeated", sample_id)
        seen_ids.add(sample_id)
        if not row.get("source_group_id"):
            _add_issue(issues, "missing_source_group", "source_group_id is required", sample_id)
        if row.get("source_type") != "real_authorised":
            _add_issue(
                issues, "invalid_source_type", "source_type must be real_authorised", sample_id
            )
        if fraud_label not in LABELS:
            _add_issue(issues, "invalid_label", "fraud_label is not supported", sample_id)
        if split not in ALL_SPLITS:
            _add_issue(
                issues,
                "invalid_split",
                "split must be train, validation, test or review",
                sample_id,
            )
        if fraud_label == "suspicious" and split != "review":
            _add_issue(
                issues,
                "suspicious_not_review",
                "suspicious samples must use the review split",
                sample_id,
            )
        if fraud_label in {"fraudulent", "genuine"} and split == "review":
            _add_issue(
                issues,
                "label_not_model_split",
                "fraudulent/genuine samples need a model split",
                sample_id,
            )
        if row.get("provider_code") not in PROVIDER_CODES:
            _add_issue(issues, "invalid_provider", "provider_code is not supported", sample_id)
        if row.get("ghana_evidence") not in GHANA_EVIDENCE_LEVELS:
            _add_issue(
                issues, "invalid_ghana_evidence", "ghana_evidence is not supported", sample_id
            )
        if row.get("pii_status") not in PII_STATUSES:
            _add_issue(issues, "invalid_pii_status", "pii_status is not supported", sample_id)
        if row.get("rights_status") not in RIGHTS_STATUSES:
            _add_issue(issues, "invalid_rights_status", "rights_status is not supported", sample_id)
        if not row.get("source_url"):
            _add_issue(issues, "missing_source_url", "source_url is required", sample_id)
        if not row.get("source_platform") or not row.get("source_account_type"):
            _add_issue(
                issues,
                "missing_source_context",
                "source platform and account type are required",
                sample_id,
            )
        if not row.get("collected_at"):
            _add_issue(issues, "missing_collection_time", "collected_at is required", sample_id)
        if not row.get("consent_or_licence_reference"):
            _add_issue(
                issues, "missing_permission", "consent/licence reference is required", sample_id
            )
        if original_pii and row.get("pii_status") != "redacted":
            _add_issue(
                issues,
                "original_pii_not_redacted",
                "original personal data requires redaction",
                sample_id,
            )
        if row.get("ocr_text_redacted") and scan_text_for_private_identifiers(
            row["ocr_text_redacted"]
        ):
            _add_issue(
                issues,
                "private_text_remaining",
                "redacted OCR text still contains private identifiers",
                sample_id,
            )
        if row.get("ocr_text_redacted") and row.get("ocr_fingerprint") != ocr_fingerprint(
            row["ocr_text_redacted"]
        ):
            _add_issue(
                issues,
                "ocr_fingerprint_mismatch",
                "ocr_fingerprint does not match redacted OCR text",
                sample_id,
            )

        local_path = _safe_path(root, row.get("local_relative_path", ""))
        if local_path is None:
            _add_issue(
                issues,
                "unsafe_local_path",
                "local_relative_path must stay under images/",
                sample_id,
            )
        else:
            if Path(row.get("local_relative_path", "")).stem != sample_id:
                _add_issue(
                    issues,
                    "filename_id_mismatch",
                    "image filename must use the opaque sample ID",
                    sample_id,
                )
            path_parts = PurePosixPath(row.get("local_relative_path", "").replace("\\", "/")).parts
            if split in ALL_SPLITS and (len(path_parts) != 3 or path_parts[1] != split):
                _add_issue(
                    issues,
                    "image_split_path_mismatch",
                    "image must be stored under images/<split>/",
                    sample_id,
                )
            actual_hash = _validate_image(local_path, sample_id, issues)
            if actual_hash is not None:
                hashes[actual_hash].append(sample_id)
                recorded_hash = row.get("sha256", "")
                if not GHANA_SHA256_PATTERN.fullmatch(recorded_hash):
                    _add_issue(
                        issues,
                        "invalid_sha256",
                        "sha256 must be 64 lowercase hexadecimal characters",
                        sample_id,
                    )
                elif recorded_hash != actual_hash:
                    _add_issue(
                        issues,
                        "hash_mismatch",
                        "recorded sha256 does not match image bytes",
                        sample_id,
                    )
                actual_phash = phash_file(local_path)
                recorded_phash = row.get("phash", "")
                if not recorded_phash:
                    _add_issue(
                        issues,
                        "missing_phash",
                        "phash is required for near-duplicate checks",
                        sample_id,
                    )
                elif not re.fullmatch(r"[0-9a-fA-F]{16}", recorded_phash):
                    _add_issue(
                        issues,
                        "invalid_phash",
                        "phash must contain exactly 16 hexadecimal characters",
                        sample_id,
                    )
                elif recorded_phash != actual_phash:
                    _add_issue(
                        issues,
                        "phash_mismatch",
                        "recorded phash does not match image bytes",
                        sample_id,
                    )
                else:
                    phash_records.append(
                        (sample_id, row.get("source_group_id", ""), split, recorded_phash)
                    )

        if release_eligible:
            if row.get("rights_status") not in RELEASE_RIGHTS:
                _add_issue(
                    issues,
                    "rights_not_releaseable",
                    "release-eligible row has non-releaseable rights",
                    sample_id,
                )
            if row.get("pii_status") not in RELEASE_PII:
                _add_issue(
                    issues,
                    "pii_not_releaseable",
                    "release-eligible row needs completed PII review",
                    sample_id,
                )
            if row.get("ghana_evidence") not in {"strong", "moderate"}:
                _add_issue(
                    issues,
                    "ghana_evidence_too_weak",
                    "release-eligible row needs strong or moderate Ghana evidence",
                    sample_id,
                )
            if not row.get("redaction_version"):
                _add_issue(
                    issues,
                    "missing_redaction_version",
                    "release-eligible row needs a redaction version",
                    sample_id,
                )
            if fraud_label not in {"fraudulent", "genuine"} or split not in MODEL_SPLITS:
                _add_issue(
                    issues,
                    "invalid_ready_label",
                    "only fraud/genuine model-split rows can be release eligible",
                    sample_id,
                )
            else:
                ready_count += 1
        elif split in MODEL_SPLITS:
            _add_issue(
                issues,
                "unapproved_model_row",
                "non-releaseable rows must stay in review",
                sample_id,
            )

        if row.get("source_group_id"):
            group_splits[row["source_group_id"]].add(split)
        split_counts[split] += 1
        label_counts[fraud_label] += 1
        provider_counts[row.get("provider_code", "")] += 1
        platform_counts[row.get("source_platform", "")] += 1
        rights_counts[row.get("rights_status", "")] += 1

    for digest, sample_ids in hashes.items():
        if len(sample_ids) > 1:
            for sample_id in sample_ids:
                _add_issue(
                    issues, "duplicate_sha256", f"exact duplicate image hash {digest}", sample_id
                )
    for group_id, splits in group_splits.items():
        if len(splits) > 1:
            _add_issue(issues, "source_group_leakage", f"source group crosses splits: {group_id}")
    for index, (left_id, left_group, left_split, left_phash) in enumerate(phash_records):
        for right_id, right_group, right_split, right_phash in phash_records[index + 1 :]:
            if left_id == right_id or phash_hamming(left_phash, right_phash) > 8:
                continue
            if left_split != right_split:
                _add_issue(
                    issues,
                    "near_duplicate_split_leakage",
                    f"near-duplicate pHash pair crosses {left_split}/{right_split}",
                    left_id,
                )
                _add_issue(
                    issues,
                    "near_duplicate_split_leakage",
                    f"near-duplicate pHash pair crosses {left_split}/{right_split}",
                    right_id,
                )
            elif left_group != right_group:
                _add_issue(
                    issues,
                    "near_duplicate_candidate",
                    f"review near-duplicate pHash {left_phash} against {right_id}",
                    left_id,
                    severity="warning",
                )

    if ready_count < 500:
        _add_issue(
            issues,
            "target_not_reached",
            f"{ready_count} eligible images; target is 500-600",
            severity="warning",
        )
    if ready_count > 600:
        _add_issue(
            issues,
            "target_exceeded",
            f"{ready_count} eligible images; target is 500-600",
            severity="warning",
        )
    core_count = label_counts["fraudulent"] + label_counts["genuine"]
    if core_count:
        fraud_ratio = label_counts["fraudulent"] / core_count
        if not 0.60 <= fraud_ratio <= 0.70:
            _add_issue(
                issues,
                "class_balance_warning",
                f"fraud ratio is {fraud_ratio:.3f}; target is 0.60-0.70",
                severity="warning",
            )
    if require_ready and ready_count < minimum_ready:
        _add_issue(
            issues,
            "minimum_ready_not_met",
            f"{ready_count} ready images is below required {minimum_ready}",
        )

    status = (
        "PASS"
        if ready_count > 0
        and ready_count >= minimum_ready
        and not any(issue.severity == "error" for issue in issues)
        else "NOT_READY"
    )
    return GhanaDatasetReport(
        GHANA_DATASET_VERSION,
        GHANA_MANIFEST_SCHEMA_VERSION,
        status,
        len(rows),
        ready_count,
        len(group_splits),
        split_counts,
        label_counts,
        provider_counts,
        platform_counts,
        rights_counts,
        _row_hash(rows),
        _split_hash(rows),
        tuple(issues),
    )


def write_report(report: GhanaDatasetReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_canonical_manifest(root: Path, output: Path) -> Path:
    """Project eligible redacted rows into the repository's real-data manifest."""

    report = validate_dataset(root, require_ready=True, minimum_ready=1)
    if report.errors or report.ready_count == 0:
        raise GhanaDatasetError(
            "cannot build canonical manifest before the corpus passes validation"
        )
    rows = [
        row
        for row in load_label_rows(root)
        if row.get("release_eligible", "").lower() == "true"
        and row.get("fraud_label") in {"fraudulent", "genuine"}
        and row.get("split") in MODEL_SPLITS
    ]
    records: list[ManifestRecord] = []
    for row in rows:
        object_id = f"ghana-momo-fraud/object-{row['sha256'][:24]}"
        records.append(
            ManifestRecord(
                sample_id=row["sample_id"],
                relative_path="",
                private_object_id=object_id,
                sha256=row["sha256"],
                source_group_id=row["source_group_id"],
                parent_sample_id="",
                source_type="real_authorised",
                provider_code=row["provider_code"],
                label=row["fraud_label"],
                tamper_operations=(),
                tamper_metadata="",
                split=row["split"],
                consent_or_licence_reference=row["consent_or_licence_reference"],
                contains_personal_data=False,
                anonymisation_status="anonymised",
                generated_seed=None,
                notes=(
                    f"profile={GHANA_DATASET_VERSION}; provider_alias={row['provider_alias']}; "
                    f"rights_status={row['rights_status']}"
                ),
            )
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    write_manifest(output, records)
    return output


def redact_image(
    source: Path, destination: Path, boxes: Sequence[tuple[int, int, int, int]]
) -> None:
    """Apply explicit human-reviewed masks and remove EXIF metadata."""

    if not boxes:
        raise GhanaDatasetError("at least one human-reviewed redaction box is required")
    try:
        with Image.open(source) as opened:
            opened.load()
            image = ImageOps.exif_transpose(opened).convert("RGB")
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise GhanaDatasetError(f"unable to read source image: {source}") from exc
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for box in boxes:
        if len(box) != 4 or not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
            raise GhanaDatasetError(f"redaction box is outside image bounds: {box}")
        draw.rectangle(box, fill=(0, 0, 0))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() in {".jpg", ".jpeg"}:
        image.save(destination, exif=b"", quality=95, optimize=True)
    else:
        image.save(destination, exif=b"")


def init_workspace(root: Path) -> tuple[Path, ...]:
    """Create the ignored Ghana corpus workspace without overwriting data."""

    directories = (
        root / "images" / "train",
        root / "images" / "validation",
        root / "images" / "test",
        root / "images" / "review",
        root / "metadata",
        root / "provenance",
        root / "splits",
        root / "audits",
        root / "docs",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    public_manifest_header = (
        ",".join(
            (
                "sample_id",
                "provider_code",
                "fraud_label",
                "scam_subtype",
                "language_primary",
                "media_type",
                "quality",
                "ghana_evidence",
                "pii_status",
                "rights_status",
                "split",
                "sha256",
            )
        )
        + "\n"
    )
    collection_queries_header = (
        ",".join(("query_id", "query", "source_family", "platform", "run_date", "status", "notes"))
        + "\n"
    )
    split_assignments_header = (
        ",".join(("source_group_id", "split", "assignment_method", "seed", "assigned_at", "notes"))
        + "\n"
    )
    duplicate_clusters_header = (
        ",".join(("cluster_id", "sample_id", "cluster_type", "comparison", "decision", "notes"))
        + "\n"
    )
    templates = {
        root / "metadata" / "labels_adjudicated.csv": ",".join(LABEL_COLUMNS) + "\n",
        root / "metadata" / "manifest_public.csv": public_manifest_header,
        root / "provenance" / "manifest_private.csv": ",".join(PRIVATE_PROVENANCE_COLUMNS) + "\n",
        root / "provenance" / "source_registry.csv": ",".join(SOURCE_REGISTRY_COLUMNS) + "\n",
        root / "provenance" / "collection_queries.csv": collection_queries_header,
        root / "splits" / "split_assignments.csv": split_assignments_header,
        root / "audits" / "checksums_sha256.txt": "",
        root / "audits" / "duplicate_clusters.csv": duplicate_clusters_header,
    }
    for path, content in templates.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8", newline="")
    return directories
