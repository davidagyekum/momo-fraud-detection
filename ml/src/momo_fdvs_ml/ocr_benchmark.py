"""Split-bound pretrained OCR adapters, benchmark metrics and private bundles."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import re
import shutil
import statistics
import tempfile
import time
import unicodedata
import zipfile
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol, cast

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from momo_fdvs_ml.ghana_pipeline import load_private_text_development_records
from momo_fdvs_ml.ocr_parser import (
    _PHONE,
    CRITICAL_FIELDS,
    FIELD_CONFIDENCE_THRESHOLD,
    OCR_FIELD_SCHEMA_VERSION,
    OCR_PARSER_VERSION,
    AmountCandidateSnapshot,
    ParserResult,
    _amount_candidate_snapshot,
    _normalize_phone,
    parse_momo_text,
)

OCR_ADAPTER_SCHEMA_VERSION: Final = "ocr-adapter-result-v1"
OCR_DEVELOPMENT_BUNDLE_VERSION: Final = "ghana-ocr-development-bundle-v1"
OCR_BENCHMARK_REPORT_VERSION: Final = "ghana-ocr-benchmark-report-v2"
OCR_PARSER_CEILING_REPORT_VERSION: Final = "ghana-ocr-parser-ceiling-report-v4"
OCR_MISMATCH_ATTRIBUTION_VERSION: Final = "ghana-ocr-mismatch-attribution-v1"
OCR_SELECTED_BUNDLE_VERSION: Final = "ghana-ocr-selected-bundle-v2"
OCR_BENCHMARK_VERSION: Final = "ghana-ocr-benchmark-v1"
OCR_BENCHMARK_CONFIG_VERSION: Final = "ocr-benchmark-config-v2"
REQUIRED_ENGINES: Final = ("tesseract", "easyocr", "paddleocr")
REQUIRED_ENGINE_MAJOR_VERSIONS: Final = {"tesseract": 5}
PREPROCESSING_VARIANTS: Final = (
    "original_rgb",
    "normalized_rgb",
    "grayscale_contrast",
    "adaptive_threshold",
    "field_region",
)
FIELD_WEIGHTS: Final = {
    "amount": 0.30,
    "reference": 0.25,
    "timestamp": 0.15,
    "recipient": 0.15,
}
RELEASE_GATES: Final = {
    "amount": 0.95,
    "reference": 0.90,
    "timestamp": 0.90,
    "recipient": 0.90,
    "required_field_parse_success": 0.90,
}
_PARSER_WARNING_CODE: Final = re.compile(r"[A-Z][A-Z0-9_]{2,63}")
_PARSER_WARNING_CODES: Final = frozenset(
    {
        "AMOUNT_AMBIGUOUS",
        "AMOUNT_NOT_FOUND",
        "DATE_ORDER_AMBIGUOUS_DAY_FIRST_USED",
        "RECIPIENT_FORMAT_INVALID",
        "RECIPIENT_NOT_FOUND",
        "REFERENCE_FORMAT_INVALID",
        "REFERENCE_NOT_FOUND",
        "REFERENCE_OI_AMBIGUITY_PRESERVED",
        "TIMESTAMP_FORMAT_INVALID",
        "TIMESTAMP_NOT_FOUND",
        "WALLET_AMBIGUOUS",
        "WALLET_FORMAT_INVALID",
        "WALLET_NOT_FOUND",
        "WALLET_UNAVAILABLE",
        "WALLET_UNLABELLED",
    }
)
_COMMIT_SHA: Final = re.compile(r"[0-9a-f]{40}")
_SHA256: Final = re.compile(r"[0-9a-f]{64}")
_COUNT_BUCKETS: Final = ("0", "1", "2", "3_plus")
_AMOUNT_ATTRIBUTION_CATEGORIES: Final = (
    "exact_selected",
    "no_valid_currency_candidate",
    "truth_in_active_pool_not_exact",
    "truth_in_suppressed_currency_pool",
    "truth_absent_all_candidate_pools",
)
_TEXT_ATTRIBUTION_CATEGORIES: Final = (
    "exact_selected",
    "truth_present_parser_unavailable",
    "truth_absent_parser_unavailable",
    "selected_contains_truth",
    "truth_contains_selected",
    "truth_present_not_selected",
    "truth_absent_transcript",
)
_REFERENCE_ALLOWED: Final = re.compile(r"[A-Z0-9._/-]{5,50}")
_REFERENCE_UNANCHORED: Final = re.compile(
    r"(?<![A-Z0-9._/-])([A-Z0-9._/-]{5,50})(?![A-Z0-9._/-])",
    re.IGNORECASE,
)
_REFERENCE_LINE_ANCHOR: Final = re.compile(
    r"(?:transaction\s*(?:id|reference|ref)|reference|ref\b|receipt\s*id)"
    r"\s*(?:is\s*)?(?:[:#=-]\s*|\s+)"
    r"([A-Z0-9._/-][A-Z0-9._/\-\s]{4,100})",
    re.IGNORECASE,
)
_PARSER_COMPARISON_FIELDS: Final = (
    "amount",
    "reference",
    "timestamp",
    "recipient",
    "recipient_wallet",
)
_PARSER_CEILING_FIELDS: Final = ("amount", "reference", "timestamp", "recipient")
_FIELD_OUTCOME_KEYS: Final = ("exact", "mismatch", "unavailable")
_RECIPIENT_TRUTH_SUBTYPE_KEYS: Final = (
    "recipient_name_truth",
    "recipient_wallet_truth",
)
_AMOUNT_POOL_PRESENCE_KEYS: Final = (
    "labelled_nonempty",
    "currency_nonempty",
    "both_nonempty",
    "labelled_active",
    "currency_fallback_active",
)
_AMOUNT_CANDIDATE_POOLS: Final = ("labelled", "currency", "active")
_ATTRIBUTION_FIELDS: Final = ("amount", "recipient", "reference", "timestamp")
_PRIVACY_BOUNDARY_FLAGS: Final = (
    "raw_text_persisted",
    "field_values_persisted",
    "record_identifiers_persisted",
    "locked_test_accessed",
    "training_executed",
)
_PARSER_CEILING_REPORT_KEYS: Final = frozenset(
    {
        "schema_version",
        "diagnostic_contract_version",
        "benchmark_version",
        "parser_version",
        "field_schema_version",
        "implementation_commit_sha",
        "development_manifest_sha256",
        "source_split_manifest_sha256",
        "partition",
        "record_count",
        "field_scored_record_count",
        "field_exact",
        "field_outcome_counts",
        "parser_warning_counts",
        "parser_warning_counts_by_observed_field",
        "recipient_truth_subtype_counts",
        "recipient_secondary_truth_present_count",
        "amount_candidate_pool_presence",
        "amount_candidate_count_buckets",
        "mismatch_attribution_counts",
        "required_field_scored_record_count",
        "required_field_parse_success",
        "parser_inconclusive_rate",
        *_PRIVACY_BOUNDARY_FLAGS,
    }
)


class OCRBenchmarkError(RuntimeError):
    """Raised when OCR benchmarking would violate an integrity or split boundary."""


class OCRAdapterError(OCRBenchmarkError):
    """Raised with a stable, non-sensitive adapter failure category."""

    def __init__(self, message: str, *, reason_code: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


@dataclass(frozen=True)
class OCRToken:
    text: str
    confidence: float
    bbox: tuple[int, int, int, int]
    line_id: str | None = None


@dataclass(frozen=True)
class OCRAdapterResult:
    schema_version: str
    engine: str
    engine_version: str
    configuration: str
    raw_text: str
    text_confidence: float
    tokens: tuple[OCRToken, ...]
    latency_ms: float
    device: str
    warnings: tuple[str, ...] = ()

    def as_dict(self, *, include_text: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": self.schema_version,
            "engine": self.engine,
            "engine_version": self.engine_version,
            "configuration": self.configuration,
            "text_confidence": self.text_confidence,
            "tokens": [asdict(token) for token in self.tokens] if include_text else [],
            "latency_ms": self.latency_ms,
            "device": self.device,
            "warnings": list(self.warnings),
        }
        if include_text:
            payload["raw_text"] = self.raw_text
        return payload


@dataclass(frozen=True)
class OCRConfiguration:
    engine: str
    variant: str
    engine_options: Mapping[str, object]

    @property
    def configuration_id(self) -> str:
        encoded = json.dumps(
            {
                "engine": self.engine,
                "variant": self.variant,
                "engine_options": dict(sorted(self.engine_options.items())),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return f"{self.engine}-{hashlib.sha256(encoded).hexdigest()[:12]}"


class OCRAdapter(Protocol):
    engine: str
    engine_version: str

    def extract(self, image: Image.Image, *, configuration: str) -> OCRAdapterResult: ...


class _EasyReader(Protocol):
    def readtext(self, image: np.ndarray, *, detail: int, paragraph: bool) -> Sequence[object]: ...


class _PaddleResult(Protocol):
    @property
    def json(self) -> object: ...


class _PaddlePipeline(Protocol):
    def predict(self, image: np.ndarray) -> Sequence[_PaddleResult]: ...


def _sha256_file(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        raise OCRBenchmarkError("unable to hash file") from None


def _canonical_hash(value: Mapping[str, object], hash_field: str) -> str:
    canonical = dict(value)
    canonical.pop(hash_field, None)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _require_count(value: object, *, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise OCRBenchmarkError(f"OCR parser ceiling {label} count is invalid")
    return value


def _require_count_map(
    value: object,
    *,
    keys: Sequence[str],
    label: str,
) -> dict[str, int]:
    if not isinstance(value, dict) or set(value) != set(keys):
        raise OCRBenchmarkError(f"OCR parser ceiling {label} keys are invalid")
    counts: dict[str, int] = {}
    for key in keys:
        counts[key] = _require_count(value[key], label=label)
    return counts


def _require_partition_total(
    counts: Mapping[str, int],
    *,
    denominator: int,
    label: str,
) -> None:
    if sum(counts.values()) != denominator:
        raise OCRBenchmarkError(f"OCR parser ceiling {label} total is invalid")


def _require_rate(value: object, *, allow_none: bool, label: str) -> float | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, float) or not 0.0 <= value <= 1.0:
        raise OCRBenchmarkError(f"OCR parser ceiling {label} rate is invalid")
    return value


def _require_warning_count_map(value: object, *, label: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise OCRBenchmarkError(f"OCR parser ceiling {label} keys are invalid")
    counts: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or key not in _PARSER_WARNING_CODES:
            raise OCRBenchmarkError(f"OCR parser ceiling {label} keys are invalid")
        counts[key] = _require_count(count, label=label)
    return counts


def _validate_parser_ceiling_report(report: Mapping[str, object]) -> None:
    """Fail closed unless a complete pre-hash parser-ceiling v4 report is safe."""

    if set(report) != _PARSER_CEILING_REPORT_KEYS:
        raise OCRBenchmarkError("OCR parser ceiling report keys are invalid")
    if (
        report["schema_version"] != OCR_PARSER_CEILING_REPORT_VERSION
        or report["diagnostic_contract_version"] != OCR_MISMATCH_ATTRIBUTION_VERSION
        or report["benchmark_version"] != OCR_BENCHMARK_VERSION
        or report["parser_version"] != OCR_PARSER_VERSION
        or report["field_schema_version"] != OCR_FIELD_SCHEMA_VERSION
        or report["partition"] != "validation"
    ):
        raise OCRBenchmarkError("OCR parser ceiling metadata identity is invalid")
    if (
        not isinstance(report["implementation_commit_sha"], str)
        or _COMMIT_SHA.fullmatch(report["implementation_commit_sha"]) is None
        or not isinstance(report["development_manifest_sha256"], str)
        or _SHA256.fullmatch(report["development_manifest_sha256"]) is None
        or not isinstance(report["source_split_manifest_sha256"], str)
        or _SHA256.fullmatch(report["source_split_manifest_sha256"]) is None
    ):
        raise OCRBenchmarkError("OCR parser ceiling reproducibility identity is invalid")

    record_count = _require_count(report["record_count"], label="record")
    if record_count == 0:
        raise OCRBenchmarkError("OCR parser ceiling record total is invalid")
    denominators = _require_count_map(
        report["field_scored_record_count"],
        keys=_PARSER_CEILING_FIELDS,
        label="field scored record",
    )
    if any(count > record_count for count in denominators.values()):
        raise OCRBenchmarkError("OCR parser ceiling field scored record total is invalid")

    field_exact = report["field_exact"]
    if not isinstance(field_exact, dict) or set(field_exact) != set(_PARSER_CEILING_FIELDS):
        raise OCRBenchmarkError("OCR parser ceiling field exact keys are invalid")

    field_outcomes = report["field_outcome_counts"]
    if not isinstance(field_outcomes, dict) or set(field_outcomes) != set(_PARSER_CEILING_FIELDS):
        raise OCRBenchmarkError("OCR parser ceiling field outcome keys are invalid")
    for field in _PARSER_CEILING_FIELDS:
        outcome_counts = _require_count_map(
            field_outcomes[field],
            keys=_FIELD_OUTCOME_KEYS,
            label=f"{field} field outcome",
        )
        _require_partition_total(
            outcome_counts,
            denominator=denominators[field],
            label=f"{field} field outcome",
        )
        exact_rate = _require_rate(
            field_exact[field],
            allow_none=denominators[field] == 0,
            label=f"{field} field exact",
        )
        if denominators[field] == 0:
            if exact_rate is not None:
                raise OCRBenchmarkError(f"OCR parser ceiling {field} field exact rate is invalid")
        elif exact_rate != outcome_counts["exact"] / denominators[field]:
            raise OCRBenchmarkError(f"OCR parser ceiling {field} field exact rate is invalid")

    _require_warning_count_map(report["parser_warning_counts"], label="parser warning")
    warning_counts_by_field = report["parser_warning_counts_by_observed_field"]
    if not isinstance(warning_counts_by_field, dict) or not set(warning_counts_by_field).issubset(
        _PARSER_COMPARISON_FIELDS
    ):
        raise OCRBenchmarkError("OCR parser ceiling observed-field warning keys are invalid")
    for field in _PARSER_COMPARISON_FIELDS:
        if field in warning_counts_by_field:
            _require_warning_count_map(
                warning_counts_by_field[field],
                label=f"{field} observed-field warning",
            )

    recipient_subtypes = _require_count_map(
        report["recipient_truth_subtype_counts"],
        keys=_RECIPIENT_TRUTH_SUBTYPE_KEYS,
        label="recipient truth subtype",
    )
    _require_partition_total(
        recipient_subtypes,
        denominator=denominators["recipient"],
        label="recipient truth subtype",
    )
    secondary_truth_count = _require_count(
        report["recipient_secondary_truth_present_count"],
        label="recipient secondary truth present",
    )
    if secondary_truth_count > recipient_subtypes["recipient_name_truth"]:
        raise OCRBenchmarkError("OCR parser ceiling recipient secondary truth total is invalid")

    presence = _require_count_map(
        report["amount_candidate_pool_presence"],
        keys=_AMOUNT_POOL_PRESENCE_KEYS,
        label="amount candidate pool presence",
    )
    amount_denominator = denominators["amount"]
    if (
        any(count > amount_denominator for count in presence.values())
        or presence["both_nonempty"] > presence["labelled_nonempty"]
        or presence["both_nonempty"] > presence["currency_nonempty"]
        or presence["both_nonempty"]
        < presence["labelled_nonempty"] + presence["currency_nonempty"] - amount_denominator
        or presence["labelled_nonempty"] > presence["labelled_active"]
        or presence["labelled_active"] + presence["currency_fallback_active"] != amount_denominator
    ):
        raise OCRBenchmarkError("OCR parser ceiling amount candidate presence total is invalid")

    candidate_buckets = report["amount_candidate_count_buckets"]
    if not isinstance(candidate_buckets, dict) or set(candidate_buckets) != set(
        _AMOUNT_CANDIDATE_POOLS
    ):
        raise OCRBenchmarkError("OCR parser ceiling amount candidate bucket keys are invalid")
    validated_buckets: dict[str, dict[str, int]] = {}
    for pool in _AMOUNT_CANDIDATE_POOLS:
        validated_buckets[pool] = _require_count_map(
            candidate_buckets[pool],
            keys=_COUNT_BUCKETS,
            label=f"{pool} amount candidate bucket",
        )
        _require_partition_total(
            validated_buckets[pool],
            denominator=amount_denominator,
            label=f"{pool} amount candidate bucket",
        )
    if (
        validated_buckets["labelled"]["0"] != amount_denominator - presence["labelled_nonempty"]
        or validated_buckets["currency"]["0"] != amount_denominator - presence["currency_nonempty"]
    ):
        raise OCRBenchmarkError("OCR parser ceiling amount candidate bucket presence is invalid")

    attributions = report["mismatch_attribution_counts"]
    if not isinstance(attributions, dict) or set(attributions) != set(_ATTRIBUTION_FIELDS):
        raise OCRBenchmarkError("OCR parser ceiling mismatch attribution keys are invalid")
    attribution_keys = {
        "amount": _AMOUNT_ATTRIBUTION_CATEGORIES,
        "recipient": _TEXT_ATTRIBUTION_CATEGORIES,
        "reference": _TEXT_ATTRIBUTION_CATEGORIES,
        "timestamp": ("deferred_insufficient_support",),
    }
    for field in _ATTRIBUTION_FIELDS:
        attribution_counts = _require_count_map(
            attributions[field],
            keys=attribution_keys[field],
            label=f"{field} mismatch attribution",
        )
        _require_partition_total(
            attribution_counts,
            denominator=denominators[field],
            label=f"{field} mismatch attribution",
        )

    required_denominator = _require_count(
        report["required_field_scored_record_count"],
        label="required field scored record",
    )
    if required_denominator > min(denominators.values()):
        raise OCRBenchmarkError("OCR parser ceiling required field scored record total is invalid")
    required_rate = _require_rate(
        report["required_field_parse_success"],
        allow_none=required_denominator == 0,
        label="required field parse success",
    )
    if (required_denominator == 0) != (required_rate is None):
        raise OCRBenchmarkError("OCR parser ceiling required field parse success rate is invalid")
    _require_rate(
        report["parser_inconclusive_rate"],
        allow_none=False,
        label="parser inconclusive",
    )
    if any(report[flag] is not False for flag in _PRIVACY_BOUNDARY_FLAGS):
        raise OCRBenchmarkError("OCR parser ceiling privacy boundary is invalid")


def _load_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise OCRBenchmarkError("unable to read JSON object") from None
    if not isinstance(value, dict):
        raise OCRBenchmarkError("JSON content must contain an object")
    return value


def _write_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(temporary, path)
    except OSError:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
        raise OCRBenchmarkError("unable to write JSON output") from None


def _require_private_path(path: Path, repository_root: Path, label: str) -> None:
    resolved = path.resolve()
    if resolved == repository_root.resolve() or resolved.is_relative_to(repository_root.resolve()):
        raise OCRBenchmarkError(f"{label} must remain outside the repository")


def engine_inventory() -> dict[str, dict[str, object]]:
    """Report package availability without loading models or downloading weights."""

    packages = {
        "tesseract": ("pytesseract", "Apache-2.0", "system binary plus Python adapter"),
        "easyocr": ("easyocr", "Apache-2.0", "model weights required"),
        "paddleocr": ("paddleocr", "Apache-2.0", "PaddlePaddle and model weights required"),
    }
    inventory: dict[str, dict[str, object]] = {}
    for engine, (package, license_name, note) in packages.items():
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            version = None
        inventory[engine] = {
            "package": package,
            "package_version": version,
            "package_available": version is not None,
            "license": license_name,
            "note": note,
        }
    return inventory


def load_ocr_benchmark_config(path: Path) -> dict[str, object]:
    """Validate the versioned matrix, weights, gates and locked-test policy."""

    config = _load_object(path)
    engines = config.get("engines")
    variants = config.get("preprocessing_variants")
    weights = config.get("selection_weights")
    gates = config.get("release_gates")
    policy = config.get("data_policy")
    selection_policy = config.get("selection_policy")
    expected_weights = {
        "amount_exact": FIELD_WEIGHTS["amount"],
        "reference_exact": FIELD_WEIGHTS["reference"],
        "timestamp_exact": FIELD_WEIGHTS["timestamp"],
        "recipient_exact": FIELD_WEIGHTS["recipient"],
        "cer_wer_composite": 0.10,
        "median_latency": 0.05,
    }
    expected_gates = {
        "amount_exact": RELEASE_GATES["amount"],
        "reference_exact": RELEASE_GATES["reference"],
        "timestamp_exact": RELEASE_GATES["timestamp"],
        "recipient_exact": RELEASE_GATES["recipient"],
        "required_field_parse_success": RELEASE_GATES["required_field_parse_success"],
    }
    engine_contracts = (
        {entry.get("engine"): entry for entry in engines if isinstance(entry, dict)}
        if isinstance(engines, list)
        else {}
    )
    tesseract_contract = engine_contracts.get("tesseract", {})
    paddle_contract = engine_contracts.get("paddleocr", {})
    if (
        config.get("schema_version") != OCR_BENCHMARK_CONFIG_VERSION
        or config.get("benchmark_version") != OCR_BENCHMARK_VERSION
        or config.get("two_stage_selection") is not True
        or not isinstance(engines, list)
        or {entry.get("engine") for entry in engines if isinstance(entry, dict)}
        != set(REQUIRED_ENGINES)
        or variants != list(PREPROCESSING_VARIANTS)
        or weights != expected_weights
        or gates != expected_gates
        or not isinstance(policy, dict)
        or policy.get("locked_test_access_allowed") is not False
        or policy.get("primary_partition") != "controlled_real_validation"
        or policy.get("synthetic_results_supplementary_only") is not True
        or selection_policy
        != {
            "complete_record_coverage_required": True,
            "required_engines_available": True,
        }
        or tesseract_contract.get("required_major_version") != 5
        or paddle_contract.get("options")
        != {
            "device": "cpu",
            "enable_mkldnn": False,
            "language": "en",
            "ocr_version": "PP-OCRv6",
        }
    ):
        raise OCRBenchmarkError("OCR benchmark configuration drifted from PR17 policy")
    return config


def preprocessing_variants(
    content: bytes,
    *,
    field_boxes: Sequence[Sequence[int]] = (),
    target_width: int = 1200,
) -> dict[str, Image.Image]:
    """Create deterministic variants while retaining decimal points and digits."""

    try:
        import io

        with Image.open(io.BytesIO(content)) as opened:
            original = ImageOps.exif_transpose(opened).convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise OCRBenchmarkError("benchmark image could not be decoded") from exc
    scale = min(3.0, max(1.0, target_width / max(original.width, 1)))
    normalized = (
        original.resize(
            (round(original.width * scale), round(original.height * scale)),
            Image.Resampling.LANCZOS,
        )
        if scale > 1
        else original.copy()
    )
    gray = ImageOps.autocontrast(normalized.convert("L"))
    variants: dict[str, Image.Image] = {
        "original_rgb": original,
        "normalized_rgb": normalized,
        "grayscale_contrast": gray,
    }
    try:
        cv2 = importlib.import_module("cv2")
        array = np.asarray(gray)
        threshold = cv2.adaptiveThreshold(
            array,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            11,
        )
        variants["adaptive_threshold"] = Image.fromarray(threshold)
    except (ImportError, AttributeError):
        pass
    valid_boxes = [
        tuple(int(value) for value in box)
        for box in field_boxes
        if len(box) == 4
        and all(isinstance(value, int) and not isinstance(value, bool) for value in box)
    ]
    if valid_boxes:
        x0 = max(0, min(box[0] for box in valid_boxes))
        y0 = max(0, min(box[1] for box in valid_boxes))
        x1 = min(original.width, max(box[0] + box[2] for box in valid_boxes))
        y1 = min(original.height, max(box[1] + box[3] for box in valid_boxes))
        if x1 > x0 and y1 > y0 and (x1 - x0, y1 - y0) != original.size:
            variants["field_region"] = original.crop((x0, y0, x1, y1))
    return variants


class TesseractAdapter:
    engine = "tesseract"

    def __init__(
        self,
        *,
        psm: int = 6,
        language: str = "eng",
        runner: Callable[[Image.Image, str], Mapping[str, Sequence[object]]] | None = None,
        version: str | None = None,
    ) -> None:
        self.psm = psm
        self.language = language
        self._runner = runner
        self.engine_version = version or "unresolved"

    def extract(self, image: Image.Image, *, configuration: str) -> OCRAdapterResult:
        started = time.perf_counter()
        if self._runner is None:
            try:
                pytesseract = importlib.import_module("pytesseract")
                self.engine_version = str(pytesseract.get_tesseract_version()).splitlines()[0]
                data = pytesseract.image_to_data(
                    image,
                    lang=self.language,
                    config=f"--psm {self.psm}",
                    output_type=pytesseract.Output.DICT,
                )
            except (ImportError, OSError, RuntimeError) as exc:
                raise OCRAdapterError(
                    "tesseract engine is unavailable", reason_code="OCR_ENGINE_UNAVAILABLE"
                ) from exc
        else:
            data = self._runner(image, f"--psm {self.psm}")
        tokens: list[OCRToken] = []
        texts = data.get("text", ())
        for index, raw in enumerate(texts):
            text = str(raw).strip()
            if not text:
                continue
            try:
                confidence = max(0.0, min(1.0, float(data["conf"][index]) / 100))
                bbox = (
                    int(data["left"][index]),
                    int(data["top"][index]),
                    int(data["width"][index]),
                    int(data["height"][index]),
                )
                line_id = ":".join(
                    str(data[key][index]) for key in ("block_num", "par_num", "line_num")
                )
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise OCRAdapterError(
                    "tesseract returned an invalid token schema",
                    reason_code="OCR_ENGINE_RESULT_INVALID",
                ) from exc
            tokens.append(OCRToken(text, round(confidence, 4), bbox, line_id))
        return _adapter_result(
            engine=self.engine,
            version=self.engine_version,
            configuration=configuration,
            tokens=tokens,
            started=started,
            device="cpu",
        )


class EasyOCRAdapter:
    engine = "easyocr"

    def __init__(
        self,
        *,
        reader: object | None = None,
        gpu: bool = False,
        model_storage_directory: str | None = None,
    ) -> None:
        if reader is None:
            try:
                easyocr = importlib.import_module("easyocr")
                options: dict[str, object] = {"gpu": gpu}
                if model_storage_directory is not None:
                    options["model_storage_directory"] = model_storage_directory
                reader = easyocr.Reader(["en"], **options)
            except (ImportError, OSError, RuntimeError) as exc:
                raise OCRAdapterError(
                    "easyocr engine is unavailable", reason_code="OCR_ENGINE_UNAVAILABLE"
                ) from exc
        self.reader = cast(_EasyReader, reader)
        try:
            self.engine_version = importlib.metadata.version("easyocr")
        except importlib.metadata.PackageNotFoundError:
            self.engine_version = "injected-test-double"
        self.device = "accelerator" if gpu else "cpu"

    def extract(self, image: Image.Image, *, configuration: str) -> OCRAdapterResult:
        started = time.perf_counter()
        try:
            rows = self.reader.readtext(np.asarray(image), detail=1, paragraph=False)
        except (AttributeError, RuntimeError, ValueError) as exc:
            raise OCRAdapterError(
                "easyocr inference failed", reason_code="OCR_ENGINE_INFERENCE_FAILED"
            ) from exc
        tokens: list[OCRToken] = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                raise OCRAdapterError(
                    "easyocr returned an invalid token schema",
                    reason_code="OCR_ENGINE_RESULT_INVALID",
                )
            polygon, text, confidence = row
            points = list(polygon)
            xs = [int(point[0]) for point in points]
            ys = [int(point[1]) for point in points]
            bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
            tokens.append(OCRToken(str(text), round(float(confidence), 4), bbox))
        return _adapter_result(
            engine=self.engine,
            version=self.engine_version,
            configuration=configuration,
            tokens=tokens,
            started=started,
            device=self.device,
        )


class PaddleOCRAdapter:
    engine = "paddleocr"

    def __init__(
        self,
        *,
        pipeline: object | None = None,
        device: str = "cpu",
        ocr_version: str = "PP-OCRv6",
        enable_mkldnn: bool = False,
    ) -> None:
        if pipeline is None:
            try:
                paddleocr = importlib.import_module("paddleocr")
                pipeline = paddleocr.PaddleOCR(
                    lang="en",
                    device=device,
                    ocr_version=ocr_version,
                    enable_mkldnn=enable_mkldnn,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
            except (ImportError, OSError, RuntimeError) as exc:
                raise OCRAdapterError(
                    "paddleocr engine is unavailable", reason_code="OCR_ENGINE_UNAVAILABLE"
                ) from exc
        self.pipeline = cast(_PaddlePipeline, pipeline)
        try:
            self.engine_version = importlib.metadata.version("paddleocr")
        except importlib.metadata.PackageNotFoundError:
            self.engine_version = "injected-test-double"
        self.device = device

    def extract(self, image: Image.Image, *, configuration: str) -> OCRAdapterResult:
        started = time.perf_counter()
        try:
            results = list(self.pipeline.predict(np.asarray(image)))
        except (AttributeError, RuntimeError, ValueError) as exc:
            raise OCRAdapterError(
                "paddleocr inference failed", reason_code="OCR_ENGINE_INFERENCE_FAILED"
            ) from exc
        if len(results) != 1:
            raise OCRAdapterError(
                "paddleocr returned an invalid result count",
                reason_code="OCR_ENGINE_RESULT_INVALID",
            )
        payload = results[0].json
        if callable(payload):
            payload = payload()
        if not isinstance(payload, dict):
            raise OCRAdapterError(
                "paddleocr returned an invalid result schema",
                reason_code="OCR_ENGINE_RESULT_INVALID",
            )
        data = payload.get("res", payload)
        if not isinstance(data, dict):
            raise OCRAdapterError(
                "paddleocr returned an invalid result schema",
                reason_code="OCR_ENGINE_RESULT_INVALID",
            )
        texts = data.get("rec_texts", [])
        scores = data.get("rec_scores", [])
        boxes = data.get("rec_boxes", [])
        if not (len(texts) == len(scores) == len(boxes)):
            raise OCRAdapterError(
                "paddleocr returned misaligned tokens",
                reason_code="OCR_ENGINE_RESULT_INVALID",
            )
        tokens = [
            OCRToken(
                str(text),
                round(float(score), 4),
                (int(box[0]), int(box[1]), int(box[2]) - int(box[0]), int(box[3]) - int(box[1])),
            )
            for text, score, box in zip(texts, scores, boxes, strict=True)
        ]
        return _adapter_result(
            engine=self.engine,
            version=self.engine_version,
            configuration=configuration,
            tokens=tokens,
            started=started,
            device=self.device,
        )


def _adapter_result(
    *,
    engine: str,
    version: str,
    configuration: str,
    tokens: Sequence[OCRToken],
    started: float,
    device: str,
) -> OCRAdapterResult:
    ordered = sorted(tokens, key=lambda token: (token.bbox[1], token.bbox[0]))
    text = "\n".join(token.text for token in ordered)
    confidence = statistics.fmean(token.confidence for token in ordered) if ordered else 0.0
    return OCRAdapterResult(
        OCR_ADAPTER_SCHEMA_VERSION,
        engine,
        version,
        configuration,
        text,
        round(confidence, 4),
        tuple(ordered),
        round((time.perf_counter() - started) * 1000, 4),
        device,
        () if ordered else ("OCR_NO_TEXT",),
    )


def prepare_ocr_development_bundle(
    *,
    split_manifest_path: Path,
    image_bindings: Mapping[str, Path],
    image_sha256_bindings: Mapping[str, str] | None = None,
    truth_root: Path,
    output_root: Path,
    repository_root: Path,
) -> Path:
    """Copy only explicitly bound train/validation images and truth into a private bundle."""

    for path, label in (
        (split_manifest_path, "split manifest"),
        (truth_root, "OCR truth"),
        (output_root, "OCR development bundle"),
    ):
        _require_private_path(path, repository_root, label)
    development = load_private_text_development_records(split_manifest_path)
    screenshot_records = {
        cast(str, record["record_id"]): record
        for record in development
        if record.get("source_corpus") == "screenshot_ocr"
    }
    unknown = sorted(set(image_bindings) - set(screenshot_records))
    if unknown:
        raise OCRBenchmarkError("image bindings contain a non-development or locked-test record")
    missing = sorted(set(screenshot_records) - set(image_bindings))
    if missing:
        raise OCRBenchmarkError("image bindings do not cover every development screenshot")
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_records: list[dict[str, object]] = []
    for record_id, assignment in sorted(screenshot_records.items()):
        source = image_bindings[record_id].resolve()
        truth_path = (truth_root / f"{record_id}.json").resolve()
        truth = _load_object(truth_path)
        source_hash = _sha256_file(source)
        expected_image_hash = (
            image_sha256_bindings.get(record_id)
            if image_sha256_bindings is not None
            else truth.get("source_sha256")
        )
        if (
            truth.get("record_id") != record_id
            or expected_image_hash != source_hash
            or truth.get("training_executed") is not False
        ):
            raise OCRBenchmarkError("development image and OCR truth identity mismatch")
        suffix = source.suffix.casefold()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise OCRBenchmarkError("development image extension is unsupported")
        image_relative = Path("images") / f"{record_id}{suffix}"
        truth_relative = Path("truth") / f"{record_id}.json"
        image_destination = output_root / image_relative
        truth_destination = output_root / truth_relative
        image_destination.parent.mkdir(parents=True, exist_ok=True)
        truth_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, image_destination)
        shutil.copyfile(truth_path, truth_destination)
        manifest_records.append(
            {
                "record_id": record_id,
                "source_group_id": assignment["source_group_id"],
                "split": assignment["split"],
                "locked_test": False,
                "image_path": image_relative.as_posix(),
                "image_sha256": source_hash,
                "truth_source_sha256": truth.get("source_sha256"),
                "image_relationship": (
                    "source" if truth.get("source_sha256") == source_hash else "governed_derivative"
                ),
                "truth_path": truth_relative.as_posix(),
                "truth_sha256": _sha256_file(truth_destination),
            }
        )
    split_manifest = _load_object(split_manifest_path)
    manifest: dict[str, object] = {
        "schema_version": OCR_DEVELOPMENT_BUNDLE_VERSION,
        "benchmark_version": OCR_BENCHMARK_VERSION,
        "source_split_manifest_sha256": split_manifest.get("manifest_sha256"),
        "records": manifest_records,
        "record_count": len(manifest_records),
        "split_counts": {
            split: sum(record["split"] == split for record in manifest_records)
            for split in ("train", "validation")
        },
        "locked_test_included": False,
        "training_executed": False,
    }
    manifest["manifest_sha256"] = _canonical_hash(manifest, "manifest_sha256")
    path = output_root / "development-manifest.json"
    _write_json(path, manifest)
    return path


def load_ocr_development_bundle(
    manifest_path: Path, *, partition: str
) -> tuple[dict[str, object], ...]:
    """Load only train or validation; test is not a valid API value."""

    if partition not in {"train", "validation"}:
        raise OCRBenchmarkError("OCR development partition must be train or validation")
    manifest = _load_object(manifest_path)
    if (
        manifest.get("schema_version") != OCR_DEVELOPMENT_BUNDLE_VERSION
        or manifest.get("locked_test_included") is not False
        or manifest.get("training_executed") is not False
        or manifest.get("manifest_sha256") != _canonical_hash(manifest, "manifest_sha256")
    ):
        raise OCRBenchmarkError("OCR development bundle identity or lock state is invalid")
    records = manifest.get("records")
    if not isinstance(records, list) or not all(isinstance(record, dict) for record in records):
        raise OCRBenchmarkError("OCR development bundle records are invalid")
    selected = tuple(record for record in records if record.get("split") == partition)
    if any(record.get("locked_test") is not False for record in selected):
        raise OCRBenchmarkError("OCR development bundle exposed a locked record")
    return selected


def edit_distance(left: Sequence[object], right: Sequence[object]) -> int:
    """Return Levenshtein distance without a heavyweight metric dependency."""

    prior = list(range(len(right) + 1))
    for row, left_value in enumerate(left, start=1):
        current = [row]
        for column, right_value in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    prior[column] + 1,
                    prior[column - 1] + (left_value != right_value),
                )
            )
        prior = current
    return prior[-1]


def text_error_rates(expected: str, observed: str) -> tuple[float, float]:
    normalized_expected = " ".join(expected.casefold().split())
    normalized_observed = " ".join(observed.casefold().split())
    cer = edit_distance(normalized_expected, normalized_observed) / max(len(normalized_expected), 1)
    expected_words = normalized_expected.split()
    observed_words = normalized_observed.split()
    wer = edit_distance(expected_words, observed_words) / max(len(expected_words), 1)
    return round(cer, 6), round(wer, 6)


def _truth_fields(truth: Mapping[str, object]) -> dict[str, str]:
    fields = truth.get("fields")
    if not isinstance(fields, list):
        raise OCRBenchmarkError("OCR truth fields are invalid")
    values: dict[str, str] = {}
    for field in fields:
        if not isinstance(field, dict):
            raise OCRBenchmarkError("OCR truth field is invalid")
        name = field.get("name")
        normalized = field.get("normalized")
        if isinstance(name, str) and isinstance(normalized, str) and normalized:
            values.setdefault(name, normalized)
    return values


@dataclass(frozen=True)
class FieldComparison:
    """One private in-memory field comparison with explicit field identity."""

    aggregate_field: str
    truth_field: str
    observed_field: str
    expected_normalized: str
    observed_normalized: str | None
    matched: bool
    available: bool
    warnings: tuple[str, ...]
    truth_subtype: str | None = None
    secondary_truth_present: bool = False


def _candidate_count_bucket(values: Sequence[str]) -> str:
    count = len(values)
    if count == 0:
        return "0"
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    return "3_plus"


def _classify_amount_attribution(
    comparison: FieldComparison,
    snapshot: AmountCandidateSnapshot,
) -> str:
    if comparison.matched:
        return "exact_selected"
    truth = comparison.expected_normalized
    labelled = set(snapshot.labelled_distinct_normalized)
    currency = set(snapshot.currency_distinct_normalized)
    active = set(snapshot.active_distinct_normalized)
    if not labelled and not currency:
        return "no_valid_currency_candidate"
    if truth in active:
        return "truth_in_active_pool_not_exact"
    if snapshot.active_source == "labelled" and truth not in labelled and truth in currency:
        return "truth_in_suppressed_currency_pool"
    return "truth_absent_all_candidate_pools"


def _valid_reference_span(value: str) -> str | None:
    normalized = re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).upper()
    if _REFERENCE_ALLOWED.fullmatch(normalized) is None or not any(
        character.isdigit() for character in normalized
    ):
        return None
    return normalized


def _anchored_reference_spans(value: str) -> tuple[str, ...]:
    spans: list[str] = []
    tokens = value.split()
    for end in range(1, len(tokens) + 1):
        token = tokens[end - 1]
        if spans and token.isalpha():
            break
        if (normalized := _valid_reference_span(" ".join(tokens[:end]))) is not None:
            spans.append(normalized)
    return tuple(dict.fromkeys(spans))


def _reference_like_spans(text: str) -> tuple[str, ...]:
    spans: list[str] = []
    for raw_line in text.splitlines():
        line = unicodedata.normalize("NFKC", raw_line)
        anchored = _REFERENCE_LINE_ANCHOR.search(line)
        if anchored is not None:
            spans.extend(_anchored_reference_spans(anchored.group(1)))
        else:
            for match in _REFERENCE_UNANCHORED.finditer(line):
                if (value := _valid_reference_span(match.group(1))) is not None:
                    spans.append(value)
    return tuple(dict.fromkeys(spans))


def _classify_text_attribution(
    comparison: FieldComparison,
    *,
    truth_present: bool,
) -> str:
    if comparison.matched:
        return "exact_selected"
    if not comparison.available:
        return (
            "truth_present_parser_unavailable"
            if truth_present
            else "truth_absent_parser_unavailable"
        )
    observed = comparison.observed_normalized
    if observed is None:
        raise OCRBenchmarkError("parser comparison availability state is invalid")
    truth = comparison.expected_normalized
    if truth != observed and truth in observed:
        return "selected_contains_truth"
    if truth != observed and observed in truth:
        return "truth_contains_selected"
    return "truth_present_not_selected" if truth_present else "truth_absent_transcript"


def _normalize_recipient_name_evidence(value: str) -> str:
    normalized = re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()
    while normalized and unicodedata.category(normalized[0]).startswith("P"):
        normalized = normalized[1:].lstrip()
    while normalized and unicodedata.category(normalized[-1]).startswith("P"):
        normalized = normalized[:-1].rstrip()
    return normalized.upper()


def _recipient_truth_present(comparison: FieldComparison, transcript: str) -> bool:
    if comparison.truth_subtype == "recipient_name_truth":
        if comparison.observed_field != "recipient":
            raise OCRBenchmarkError("OCR recipient observed field is invalid")
        normalized_text = _normalize_recipient_name_evidence(transcript)
        normalized_truth = _normalize_recipient_name_evidence(comparison.expected_normalized)
        return normalized_truth in normalized_text
    if comparison.truth_subtype == "recipient_wallet_truth":
        if comparison.observed_field != "recipient_wallet":
            raise OCRBenchmarkError("OCR recipient observed field is invalid")
        normalized_candidates = {
            normalized
            for raw in _PHONE.findall(unicodedata.normalize("NFKC", transcript))
            if (normalized := _normalize_phone(raw)) is not None
        }
        return comparison.expected_normalized in normalized_candidates
    raise OCRBenchmarkError("OCR recipient truth subtype is invalid")


def _make_field_comparison(
    *,
    aggregate_field: str,
    truth_field: str,
    observed_field: str,
    expected_normalized: str,
    parser: ParserResult,
    truth_subtype: str | None = None,
    secondary_truth_present: bool = False,
) -> FieldComparison:
    try:
        observed = parser.fields[observed_field]
    except KeyError as exc:
        raise OCRBenchmarkError(f"parser is missing required field {observed_field}") from exc
    return FieldComparison(
        aggregate_field=aggregate_field,
        truth_field=truth_field,
        observed_field=observed_field,
        expected_normalized=expected_normalized,
        observed_normalized=observed.normalized,
        matched=expected_normalized == observed.normalized,
        available=bool(observed.available and observed.normalized is not None),
        warnings=tuple(observed.warnings),
        truth_subtype=truth_subtype,
        secondary_truth_present=secondary_truth_present,
    )


def compare_parser_result(
    parser: ParserResult, truth: Mapping[str, object]
) -> dict[str, FieldComparison | None]:
    """Compare normalized truth against the exact parser subfield used downstream."""

    for field in _PARSER_COMPARISON_FIELDS:
        observed = parser.fields.get(field)
        if observed is None:
            raise OCRBenchmarkError(f"parser is missing required field {field}")
        if observed.available is not (observed.normalized is not None):
            raise OCRBenchmarkError(f"parser field availability state is invalid for {field}")
    expected = _truth_fields(truth)
    comparisons: dict[str, FieldComparison | None] = {}
    for field in ("amount", "reference", "timestamp"):
        expected_normalized = expected.get(field)
        comparisons[field] = (
            None
            if expected_normalized is None
            else _make_field_comparison(
                aggregate_field=field,
                truth_field=field,
                observed_field=field,
                expected_normalized=expected_normalized,
                parser=parser,
            )
        )

    recipient_name = expected.get("recipient_name")
    recipient_wallet = expected.get("recipient_wallet")
    if recipient_name is not None:
        comparisons["recipient"] = _make_field_comparison(
            aggregate_field="recipient",
            truth_field="recipient_name",
            observed_field="recipient",
            expected_normalized=recipient_name,
            parser=parser,
            truth_subtype="recipient_name_truth",
            secondary_truth_present=recipient_wallet is not None,
        )
    elif recipient_wallet is not None:
        comparisons["recipient"] = _make_field_comparison(
            aggregate_field="recipient",
            truth_field="recipient_wallet",
            observed_field="recipient_wallet",
            expected_normalized=recipient_wallet,
            parser=parser,
            truth_subtype="recipient_wallet_truth",
        )
    else:
        comparisons["recipient"] = None
    return comparisons


def score_parser_result(
    parser: ParserResult, truth: Mapping[str, object]
) -> dict[str, bool | None]:
    """Score exact normalized fields, leaving unavailable truth out of the denominator."""

    return {
        field: None if comparison is None else comparison.matched
        for field, comparison in compare_parser_result(parser, truth).items()
    }


def aggregate_configuration_metrics(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Aggregate the predeclared PR17 weighted selector and release gates."""

    if not rows:
        raise OCRBenchmarkError("OCR configuration has no successful validation rows")
    field_scores: dict[str, float | None] = {}
    for field in FIELD_WEIGHTS:
        values = [
            bool(cast(Mapping[str, object], row["field_matches"])[field])
            for row in rows
            if cast(Mapping[str, object], row["field_matches"])[field] is not None
        ]
        field_scores[field] = statistics.fmean(values) if values else None
    required_rows = [
        all(value is True for value in cast(Mapping[str, object], row["field_matches"]).values())
        for row in rows
        if all(
            value is not None for value in cast(Mapping[str, object], row["field_matches"]).values()
        )
    ]
    parse_success = statistics.fmean(required_rows) if required_rows else None
    cer = statistics.fmean(float(cast(float | int, row["cer"])) for row in rows)
    wer = statistics.fmean(float(cast(float | int, row["wer"])) for row in rows)
    median_latency = statistics.median(float(cast(float | int, row["latency_ms"])) for row in rows)
    text_score = max(0.0, 1.0 - min(1.0, (cer + wer) / 2))
    latency_score = 1.0 / (1.0 + median_latency / 1000.0)
    weighted = sum((field_scores[name] or 0.0) * weight for name, weight in FIELD_WEIGHTS.items())
    weighted += text_score * 0.10 + latency_score * 0.05
    gates = {
        field: field_scores[field] is not None
        and cast(float, field_scores[field]) >= RELEASE_GATES[field]
        for field in FIELD_WEIGHTS
    }
    gates["required_field_parse_success"] = (
        parse_success is not None and parse_success >= RELEASE_GATES["required_field_parse_success"]
    )
    return {
        "field_exact": field_scores,
        "required_field_parse_success": parse_success,
        "mean_cer": round(cer, 6),
        "mean_wer": round(wer, 6),
        "median_latency_ms": round(median_latency, 4),
        "weighted_selection_score": round(weighted, 6),
        "release_gates": gates,
        "all_release_gates_passed": all(gates.values()),
        "record_count": len(rows),
    }


