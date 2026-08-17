"""Versioned OCR preprocessing, extraction and immutable review evidence."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import statistics
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, cast

import cv2
import numpy as np
import pytesseract
from dateutil import parser as date_parser
from flask import current_app
from PIL import Image, ImageOps
from PIL import __version__ as pillow_version
from pytesseract import Output
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    IdempotencyRecord,
    OCRConfirmation,
    OCRResult,
    ReceiptDerivative,
    ReceiptTemplate,
    Transaction,
    User,
)
from momo_fdvs.services.audit import audit_event
from momo_fdvs.services.text_fraud import (
    TEXT_FRAUD_RULESET_VERSION,
    TEXT_FRAUD_SCHEMA_VERSION,
    TextFraudContext,
    assess_ocr_text,
    confidence_from_ocr_tokens,
)
from momo_fdvs.storage.base import ObjectStorage, generated_key, sha256_bytes

cv2.setNumThreads(1)

PIPELINE_VARIANTS = (
    "BASE_RESIZED",
    "GRAY_CLAHE",
    "DENOISE_SHARPEN",
    "OTSU_BINARY",
    "ADAPTIVE_BINARY",
)
REQUIRED_FIELDS = ("transaction_reference", "amount", "currency", "occurred_at")
FIELD_NAMES = (
    "provider_code",
    "transaction_reference",
    "amount",
    "currency",
    "sender_name",
    "sender_phone",
    "receiver_name",
    "receiver_phone",
    "occurred_at",
    "status_text",
)
PROVIDER_ANCHORS = {
    "MTN_MOMO": ("MTN", "MOMO"),
    "TELECEL_CASH": ("TELECEL", "CASH"),
    "AIRTELTIGO_MONEY": ("AIRTELTIGO", "MONEY"),
    "GENERIC_MOMO": ("MOBILE MONEY",),
}


class OCRFailure(RuntimeError):
    """A safe, intentionally public OCR workflow failure."""

    def __init__(
        self,
        code: str,
        message: str,
        status: int,
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.field_errors = field_errors


@dataclass(frozen=True)
class OCRCandidate:
    variant: str
    psm: int
    raw_text: str
    tokens: list[dict[str, Any]]
    fields: dict[str, dict[str, Any]]
    provider: dict[str, Any]
    mean_confidence: float
    median_confidence: float
    required_coverage: float
    score: float


@dataclass(frozen=True)
class OCRPipelineResult:
    engine_version: str
    selected_variant: str
    selected_image: bytes
    raw_text: str
    tokens: list[dict[str, Any]]
    fields: dict[str, dict[str, Any]]
    provider: dict[str, Any]
    warnings: list[str]
    candidate_summary: list[dict[str, Any]]
    quality_features: dict[str, Any]
    partial: bool
    fraud_preview: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRRunResult:
    transaction: Transaction
    ocr_result: OCRResult
    replayed: bool
    partial: bool


@dataclass(frozen=True)
class ConfirmationResult:
    transaction: Transaction
    confirmation: OCRConfirmation
    replayed: bool


def _normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def normalize_reference(value: str) -> str | None:
    candidate = re.sub(r"\s+", "", _normalized_text(value)).upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{5,49}", candidate):
        return None
    return candidate


def normalize_amount(value: str) -> str | None:
    candidate = re.sub(r"[^0-9.,-]", "", _normalized_text(value)).replace(",", "")
    try:
        amount = Decimal(candidate)
    except (InvalidOperation, ValueError):
        return None
    if amount < 0 or amount > Decimal("999999999.99"):
        return None
    return f"{amount.quantize(Decimal('0.01')):.2f}"


def normalize_phone(value: str) -> str | None:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("233") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+233{digits[1:]}"
    if len(digits) == 9 and digits.startswith(("2", "5")):
        return f"+233{digits}"
    return None


def mask_phone(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:7]} *** {value[-4:]}"


def normalize_name(value: str) -> str | None:
    candidate = _normalized_text(value).strip(" :-")
    if not candidate or len(candidate) > 150 or not re.search(r"[A-Za-z]", candidate):
        return None
    return candidate.upper()


def normalize_occurred_at(value: str) -> tuple[str | None, list[str]]:
    candidate = _normalized_text(value)
    if not candidate:
        return None, []
    parsed: datetime | None = None
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",
    )
    for date_format in formats:
        try:
            parsed = datetime.strptime(candidate, date_format)
            break
        except ValueError:
            continue
    if parsed is None:
        try:
            parsed = date_parser.isoparse(candidate)
        except (ValueError, OverflowError):
            return None, ["DATE_TIME_INVALID"]
    warnings: list[str] = []
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
        warnings.append("TIMEZONE_INFERRED_GHANA_UTC")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z"), warnings


def _token_ids_for_value(tokens: list[dict[str, Any]], raw_value: str) -> list[int]:
    pieces = {
        re.sub(r"[^A-Z0-9]", "", part.upper())
        for part in raw_value.split()
        if re.sub(r"[^A-Z0-9]", "", part.upper())
    }
    return [
        int(token["id"])
        for token in tokens
        if re.sub(r"[^A-Z0-9]", "", str(token["text"]).upper()) in pieces
    ]


def _source_confidence(tokens: list[dict[str, Any]], token_ids: list[int]) -> float:
    values = [
        float(tokens[index]["confidence"]) / 100 for index in token_ids if index < len(tokens)
    ]
    return sum(values) / len(values) if values else 0.45


def _field(
    *,
    raw_value: str | None,
    value: str | None,
    tokens: list[dict[str, Any]],
    threshold: float,
    validation_warnings: list[str] | None = None,
    confidence_bonus: float = 0.1,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    token_ids = _token_ids_for_value(tokens, raw_value or "")
    valid = value is not None
    confidence = min(
        1.0, _source_confidence(tokens, token_ids) + (confidence_bonus if valid else 0)
    )
    warnings = list(validation_warnings or [])
    if raw_value and not valid:
        warnings.append("FIELD_FORMAT_INVALID")
    if not raw_value:
        warnings.append("FIELD_NOT_FOUND")
    result: dict[str, Any] = {
        "raw_value": raw_value,
        "value": value,
        "confidence": round(confidence, 4) if raw_value else 0.0,
        "valid": valid,
        "requires_review": not valid or confidence < threshold,
        "source_token_ids": token_ids,
        "warnings": warnings,
    }
    result.update(extra or {})
    return result


def _first_match(patterns: tuple[str, ...], text: str, group: int = 1) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return _normalized_text(match.group(group))
    return None


def detect_provider(raw_text: str) -> dict[str, Any]:
    upper = raw_text.upper()
    best_code = "GENERIC_MOMO"
    best_matches: list[str] = []
    for code, anchors in PROVIDER_ANCHORS.items():
        matches = [anchor for anchor in anchors if anchor in upper]
        if len(matches) > len(best_matches):
            best_code, best_matches = code, matches
    if best_matches:
        confidence = min(0.98, 0.55 + 0.2 * len(best_matches))
        warnings: list[str] = []
    else:
        confidence = 0.35
        warnings = ["UNKNOWN_TEMPLATE_GENERIC_FALLBACK"]
    return {
        "value": best_code,
        "confidence": round(confidence, 4),
        "matched_anchors": best_matches,
        "requires_review": confidence < 0.75,
        "warnings": warnings,
    }


def parse_fields(
    raw_text: str,
    tokens: list[dict[str, Any]],
    review_threshold: float,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    text = unicodedata.normalize("NFKC", raw_text)
    provider = detect_provider(text)
    reference_raw = _first_match(
        (
            r"(?:TRANSACTION\s*(?:ID|REFERENCE)|REFERENCE|REF(?:ERENCE)?)[\s:#-]*([A-Z0-9][A-Z0-9._/-]{5,49})",
        ),
        text,
    )
    amount_raw = _first_match(
        (
            r"(?:AMOUNT|TOTAL|PAID|TRANSFERRED)[^\d\n]{0,24}(?:GH[₵¢S]?\s*)?([0-9][0-9,]*\.\d{2})",
            r"(?:GH[₵¢S]?\s*)([0-9][0-9,]*\.\d{2})",
        ),
        text,
    )
    currency_raw = _first_match((r"\b(GHS|GH[₵¢])\b",), text)
    sender_phone_raw = _first_match(
        (r"(?:SENDER\s*PHONE|FROM\s*PHONE|SENDER\s*MSISDN)[\s:#-]*([+0-9][0-9 +()-]{8,20})",),
        text,
    )
    receiver_phone_raw = _first_match(
        (
            r"(?:RECEIVER\s*PHONE|RECIPIENT\s*PHONE|TO\s*PHONE|RECEIVER\s*MSISDN)"
            r"[\s:#-]*([+0-9][0-9 +()-]{8,20})",
        ),
        text,
    )
    sender_name_raw = _first_match((r"(?:SENDER\s*NAME|FROM\s*NAME)[\s:#-]*([^\n]{2,150})",), text)
    receiver_name_raw = _first_match(
        (r"(?:RECEIVER\s*NAME|RECIPIENT\s*NAME|TO\s*NAME)[\s:#-]*([^\n]{2,150})",),
        text,
    )
    occurred_raw = _first_match(
        (
            r"(?:DATE\s*/?\s*TIME|DATE|TIME)[\s:#-]*"
            r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)",
            r"(?:DATE\s*/?\s*TIME|DATE|TIME)[\s:#-]*(\d{2}[/-]\d{2}[/-]\d{4}\s+\d{2}:\d{2}(?::\d{2})?)",
        ),
        text,
    )
    status_raw = _first_match(
        (r"(?:STATUS)[\s:#-]*(SUCCESSFUL|SUCCESS|COMPLETED|FAILED|PENDING|REVERSED)",),
        text,
    )
    occurred_at, occurred_warnings = normalize_occurred_at(occurred_raw or "")
    currency = "GHS" if currency_raw else ("GHS" if amount_raw else None)
    currency_warnings = [] if currency_raw else (["CURRENCY_INFERRED_GHS"] if amount_raw else [])
    status = status_raw.upper() if status_raw else None
    if status in {"SUCCESS", "COMPLETED"}:
        status = "SUCCESSFUL"

    fields = {
        "provider_code": _field(
            raw_value=" ".join(provider["matched_anchors"]) or None,
            value=provider["value"],
            tokens=tokens,
            threshold=review_threshold,
            validation_warnings=list(provider["warnings"]),
            confidence_bonus=0,
        ),
        "transaction_reference": _field(
            raw_value=reference_raw,
            value=normalize_reference(reference_raw or ""),
            tokens=tokens,
            threshold=review_threshold,
        ),
        "amount": _field(
            raw_value=amount_raw,
            value=normalize_amount(amount_raw or ""),
            tokens=tokens,
            threshold=review_threshold,
            extra={"currency": currency},
        ),
        "currency": _field(
            raw_value=currency_raw,
            value=currency,
            tokens=tokens,
            threshold=review_threshold,
            validation_warnings=currency_warnings,
        ),
        "sender_name": _field(
            raw_value=sender_name_raw,
            value=normalize_name(sender_name_raw or ""),
            tokens=tokens,
            threshold=review_threshold,
        ),
        "sender_phone": _field(
            raw_value=sender_phone_raw,
            value=normalize_phone(sender_phone_raw or ""),
            tokens=tokens,
            threshold=review_threshold,
            extra={"masked": mask_phone(normalize_phone(sender_phone_raw or ""))},
        ),
        "receiver_name": _field(
            raw_value=receiver_name_raw,
            value=normalize_name(receiver_name_raw or ""),
            tokens=tokens,
            threshold=review_threshold,
        ),
        "receiver_phone": _field(
            raw_value=receiver_phone_raw,
            value=normalize_phone(receiver_phone_raw or ""),
            tokens=tokens,
            threshold=review_threshold,
            extra={"masked": mask_phone(normalize_phone(receiver_phone_raw or ""))},
        ),
        "occurred_at": _field(
            raw_value=occurred_raw,
            value=occurred_at,
            tokens=tokens,
            threshold=review_threshold,
            validation_warnings=occurred_warnings,
        ),
        "status_text": _field(
            raw_value=status_raw,
            value=status,
            tokens=tokens,
            threshold=review_threshold,
        ),
    }
    fields["provider_code"]["confidence"] = provider["confidence"]
    fields["provider_code"]["requires_review"] = provider["requires_review"]
    return fields, provider


def _quality_features(gray: np.ndarray) -> dict[str, Any]:
    height, width = gray.shape[:2]
    laplacian_variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    edges = cv2.Canny(gray, 100, 200)
    underexposed = float(np.mean(gray < 20))
    overexposed = float(np.mean(gray > 235))
    return {
        "width_px": width,
        "height_px": height,
        "aspect_ratio": round(width / max(height, 1), 6),
        "grayscale_mean": round(float(np.mean(gray)), 4),
        "grayscale_std": round(float(np.std(gray)), 4),
        "contrast_range": int(np.percentile(gray, 95) - np.percentile(gray, 5)),
        "laplacian_variance": round(laplacian_variance, 4),
        "edge_density": round(float(np.mean(edges > 0)), 6),
        "underexposed_proportion": round(underexposed, 6),
        "overexposed_proportion": round(overexposed, 6),
        "ocr_scale_suitable": width >= 1_000,
    }


def create_preprocessing_variants(content: bytes) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    try:
        with Image.open(io.BytesIO(content)) as source:
            rgb = np.asarray(ImageOps.exif_transpose(source).convert("RGB"))
    except (OSError, ValueError) as exc:
        raise OCRFailure(
            "OCR_IMAGE_DECODE_FAILED", "The stored receipt could not be decoded.", 422
        ) from exc
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    target_width = int(current_app.config["OCR_TARGET_MIN_WIDTH_PX"])
    scale = min(3.0, max(1.0, target_width / max(bgr.shape[1], 1)))
    if scale > 1:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    denoised = cv2.fastNlMeansDenoising(clahe, None, 7, 7, 21)
    sharpened = cv2.addWeighted(denoised, 1.5, cv2.GaussianBlur(denoised, (0, 0), 1.2), -0.5, 0)
    _, otsu = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    adaptive = cv2.adaptiveThreshold(
        clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 11
    )
    variants: dict[str, np.ndarray] = {
        "BASE_RESIZED": bgr,
        "GRAY_CLAHE": clahe,
        "DENOISE_SHARPEN": sharpened,
        "OTSU_BINARY": otsu,
        "ADAPTIVE_BINARY": adaptive,
    }
    inverse = cv2.bitwise_not(otsu)
    coordinates = cv2.findNonZero(inverse)
    deskew_angle: float | None = None
    if coordinates is not None and len(coordinates) >= 100:
        angle = float(cv2.minAreaRect(coordinates)[-1])
        angle = -(90 + angle) if angle < -45 else -angle
        if 1.0 <= abs(angle) <= 15.0:
            center = (clahe.shape[1] / 2, clahe.shape[0] / 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            variants["DESKEWED_CLAHE"] = cv2.warpAffine(
                clahe,
                matrix,
                (clahe.shape[1], clahe.shape[0]),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE,
            )
            deskew_angle = round(angle, 4)
    maximum = int(current_app.config["OCR_MAX_VARIANTS"])
    variants = dict(list(variants.items())[:maximum])
    quality = _quality_features(gray)
    quality.update(
        {
            "orientation_applied": True,
            "resize_scale": round(scale, 4),
            "deskew_angle": deskew_angle,
            "opencv_version": cv2.__version__,
            "pillow_version": pillow_version,
        }
    )
    return variants, quality


def _tokens_from_tesseract(data: dict[str, list[Any]]) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for index, raw_text in enumerate(data.get("text", [])):
        text = _normalized_text(str(raw_text))
        if not text:
            continue
        try:
            confidence = max(0.0, min(100.0, float(data["conf"][index])))
        except (KeyError, ValueError, TypeError, IndexError):
            confidence = 0.0
        token = {
            "id": len(tokens),
            "text": text,
            "confidence": round(confidence, 2),
            "x": int(data["left"][index]),
            "y": int(data["top"][index]),
            "width": int(data["width"][index]),
            "height": int(data["height"][index]),
            "line_id": ":".join(
                str(data[name][index]) for name in ("page_num", "block_num", "par_num", "line_num")
            ),
        }
        tokens.append(token)
    return tokens


def _raw_text(tokens: list[dict[str, Any]]) -> str:
    lines: dict[str, list[str]] = {}
    for token in tokens:
        lines.setdefault(str(token["line_id"]), []).append(str(token["text"]))
    return "\n".join(" ".join(words) for words in lines.values())


def _candidate(variant: str, image: np.ndarray, psm: int, threshold: float) -> OCRCandidate:
    data = cast(
        dict[str, list[Any]],
        pytesseract.image_to_data(
            image,
            lang=current_app.config["TESSERACT_LANG"],
            config=f"--psm {psm}",
            output_type=Output.DICT,
            timeout=current_app.config["TESSERACT_TIMEOUT_SECONDS"],
        ),
    )
    tokens = _tokens_from_tesseract(data)
    raw_text = _raw_text(tokens)
    fields, provider = parse_fields(raw_text, tokens, threshold)
    confidences = [float(token["confidence"]) / 100 for token in tokens]
    mean_confidence = statistics.fmean(confidences) if confidences else 0.0
    median_confidence = statistics.median(confidences) if confidences else 0.0
    required_coverage = sum(bool(fields[name]["valid"]) for name in REQUIRED_FIELDS) / len(
        REQUIRED_FIELDS
    )
    sanity = min(1.0, len(raw_text) / 120) if tokens else 0.0
    score = (
        0.25 * mean_confidence
        + 0.15 * median_confidence
        + 0.45 * required_coverage
        + 0.10 * float(provider["confidence"])
        + 0.05 * sanity
    )
    return OCRCandidate(
        variant=variant,
        psm=psm,
        raw_text=raw_text,
        tokens=tokens,
        fields=fields,
        provider=provider,
        mean_confidence=round(mean_confidence, 4),
        median_confidence=round(median_confidence, 4),
        required_coverage=round(required_coverage, 4),
        score=round(score, 6),
    )


def _encode_png(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not success:
        raise OCRFailure("OCR_DERIVATIVE_FAILED", "The OCR derivative could not be encoded.", 503)
    return bytes(encoded)


def execute_ocr(content: bytes, expected_sha256: str) -> OCRPipelineResult:
    if not hashlib.sha256(content).hexdigest() == expected_sha256:
        raise OCRFailure(
            "OCR_RECEIPT_HASH_MISMATCH",
            "The stored receipt failed its evidence-integrity check.",
            409,
        )
    variants, quality = create_preprocessing_variants(content)
    pytesseract.pytesseract.tesseract_cmd = current_app.config["TESSERACT_CMD"]
    warnings: list[str] = []
    candidates: list[OCRCandidate] = []
    engine_version = "unavailable"
    try:
        if shutil.which(current_app.config["TESSERACT_CMD"]) is None:
            raise pytesseract.TesseractNotFoundError()
        engine_version = str(pytesseract.get_tesseract_version()).splitlines()[0]
        threshold = float(current_app.config["OCR_REVIEW_CONFIDENCE_THRESHOLD"])
        for variant, image in variants.items():
            for psm in (6, 11):
                candidates.append(_candidate(variant, image, psm, threshold))
    except pytesseract.TesseractNotFoundError:
        warnings.append("OCR_ENGINE_UNAVAILABLE")
    except RuntimeError:
        warnings.append("OCR_ENGINE_TIMEOUT")
    except pytesseract.TesseractError:
        warnings.append("OCR_ENGINE_FAILED")

    if candidates:
        winner = max(candidates, key=lambda item: (item.score, item.required_coverage))
        selected_image = variants[winner.variant]
        fields = winner.fields
        provider = winner.provider
        raw_text = winner.raw_text
        tokens = winner.tokens
        selected_variant = winner.variant
        if winner.required_coverage < 1:
            warnings.append("CRITICAL_OCR_FIELDS_MISSING")
        warnings.extend(provider["warnings"])
        partial = winner.required_coverage < 1
    else:
        selected_variant = next(iter(variants))
        selected_image = variants[selected_variant]
        fields, provider = parse_fields(
            "", [], float(current_app.config["OCR_REVIEW_CONFIDENCE_THRESHOLD"])
        )
        raw_text = ""
        tokens = []
        warnings.extend(["CRITICAL_OCR_FIELDS_MISSING", *provider["warnings"]])
        partial = True
    summary = [
        {
            "variant": candidate.variant,
            "psm": candidate.psm,
            "score": candidate.score,
            "mean_confidence": candidate.mean_confidence,
            "median_confidence": candidate.median_confidence,
            "required_field_coverage": candidate.required_coverage,
            "token_count": len(candidate.tokens),
            "provider_code": candidate.provider["value"],
        }
        for candidate in candidates
    ]
    fraud_preview = assess_ocr_text(
        raw_text,
        ocr_confidence=confidence_from_ocr_tokens(tokens),
        context=TextFraudContext(claimed_provider=str(provider["value"])),
    ).as_public_dict()
    return OCRPipelineResult(
        engine_version=engine_version,
        selected_variant=selected_variant,
        selected_image=_encode_png(selected_image),
        raw_text=raw_text,
        tokens=tokens,
        fields=fields,
        provider=provider,
        warnings=list(dict.fromkeys(warnings)),
        candidate_summary=summary,
        quality_features=quality,
        partial=partial,
        fraud_preview=fraud_preview,
    )


def _request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _claim_idempotency(
    user: User, scope: str, key: str, request_hash: str
) -> tuple[IdempotencyRecord, bool]:
    if not 8 <= len(key) <= 200:
        raise OCRFailure(
            "IDEMPOTENCY_KEY_INVALID", "Idempotency-Key must contain 8 to 200 characters.", 400
        )
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    lookup = select(IdempotencyRecord).where(
        IdempotencyRecord.principal_id == user.id,
        IdempotencyRecord.scope == scope,
        IdempotencyRecord.key_hash == key_hash,
    )
    record = db.session.scalar(lookup.with_for_update())
    if record is not None:
        return record, False
    candidate = IdempotencyRecord(
        principal_id=user.id,
        scope=scope,
        key_hash=key_hash,
        request_hash=request_hash,
        expires_at=datetime.now(UTC)
        + timedelta(hours=current_app.config["UPLOAD_IDEMPOTENCY_TTL_HOURS"]),
    )
    try:
        with db.session.begin_nested():
            db.session.add(candidate)
            db.session.flush()
        return candidate, True
    except IntegrityError:
        record = db.session.scalar(lookup.with_for_update())
        if record is None:
            raise
        return record, False


def _resolve_template(provider_code: str) -> ReceiptTemplate | None:
    return db.session.scalar(
        select(ReceiptTemplate)
        .where(
            ReceiptTemplate.provider_code == provider_code,
            ReceiptTemplate.status == "ACTIVE",
        )
        .order_by(ReceiptTemplate.updated_at.desc())
    )


def run_and_store_ocr(
    *,
    transaction: Transaction,
    user: User,
    roles: set[str],
    idempotency_key: str,
    storage: ObjectStorage,
) -> OCRRunResult:
    if transaction.receipt is None:
        raise OCRFailure("RECEIPT_NOT_FOUND", "Receipt not found.", 404)
    if transaction.status not in {"UPLOADED", "OCR_REVIEW", "READY", "FAILED"}:
        raise OCRFailure(
            "OCR_STATE_INVALID", "OCR cannot run in the transaction's current state.", 409
        )
    receipt = transaction.receipt
    request_hash = _request_hash(
        {
            "receipt_sha256": receipt.sha256,
            "pipeline_version": current_app.config["OCR_PIPELINE_VERSION"],
        }
    )
    scope = f"POST:/api/v1/transactions/{transaction.id}/ocr"
    record, claimed = _claim_idempotency(user, scope, idempotency_key, request_hash)
    if not claimed:
        if record.request_hash != request_hash:
            raise OCRFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different request.",
                409,
            )
        if record.resource_type != "ocr_result" or record.resource_id is None:
            raise OCRFailure(
                "IDEMPOTENCY_REQUEST_IN_PROGRESS",
                "The original OCR request is still being processed. Retry shortly.",
                409,
            )
        existing = db.session.get(OCRResult, record.resource_id)
        if existing is None or existing.receipt_id != receipt.id:
            raise OCRFailure(
                "IDEMPOTENCY_RESOURCE_UNAVAILABLE", "The original OCR result is unavailable.", 409
            )
        audit_event(
            "ocr.run_replayed",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="transaction",
            target_id=transaction.id,
        )
        db.session.commit()
        return OCRRunResult(
            transaction=transaction,
            ocr_result=existing,
            replayed=True,
            partial="OCR_ENGINE_UNAVAILABLE" in existing.warnings
            or "CRITICAL_OCR_FIELDS_MISSING" in existing.warnings,
        )

    written_key: str | None = None
    try:
        content = storage.read_bytes(receipt.object_key)
        pipeline = execute_ocr(content, receipt.sha256)
        selected_sha = sha256_bytes(pipeline.selected_image)
        derivative_version = (
            f"{current_app.config['OCR_PIPELINE_VERSION']}:{pipeline.selected_variant}"[:50]
        )
        derivative = db.session.scalar(
            select(ReceiptDerivative).where(
                ReceiptDerivative.receipt_id == receipt.id,
                ReceiptDerivative.kind == "OCR_VARIANT",
                ReceiptDerivative.version == derivative_version,
                ReceiptDerivative.sha256 == selected_sha,
            )
        )
        if derivative is None:
            key = generated_key(
                f"receipts/{transaction.user_id}/{transaction.id}/derived/ocr", "png"
            )
            stored = storage.put_bytes(
                key,
                pipeline.selected_image,
                "image/png",
                {
                    "source-sha256": receipt.sha256,
                    "pipeline-version": current_app.config["OCR_PIPELINE_VERSION"],
                },
            )
            written_key = stored.key
            derivative = ReceiptDerivative(
                receipt_id=receipt.id,
                kind="OCR_VARIANT",
                version=derivative_version,
                object_key=stored.key,
                sha256=selected_sha,
                metadata_json={
                    "media_type": "image/png",
                    "selected_variant": pipeline.selected_variant,
                    "candidate_summary": pipeline.candidate_summary,
                    "quality_features": pipeline.quality_features,
                    "pipeline_version": current_app.config["OCR_PIPELINE_VERSION"],
                    "parser_version": current_app.config["OCR_PARSER_VERSION"],
                    "tesseract_language": current_app.config["TESSERACT_LANG"],
                    "tesseract_psms": [6, 11],
                    "tesseract_timeout_seconds": current_app.config["TESSERACT_TIMEOUT_SECONDS"],
                },
            )
            db.session.add(derivative)

        template = _resolve_template(str(pipeline.provider["value"]))
        field_confidences = {
            name: float(value["confidence"]) for name, value in pipeline.fields.items()
        }
        accuracy_hint = sum(bool(pipeline.fields[name]["valid"]) for name in REQUIRED_FIELDS) / len(
            REQUIRED_FIELDS
        )
        fraud_preview = (
            pipeline.fraud_preview
            or assess_ocr_text(
                pipeline.raw_text,
                ocr_confidence=confidence_from_ocr_tokens(pipeline.tokens),
                context=TextFraudContext(claimed_provider=str(pipeline.provider["value"])),
            ).as_public_dict()
        )
        ocr_result = OCRResult(
            receipt_id=receipt.id,
            template_id=template.id if template else None,
            engine_name="tesseract",
            engine_version=pipeline.engine_version,
            pipeline_version=current_app.config["OCR_PIPELINE_VERSION"],
            selected_variant=pipeline.selected_variant,
            raw_text=pipeline.raw_text,
            token_data=pipeline.tokens,
            extracted_fields={
                **pipeline.fields,
                "_text_fraud": fraud_preview,
                "_evidence": {
                    "parser_version": current_app.config["OCR_PARSER_VERSION"],
                    "field_schema_version": current_app.config["OCR_FIELD_SCHEMA_VERSION"],
                    "template_version": template.version if template else "generic-v1",
                    "text_fraud_schema_version": TEXT_FRAUD_SCHEMA_VERSION,
                    "text_fraud_ruleset_version": TEXT_FRAUD_RULESET_VERSION,
                },
            },
            field_confidences=field_confidences,
            warnings=pipeline.warnings,
            required_field_accuracy_hint=Decimal(f"{accuracy_hint:.4f}"),
        )
        db.session.add(ocr_result)
        db.session.flush()
        transaction.provider_code = str(pipeline.provider["value"])
        transaction.status = "OCR_REVIEW"
        record.resource_type = "ocr_result"
        record.resource_id = ocr_result.id
        record.response_status = 200
        audit_event(
            "ocr.completed" if not pipeline.partial else "ocr.partial",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="transaction",
            target_id=transaction.id,
            metadata={
                "ocr_result_id": str(ocr_result.id),
                "engine_version": pipeline.engine_version,
                "pipeline_version": ocr_result.pipeline_version,
                "selected_variant": pipeline.selected_variant,
                "warning_codes": pipeline.warnings,
                "required_field_coverage": round(accuracy_hint, 4),
                "text_fraud_status": fraud_preview["status"],
                "text_fraud_class": fraud_preview["class"],
                "text_fraud_reason_codes": fraud_preview["reason_codes"],
                "text_fraud_ruleset_version": TEXT_FRAUD_RULESET_VERSION,
            },
        )
        db.session.commit()
        return OCRRunResult(transaction, ocr_result, False, pipeline.partial)
    except OCRFailure:
        db.session.rollback()
        if written_key:
            storage.delete(written_key)
        raise
    except Exception as exc:
        db.session.rollback()
        if written_key:
            try:
                storage.delete(written_key)
            except Exception:
                current_app.logger.exception("ocr_derivative_cleanup_failed")
        current_app.logger.exception("ocr_run_failed", exc_info=exc)
        raise OCRFailure(
            "OCR_PROCESSING_UNAVAILABLE",
            "OCR processing is temporarily unavailable. The original receipt is unchanged.",
            503,
        ) from exc


def latest_ocr_result(transaction: Transaction) -> OCRResult | None:
    if transaction.receipt is None:
        return None
    return db.session.scalar(
        select(OCRResult)
        .where(OCRResult.receipt_id == transaction.receipt.id)
        .order_by(OCRResult.created_at.desc(), OCRResult.id.desc())
    )


def canonicalize_confirmation_fields(
    raw_fields: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, list[str]]]:
    errors: dict[str, list[str]] = {}
    canonical: dict[str, Any] = {}
    provider = _normalized_text(str(raw_fields.get("provider_code", ""))).upper()
    if not re.fullmatch(r"[A-Z0-9_]{2,50}", provider):
        errors["provider_code"] = ["Enter a valid provider code."]
    else:
        canonical["provider_code"] = provider
    reference = normalize_reference(str(raw_fields.get("transaction_reference", "")))
    if reference is None:
        errors["transaction_reference"] = ["Enter a valid transaction reference."]
    else:
        canonical["transaction_reference"] = reference
    amount = normalize_amount(str(raw_fields.get("amount", "")))
    if amount is None:
        errors["amount"] = ["Enter a valid non-negative amount."]
    else:
        canonical["amount"] = amount
    currency = _normalized_text(str(raw_fields.get("currency", ""))).upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        errors["currency"] = ["Enter a three-letter currency code."]
    else:
        canonical["currency"] = currency
    for name in ("sender_name", "receiver_name"):
        raw_value = str(raw_fields.get(name, ""))
        value = normalize_name(raw_value) if raw_value.strip() else None
        if raw_value.strip() and value is None:
            errors[name] = ["Enter a valid name or leave it empty."]
        canonical[name] = value
    for name in ("sender_phone", "receiver_phone"):
        raw_value = str(raw_fields.get(name, ""))
        value = normalize_phone(raw_value) if raw_value.strip() else None
        if raw_value.strip() and value is None:
            errors[name] = ["Enter a valid Ghanaian phone number or leave it empty."]
        canonical[name] = value
    occurred_at, _warnings = normalize_occurred_at(str(raw_fields.get("occurred_at", "")))
    if occurred_at is None:
        errors["occurred_at"] = ["Enter a valid date and time with enough detail."]
    else:
        canonical["occurred_at"] = occurred_at
    status = _normalized_text(str(raw_fields.get("status_text", ""))).upper()
    if status in {"SUCCESS", "COMPLETED"}:
        status = "SUCCESSFUL"
    if not re.fullmatch(r"[A-Z][A-Z _-]{1,49}", status):
        errors["status_text"] = ["Enter the transaction status shown on the receipt."]
    else:
        canonical["status_text"] = status
    return canonical, errors


def confirm_ocr(
    *,
    transaction: Transaction,
    ocr_result: OCRResult,
    user: User,
    roles: set[str],
    raw_fields: dict[str, Any],
    correction_reasons: dict[str, Any],
    idempotency_key: str,
) -> ConfirmationResult:
    if transaction.receipt is None or ocr_result.receipt_id != transaction.receipt.id:
        raise OCRFailure("OCR_RESULT_NOT_FOUND", "OCR result not found.", 404)
    if transaction.status not in {"OCR_REVIEW", "READY"}:
        raise OCRFailure(
            "OCR_REVIEW_STATE_INVALID",
            "This transaction is not ready for OCR confirmation.",
            409,
        )
    canonical, errors = canonicalize_confirmation_fields(raw_fields)
    original = {
        name: cast(dict[str, Any], ocr_result.extracted_fields.get(name, {})).get("value")
        for name in FIELD_NAMES
    }
    corrections: list[dict[str, Any]] = []
    for name in FIELD_NAMES:
        if canonical.get(name) == original.get(name):
            continue
        reason = _normalized_text(str(correction_reasons.get(name, "")))
        if len(reason) < 5 or len(reason) > 300:
            errors.setdefault(name, []).append("Explain this correction in 5 to 300 characters.")
            continue
        corrections.append(
            {
                "field": name,
                "original_value": original.get(name),
                "confirmed_value": canonical.get(name),
                "reason": reason,
                "original_confidence": ocr_result.field_confidences.get(name, 0),
            }
        )
    if errors:
        raise OCRFailure(
            "OCR_CONFIRMATION_INVALID",
            "Review the highlighted OCR fields before confirming.",
            422,
            errors,
        )
    request_hash = _request_hash(
        {
            "ocr_result_id": str(ocr_result.id),
            "fields": canonical,
            "correction_reasons": correction_reasons,
        }
    )
    scope = f"POST:/api/v1/transactions/{transaction.id}/ocr-confirmations"
    record, claimed = _claim_idempotency(user, scope, idempotency_key, request_hash)
    if not claimed:
        if record.request_hash != request_hash:
            raise OCRFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different request.",
                409,
            )
        existing = (
            db.session.get(OCRConfirmation, record.resource_id)
            if record.resource_type == "ocr_confirmation" and record.resource_id
            else None
        )
        if existing is None or existing.transaction_id != transaction.id:
            raise OCRFailure(
                "IDEMPOTENCY_RESOURCE_UNAVAILABLE",
                "The original OCR confirmation is unavailable.",
                409,
            )
        return ConfirmationResult(transaction, existing, True)
    confirmation = OCRConfirmation(
        ocr_result_id=ocr_result.id,
        transaction_id=transaction.id,
        confirmed_fields=canonical,
        corrections=corrections,
        confirmed_by=user.id,
        confirmed_at=datetime.now(UTC),
        schema_version=current_app.config["OCR_FIELD_SCHEMA_VERSION"],
    )
    db.session.add(confirmation)
    db.session.flush()
    transaction.status = "READY"
    transaction.provider_code = canonical["provider_code"]
    reference = str(canonical["transaction_reference"])
    transaction.display_reference_masked = (
        reference if len(reference) <= 8 else f"{reference[:4]}…{reference[-2:]}"
    )
    record.resource_type = "ocr_confirmation"
    record.resource_id = confirmation.id
    record.response_status = 201
    audit_event(
        "ocr.confirmed",
        "SUCCESS",
        actor_id=user.id,
        roles=roles,
        target_type="transaction",
        target_id=transaction.id,
        metadata={
            "ocr_result_id": str(ocr_result.id),
            "confirmation_id": str(confirmation.id),
            "corrected_fields": [item["field"] for item in corrections],
            "correction_count": len(corrections),
            "schema_version": confirmation.schema_version,
        },
    )
    db.session.commit()
    return ConfirmationResult(transaction, confirmation, False)


def latest_confirmation(transaction: Transaction) -> OCRConfirmation | None:
    return db.session.scalar(
        select(OCRConfirmation)
        .where(OCRConfirmation.transaction_id == transaction.id)
        .order_by(OCRConfirmation.confirmed_at.desc(), OCRConfirmation.id.desc())
    )


__all__ = [
    "FIELD_NAMES",
    "OCRFailure",
    "OCRPipelineResult",
    "canonicalize_confirmation_fields",
    "confirm_ocr",
    "create_preprocessing_variants",
    "execute_ocr",
    "latest_confirmation",
    "latest_ocr_result",
    "mask_phone",
    "normalize_amount",
    "normalize_occurred_at",
    "normalize_phone",
    "normalize_reference",
    "parse_fields",
    "run_and_store_ocr",
]