def _resolve_bundle_file(root: Path, relative: object, expected_hash: object, label: str) -> Path:
    if not isinstance(relative, str) or not isinstance(expected_hash, str):
        raise OCRBenchmarkError(f"OCR bundle {label} identity is invalid")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise OCRBenchmarkError(f"OCR bundle {label} escaped or is missing")
    if _sha256_file(path) != expected_hash:
        raise OCRBenchmarkError(f"OCR bundle {label} hash changed")
    return path


def package_ocr_development_bundle(
    *, manifest_path: Path, output_path: Path, repository_root: Path
) -> str:
    """Write one deterministic, POSIX-member private ZIP and return its SHA-256."""

    _require_private_path(manifest_path, repository_root, "OCR development manifest")
    _require_private_path(output_path, repository_root, "OCR development archive")
    if output_path.suffix.casefold() != ".zip":
        raise OCRBenchmarkError("OCR development archive must use a .zip extension")
    root = manifest_path.parent.resolve()
    records = (
        *load_ocr_development_bundle(manifest_path, partition="train"),
        *load_ocr_development_bundle(manifest_path, partition="validation"),
    )
    members: dict[str, Path] = {"development-manifest.json": manifest_path.resolve()}
    for record in records:
        for field, hash_field, label in (
            ("image_path", "image_sha256", "image"),
            ("truth_path", "truth_sha256", "truth"),
        ):
            relative = record.get(field)
            if not isinstance(relative, str) or "\\" in relative:
                raise OCRBenchmarkError("OCR development archive member must use POSIX separators")
            path = _resolve_bundle_file(root, relative, record.get(hash_field), label)
            if relative in members:
                raise OCRBenchmarkError("OCR development archive member is duplicated")
            members[relative] = path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent, delete=False
        ) as handle:
            temporary_path = Path(handle.name)
        with zipfile.ZipFile(
            temporary_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, path in sorted(members.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        os.replace(temporary_path, output_path)
        temporary_path = None
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise OCRBenchmarkError("unable to package OCR development archive") from exc
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return _sha256_file(output_path)


def _truth_boxes(truth: Mapping[str, object]) -> tuple[tuple[int, int, int, int], ...]:
    fields = truth.get("fields")
    if not isinstance(fields, list):
        return ()
    boxes: list[tuple[int, int, int, int]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        bbox = field.get("bbox")
        if (
            isinstance(bbox, list)
            and len(bbox) == 4
            and all(isinstance(value, int) and not isinstance(value, bool) for value in bbox)
        ):
            boxes.append(cast(tuple[int, int, int, int], tuple(bbox)))
    return tuple(boxes)


def run_ocr_parser_ceiling_diagnostic(
    *,
    development_manifest_path: Path,
    output_path: Path,
    repository_root: Path,
    implementation_commit_sha: str,
    now: datetime | None = None,
) -> Path:
    """Measure parser performance on verified transcripts without persisting private values."""

    if (
        not isinstance(implementation_commit_sha, str)
        or _COMMIT_SHA.fullmatch(implementation_commit_sha) is None
    ):
        raise OCRBenchmarkError("OCR parser ceiling implementation identity is invalid")
    _require_private_path(development_manifest_path, repository_root, "development manifest")
    _require_private_path(output_path, repository_root, "OCR parser ceiling report")
    if now is not None and now.tzinfo is None:
        raise OCRBenchmarkError("OCR parser ceiling clock must be timezone-aware")
    development_manifest = _load_object(development_manifest_path)
    development_manifest_sha256 = development_manifest.get("manifest_sha256")
    source_split_manifest_sha256 = development_manifest.get("source_split_manifest_sha256")
    if (
        not isinstance(development_manifest_sha256, str)
        or _SHA256.fullmatch(development_manifest_sha256) is None
        or development_manifest_sha256 != _canonical_hash(development_manifest, "manifest_sha256")
        or not isinstance(source_split_manifest_sha256, str)
        or _SHA256.fullmatch(source_split_manifest_sha256) is None
    ):
        raise OCRBenchmarkError("OCR parser ceiling development identity is invalid")
    root = development_manifest_path.parent.resolve()
    records = load_ocr_development_bundle(development_manifest_path, partition="validation")
    if not records:
        raise OCRBenchmarkError("OCR parser ceiling has no validation records")
    matches_by_field: dict[str, list[bool]] = {field: [] for field in FIELD_WEIGHTS}
    outcomes_by_field: dict[str, dict[str, int]] = {
        field: {"exact": 0, "mismatch": 0, "unavailable": 0} for field in FIELD_WEIGHTS
    }
    parser_warning_counts: dict[str, int] = {}
    parser_warning_counts_by_observed_field: dict[str, dict[str, int]] = {}
    recipient_truth_subtype_counts = {
        "recipient_name_truth": 0,
        "recipient_wallet_truth": 0,
    }
    recipient_secondary_truth_present_count = 0
    amount_candidate_pool_presence = {
        "labelled_nonempty": 0,
        "currency_nonempty": 0,
        "both_nonempty": 0,
        "labelled_active": 0,
        "currency_fallback_active": 0,
    }
    amount_candidate_count_buckets = {
        pool: {bucket: 0 for bucket in _COUNT_BUCKETS}
        for pool in ("labelled", "currency", "active")
    }
    amount_mismatch_attribution_counts = {
        category: 0 for category in _AMOUNT_ATTRIBUTION_CATEGORIES
    }
    text_mismatch_attribution_counts = {
        field: {category: 0 for category in _TEXT_ATTRIBUTION_CATEGORIES}
        for field in ("recipient", "reference")
    }
    timestamp_mismatch_attribution_counts = {"deferred_insufficient_support": 0}
    required_matches: list[bool] = []
    inconclusive: list[bool] = []
    for record in records:
        truth_path = _resolve_bundle_file(
            root, record.get("truth_path"), record.get("truth_sha256"), "truth"
        )
        truth = _load_object(truth_path)
        transcript = truth.get("full_transcript")
        if truth.get("record_id") != record.get("record_id") or not isinstance(transcript, str):
            raise OCRBenchmarkError("OCR validation truth record is invalid")
        parser = parse_momo_text(
            transcript,
            now=now or datetime.now(UTC),
        )
        comparisons = compare_parser_result(parser, truth)
        amount_comparison = comparisons["amount"]
        if amount_comparison is not None:
            snapshot = _amount_candidate_snapshot(transcript)
            labelled = snapshot.labelled_distinct_normalized
            currency = snapshot.currency_distinct_normalized
            active = snapshot.active_distinct_normalized
            if labelled:
                amount_candidate_pool_presence["labelled_nonempty"] += 1
            if currency:
                amount_candidate_pool_presence["currency_nonempty"] += 1
            if labelled and currency:
                amount_candidate_pool_presence["both_nonempty"] += 1
            if snapshot.active_source == "labelled":
                amount_candidate_pool_presence["labelled_active"] += 1
            else:
                amount_candidate_pool_presence["currency_fallback_active"] += 1
            for pool, candidates in (
                ("labelled", labelled),
                ("currency", currency),
                ("active", active),
            ):
                amount_candidate_count_buckets[pool][_candidate_count_bucket(candidates)] += 1
            attribution = _classify_amount_attribution(amount_comparison, snapshot)
            amount_mismatch_attribution_counts[attribution] += 1
        for field in FIELD_WEIGHTS:
            for warning in parser.fields[field].warnings:
                if _PARSER_WARNING_CODE.fullmatch(warning) is None:
                    raise OCRBenchmarkError("OCR parser warning code is invalid")
                parser_warning_counts[warning] = parser_warning_counts.get(warning, 0) + 1
        field_matches = {
            field: None if comparison is None else comparison.matched
            for field, comparison in comparisons.items()
        }
        for field, comparison in comparisons.items():
            if comparison is None:
                continue
            if field == "recipient":
                truth_present = _recipient_truth_present(comparison, transcript)
                attribution = _classify_text_attribution(
                    comparison,
                    truth_present=truth_present,
                )
                text_mismatch_attribution_counts["recipient"][attribution] += 1
            elif field == "reference":
                attribution = _classify_text_attribution(
                    comparison,
                    truth_present=(
                        comparison.expected_normalized in _reference_like_spans(transcript)
                    ),
                )
                text_mismatch_attribution_counts["reference"][attribution] += 1
            elif field == "timestamp":
                timestamp_mismatch_attribution_counts["deferred_insufficient_support"] += 1
            matches_by_field[field].append(comparison.matched)
            if comparison.matched:
                outcomes_by_field[field]["exact"] += 1
            elif not comparison.available:
                outcomes_by_field[field]["unavailable"] += 1
            else:
                outcomes_by_field[field]["mismatch"] += 1
            for warning in comparison.warnings:
                if _PARSER_WARNING_CODE.fullmatch(warning) is None:
                    raise OCRBenchmarkError("OCR parser warning code is invalid")
                observed_counts = parser_warning_counts_by_observed_field.setdefault(
                    comparison.observed_field, {}
                )
                observed_counts[warning] = observed_counts.get(warning, 0) + 1
            if comparison.truth_subtype is not None:
                if comparison.truth_subtype not in recipient_truth_subtype_counts:
                    raise OCRBenchmarkError("OCR recipient truth subtype is invalid")
                recipient_truth_subtype_counts[comparison.truth_subtype] += 1
            if comparison.secondary_truth_present:
                recipient_secondary_truth_present_count += 1
        if all(value is not None for value in field_matches.values()):
            required_matches.append(all(value is True for value in field_matches.values()))
        inconclusive.append(parser.inconclusive)
    for field, matches in matches_by_field.items():
        if sum(outcomes_by_field[field].values()) != len(matches):
            raise OCRBenchmarkError(f"OCR field outcome total is invalid for {field}")
    if sum(recipient_truth_subtype_counts.values()) != len(matches_by_field["recipient"]):
        raise OCRBenchmarkError("OCR recipient truth subtype total is invalid")
    amount_scored_count = len(matches_by_field["amount"])
    if sum(amount_mismatch_attribution_counts.values()) != amount_scored_count:
        raise OCRBenchmarkError("OCR amount attribution total is invalid")
    for field, counts in text_mismatch_attribution_counts.items():
        if sum(counts.values()) != len(matches_by_field[field]):
            raise OCRBenchmarkError(f"OCR text attribution total is invalid for {field}")
    if sum(timestamp_mismatch_attribution_counts.values()) != len(matches_by_field["timestamp"]):
        raise OCRBenchmarkError("OCR timestamp attribution total is invalid")
    if any(
        sum(buckets.values()) != amount_scored_count
        for buckets in amount_candidate_count_buckets.values()
    ):
        raise OCRBenchmarkError("OCR amount candidate bucket total is invalid")
    if (
        amount_candidate_pool_presence["both_nonempty"]
        > amount_candidate_pool_presence["labelled_nonempty"]
        or amount_candidate_pool_presence["both_nonempty"]
        > amount_candidate_pool_presence["currency_nonempty"]
        or (
            amount_candidate_pool_presence["labelled_active"]
            + amount_candidate_pool_presence["currency_fallback_active"]
            != amount_scored_count
        )
    ):
        raise OCRBenchmarkError("OCR amount candidate presence total is invalid")
    report: dict[str, object] = {
        "schema_version": OCR_PARSER_CEILING_REPORT_VERSION,
        "diagnostic_contract_version": OCR_MISMATCH_ATTRIBUTION_VERSION,
        "benchmark_version": OCR_BENCHMARK_VERSION,
        "parser_version": OCR_PARSER_VERSION,
        "field_schema_version": OCR_FIELD_SCHEMA_VERSION,
        "implementation_commit_sha": implementation_commit_sha,
        "development_manifest_sha256": development_manifest_sha256,
        "source_split_manifest_sha256": source_split_manifest_sha256,
        "partition": "validation",
        "record_count": len(records),
        "field_scored_record_count": {
            field: len(values) for field, values in matches_by_field.items()
        },
        "field_exact": {
            field: statistics.fmean(values) if values else None
            for field, values in matches_by_field.items()
        },
        "field_outcome_counts": outcomes_by_field,
        "parser_warning_counts": dict(sorted(parser_warning_counts.items())),
        "parser_warning_counts_by_observed_field": {
            field: dict(sorted(counts.items()))
            for field, counts in sorted(parser_warning_counts_by_observed_field.items())
        },
        "recipient_truth_subtype_counts": recipient_truth_subtype_counts,
        "recipient_secondary_truth_present_count": (recipient_secondary_truth_present_count),
        "amount_candidate_pool_presence": amount_candidate_pool_presence,
        "amount_candidate_count_buckets": amount_candidate_count_buckets,
        "mismatch_attribution_counts": {
            "amount": amount_mismatch_attribution_counts,
            "recipient": text_mismatch_attribution_counts["recipient"],
            "reference": text_mismatch_attribution_counts["reference"],
            "timestamp": timestamp_mismatch_attribution_counts,
        },
        "required_field_scored_record_count": len(required_matches),
        "required_field_parse_success": (
            statistics.fmean(required_matches) if required_matches else None
        ),
        "parser_inconclusive_rate": statistics.fmean(inconclusive),
        "raw_text_persisted": False,
        "field_values_persisted": False,
        "record_identifiers_persisted": False,
        "locked_test_accessed": False,
        "training_executed": False,
    }
    _validate_parser_ceiling_report(report)
    report["report_sha256"] = _canonical_hash(report, "report_sha256")
    _write_json(output_path, report)
    return output_path


def _engine_version_satisfies_policy(engine: str, version: str) -> bool:
    required_major = REQUIRED_ENGINE_MAJOR_VERSIONS.get(engine)
    if required_major is None:
        return bool(version.strip())
    match = re.match(r"\s*(\d+)", version)
    return match is not None and int(match.group(1)) == required_major


def run_ocr_validation_benchmark(
    *,
    development_manifest_path: Path,
    configurations: Sequence[OCRConfiguration],
    adapters: Mapping[str, OCRAdapter],
    output_path: Path,
    repository_root: Path,
    now: datetime | None = None,
    source_group_limit: int | None = None,
) -> Path:
    """Benchmark validation only and persist a redacted, machine-readable private report."""

    _require_private_path(development_manifest_path, repository_root, "development manifest")
    _require_private_path(output_path, repository_root, "OCR benchmark report")
    if not configurations:
        raise OCRBenchmarkError("OCR benchmark requires at least one configuration")
    configured_engines = {config.engine for config in configurations}
    if configured_engines != set(REQUIRED_ENGINES):
        raise OCRBenchmarkError("OCR benchmark must configure every required engine")
    if now is not None and now.tzinfo is None:
        raise OCRBenchmarkError("OCR benchmark clock must be timezone-aware")
    if source_group_limit is not None and (
        isinstance(source_group_limit, bool) or source_group_limit < 1
    ):
        raise OCRBenchmarkError("OCR screening group limit must be a positive integer")
    root = development_manifest_path.parent.resolve()
    records = load_ocr_development_bundle(development_manifest_path, partition="validation")
    if not records:
        raise OCRBenchmarkError("OCR benchmark has no validation records")
    all_group_ids = sorted({cast(str, record.get("source_group_id")) for record in records})
    if source_group_limit is not None:
        selected_groups = set(all_group_ids[:source_group_limit])
        records = tuple(
            record for record in records if record.get("source_group_id") in selected_groups
        )
    if len({config.configuration_id for config in configurations}) != len(configurations):
        raise OCRBenchmarkError("OCR benchmark configurations are duplicated")
    rows_by_configuration: dict[str, list[dict[str, object]]] = {
        config.configuration_id: [] for config in configurations
    }
    failures: list[dict[str, str]] = []
    group_ids: set[str] = set()
    engine_versions: dict[str, set[str]] = {engine: set() for engine in REQUIRED_ENGINES}
    for record in records:
        record_id = record.get("record_id")
        group_id = record.get("source_group_id")
        if not isinstance(record_id, str) or not isinstance(group_id, str):
            raise OCRBenchmarkError("OCR validation record identifiers are invalid")
        group_ids.add(group_id)
        image_path = _resolve_bundle_file(
            root, record.get("image_path"), record.get("image_sha256"), "image"
        )
        truth_path = _resolve_bundle_file(
            root, record.get("truth_path"), record.get("truth_sha256"), "truth"
        )
        truth = _load_object(truth_path)
        transcript = truth.get("full_transcript")
        if truth.get("record_id") != record_id or not isinstance(transcript, str):
            raise OCRBenchmarkError("OCR validation truth record is invalid")
        variants = preprocessing_variants(image_path.read_bytes(), field_boxes=_truth_boxes(truth))
        for config in configurations:
            adapter = adapters.get(config.engine)
            if adapter is None or adapter.engine != config.engine:
                failures.append(
                    {
                        "record_id": record_id,
                        "configuration_id": config.configuration_id,
                        "engine": config.engine,
                        "reason_code": "OCR_ENGINE_UNAVAILABLE",
                    }
                )
                continue
            image = variants.get(config.variant)
            if image is None:
                failures.append(
                    {
                        "record_id": record_id,
                        "configuration_id": config.configuration_id,
                        "engine": config.engine,
                        "reason_code": "OCR_PREPROCESSING_VARIANT_UNAVAILABLE",
                    }
                )
                continue
            try:
                result = adapter.extract(image, configuration=config.configuration_id)
            except OCRAdapterError as exc:
                failures.append(
                    {
                        "record_id": record_id,
                        "configuration_id": config.configuration_id,
                        "engine": config.engine,
                        "reason_code": exc.reason_code,
                    }
                )
                continue
            except OCRBenchmarkError:
                failures.append(
                    {
                        "record_id": record_id,
                        "configuration_id": config.configuration_id,
                        "engine": config.engine,
                        "reason_code": "OCR_ENGINE_FAILED",
                    }
                )
                continue
            if (
                result.engine != config.engine
                or result.schema_version != OCR_ADAPTER_SCHEMA_VERSION
            ):
                raise OCRBenchmarkError("OCR adapter result contract drifted")
            engine_versions.setdefault(config.engine, set()).add(result.engine_version)
            if not _engine_version_satisfies_policy(config.engine, result.engine_version):
                failures.append(
                    {
                        "record_id": record_id,
                        "configuration_id": config.configuration_id,
                        "engine": config.engine,
                        "reason_code": "OCR_ENGINE_VERSION_UNSUPPORTED",
                    }
                )
                continue
            parser = parse_momo_text(
                result.raw_text,
                engine_confidence=result.text_confidence,
                now=now or datetime.now(UTC),
            )
            cer, wer = text_error_rates(transcript, result.raw_text)
            rows_by_configuration[config.configuration_id].append(
                {
                    "record_id": record_id,
                    "source_group_id": group_id,
                    "field_matches": score_parser_result(parser, truth),
                    "cer": cer,
                    "wer": wer,
                    "latency_ms": result.latency_ms,
                    "parser_inconclusive": parser.inconclusive,
                    "semantic_reason_codes": list(parser.semantic_reason_codes),
                }
            )
    configuration_reports: list[dict[str, object]] = []
    for config in configurations:
        config_rows = rows_by_configuration[config.configuration_id]
        metrics = aggregate_configuration_metrics(config_rows) if config_rows else None
        failure_count = sum(
            failure["configuration_id"] == config.configuration_id for failure in failures
        )
        record_coverage = len(config_rows) / len(records)
        configuration_reports.append(
            {
                "configuration_id": config.configuration_id,
                "engine": config.engine,
                "variant": config.variant,
                "engine_options": dict(sorted(config.engine_options.items())),
                "engine_versions": sorted(engine_versions.get(config.engine, set())),
                "metrics": metrics,
                "successful_record_count": len(config_rows),
                "failure_count": failure_count,
                "record_coverage": round(record_coverage, 6),
                "coverage_complete": len(config_rows) == len(records) and failure_count == 0,
            }
        )
    engine_status = {
        engine: {
            "measured": any(
                report["engine"] == engine and report["successful_record_count"]
                for report in configuration_reports
            ),
            "versions": sorted(engine_versions.get(engine, set())),
            "required_major_version": REQUIRED_ENGINE_MAJOR_VERSIONS.get(engine),
            "required_version_satisfied": bool(engine_versions.get(engine))
            and all(
                _engine_version_satisfies_policy(engine, version)
                for version in engine_versions.get(engine, set())
            ),
            "incompatibility_documented": any(failure["engine"] == engine for failure in failures),
        }
        for engine in REQUIRED_ENGINES
    }
    comparison_complete = all(
        engine_status[engine]["required_version_satisfied"] is True
        and any(
            report["engine"] == engine and report["coverage_complete"] is True
            for report in configuration_reports
        )
        for engine in REQUIRED_ENGINES
    )
    development_manifest = _load_object(development_manifest_path)
    report: dict[str, object] = {
        "schema_version": OCR_BENCHMARK_REPORT_VERSION,
        "benchmark_version": OCR_BENCHMARK_VERSION,
        "development_manifest_sha256": development_manifest.get("manifest_sha256"),
        "partition": "validation",
        "stage": "screen" if source_group_limit is not None else "full",
        "selection_eligible": source_group_limit is None and comparison_complete,
        "comparison_complete": comparison_complete,
        "complete_record_coverage_required": True,
        "controlled_real_primary": True,
        "record_count": len(records),
        "source_group_count": len(group_ids),
        "available_source_group_count": len(all_group_ids),
        "configurations": configuration_reports,
        "engine_status": engine_status,
        "failures": failures,
        "raw_text_persisted": False,
        "locked_test_accessed": False,
        "training_executed": False,
        "tampered_derivative_slice_available": False,
        "limitations": [
            "No approved tampered image derivatives were available for PR17 validation.",
            "The controlled-real validation corpus is small and source-group imbalanced.",
        ],
    }
    report["report_sha256"] = _canonical_hash(report, "report_sha256")
    _write_json(output_path, report)
    return output_path


def select_engine_finalists(report_path: Path) -> tuple[OCRConfiguration, ...]:
    """Select one deterministic screen finalist per required engine for the full pass."""

    report = _load_object(report_path)
    if (
        report.get("schema_version") != OCR_BENCHMARK_REPORT_VERSION
        or report.get("stage") != "screen"
        or report.get("selection_eligible") is not False
        or report.get("locked_test_accessed") is not False
        or report.get("report_sha256") != _canonical_hash(report, "report_sha256")
    ):
        raise OCRBenchmarkError("OCR screen report identity or boundary is invalid")
    configurations = report.get("configurations")
    if not isinstance(configurations, list):
        raise OCRBenchmarkError("OCR screen configurations are invalid")
    finalists: list[OCRConfiguration] = []
    for engine in REQUIRED_ENGINES:
        candidates = [
            config
            for config in configurations
            if isinstance(config, dict)
            and config.get("engine") == engine
            and config.get("coverage_complete") is True
            and isinstance(config.get("metrics"), dict)
        ]
        if not candidates:
            raise OCRBenchmarkError(
                "OCR screen has no complete-coverage candidate for a required engine"
            )

        def rank(config: dict[str, object]) -> tuple[float, float, str]:
            metrics = config.get("metrics")
            if not isinstance(metrics, dict):
                return (-1.0, float("-inf"), cast(str, config["configuration_id"]))
            return (
                float(bool(metrics.get("all_release_gates_passed"))),
                float(cast(float | int, metrics["weighted_selection_score"])),
                cast(str, config["configuration_id"]),
            )

        selected = max(candidates, key=rank)
        options = selected.get("engine_options")
        if not isinstance(options, dict):
            raise OCRBenchmarkError("OCR screen engine options are invalid")
        finalists.append(
            OCRConfiguration(
                engine,
                cast(str, selected.get("variant")),
                cast(dict[str, object], options),
            )
        )
    return tuple(finalists)


def select_ocr_configuration(
    *, report_path: Path, output_path: Path, repository_root: Path
) -> Path:
    """Select a validation candidate, marking failed release gates experimental."""

    _require_private_path(report_path, repository_root, "OCR benchmark report")
    _require_private_path(output_path, repository_root, "selected OCR bundle")
    report = _load_object(report_path)
    if (
        report.get("schema_version") != OCR_BENCHMARK_REPORT_VERSION
        or report.get("partition") != "validation"
        or report.get("stage") != "full"
        or report.get("selection_eligible") is not True
        or report.get("locked_test_accessed") is not False
        or report.get("training_executed") is not False
        or report.get("report_sha256") != _canonical_hash(report, "report_sha256")
    ):
        raise OCRBenchmarkError("OCR benchmark report identity or boundary is invalid")
    configurations = report.get("configurations")
    if not isinstance(configurations, list):
        raise OCRBenchmarkError("OCR benchmark configurations are invalid")
    eligible = [
        config
        for config in configurations
        if isinstance(config, dict)
        and config.get("coverage_complete") is True
        and isinstance(config.get("metrics"), dict)
    ]
    if not eligible:
        raise OCRBenchmarkError("OCR benchmark produced no selectable configuration")
    simplicity = {"tesseract": 2, "easyocr": 1, "paddleocr": 0}

    def rank(config: dict[str, object]) -> tuple[float, float, float, int, str]:
        metrics = cast(dict[str, object], config["metrics"])
        fields = cast(dict[str, float | None], metrics["field_exact"])
        critical = (fields.get("amount") or 0.0) + (fields.get("reference") or 0.0)
        return (
            float(bool(metrics.get("all_release_gates_passed"))),
            float(cast(float | int, metrics["weighted_selection_score"])),
            critical,
            simplicity.get(cast(str, config.get("engine")), -1),
            cast(str, config.get("configuration_id")),
        )

    selected = max(eligible, key=rank)
    metrics = cast(dict[str, object], selected["metrics"])
    bundle: dict[str, object] = {
        "schema_version": OCR_SELECTED_BUNDLE_VERSION,
        "benchmark_version": OCR_BENCHMARK_VERSION,
        "source_report_schema_version": report["schema_version"],
        "source_report_sha256": report["report_sha256"],
        "comparison_complete": report["comparison_complete"],
        "coverage_complete": selected["coverage_complete"],
        "record_coverage": selected["record_coverage"],
        "validation_record_count": report["record_count"],
        "status": "validated" if metrics["all_release_gates_passed"] is True else "experimental",
        "configuration_id": selected["configuration_id"],
        "engine": selected["engine"],
        "engine_versions": selected["engine_versions"],
        "variant": selected["variant"],
        "engine_options": selected["engine_options"],
        "parser_version": OCR_PARSER_VERSION,
        "field_schema_version": OCR_FIELD_SCHEMA_VERSION,
        "field_confidence_threshold": FIELD_CONFIDENCE_THRESHOLD,
        "validation_metrics": metrics,
        "locked_test_accessed": False,
        "promotable": metrics["all_release_gates_passed"] is True,
        "training_executed": False,
    }
    bundle["bundle_sha256"] = _canonical_hash(bundle, "bundle_sha256")
    _write_json(output_path, bundle)
    return output_path


def load_selected_ocr_bundle(path: Path) -> dict[str, object]:
    """Verify selected bundle integrity and parser compatibility for replay."""

    bundle = _load_object(path)
    validation_record_count = bundle.get("validation_record_count")
    if (
        bundle.get("schema_version") != OCR_SELECTED_BUNDLE_VERSION
        or bundle.get("source_report_schema_version") != OCR_BENCHMARK_REPORT_VERSION
        or bundle.get("parser_version") != OCR_PARSER_VERSION
        or bundle.get("field_schema_version") != OCR_FIELD_SCHEMA_VERSION
        or bundle.get("comparison_complete") is not True
        or bundle.get("coverage_complete") is not True
        or bundle.get("record_coverage") != 1.0
        or isinstance(validation_record_count, bool)
        or not isinstance(validation_record_count, int)
        or validation_record_count <= 0
        or bundle.get("locked_test_accessed") is not False
        or bundle.get("training_executed") is not False
        or bundle.get("bundle_sha256") != _canonical_hash(bundle, "bundle_sha256")
    ):
        raise OCRBenchmarkError("selected OCR bundle identity or compatibility is invalid")
    return bundle


def replay_parser_bundle(
    bundle_path: Path, text: str, *, engine_confidence: float, now: datetime
) -> ParserResult:
    """Replay the frozen parser contract for parity tests without logging raw text."""

    bundle = load_selected_ocr_bundle(bundle_path)
    if bundle.get("field_confidence_threshold") != FIELD_CONFIDENCE_THRESHOLD:
        raise OCRBenchmarkError("selected OCR bundle threshold is incompatible")
    return parse_momo_text(text, engine_confidence=engine_confidence, now=now)


def safe_failure_result(
    *, engine: str, engine_version: str, configuration: str, reason_code: str
) -> dict[str, object]:
    """Return explicit unavailable fields without raw text or a fake OCR success."""

    return {
        "schema_version": OCR_ADAPTER_SCHEMA_VERSION,
        "engine": engine,
        "engine_version": engine_version,
        "configuration": configuration,
        "available": False,
        "fields": {field: None for field in CRITICAL_FIELDS},
        "warnings": [reason_code],
        "inconclusive": True,
    }
