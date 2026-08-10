"""Versioned deterministic image evidence with private diagnostic derivatives."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise
from typing import Any

import cv2
import numpy as np
from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    ImageAnalysis,
    OCRResult,
    Receipt,
    ReceiptDerivative,
    Transaction,
)
from momo_fdvs.storage.base import ObjectStorage, generated_key, sha256_bytes


class ImageForensicsFailure(RuntimeError):
    """A controlled image-evidence failure that is safe to expose as a reason code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ImageForensicsOutcome:
    image_analysis: ImageAnalysis
    written_keys: tuple[str, ...]


def _rounded(value: float, digits: int = 6) -> float:
    return round(float(value), digits)


def _signal(
    code: str,
    *,
    extractor_version: str,
    status: str,
    severity: str,
    observed: dict[str, Any],
    threshold: dict[str, Any],
    confidence: float,
    reason: str,
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "extractor_version": extractor_version,
        "status": status,
        "severity": severity,
        "observed": observed,
        "threshold": threshold,
        "confidence": _rounded(max(0.0, min(1.0, confidence)), 4),
        "reason": reason,
        "limitations": limitations or [],
    }


def _domain(version: str, signals: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": version,
        "signals": signals,
        "triggered_codes": [
            str(signal["code"]) for signal in signals if signal["status"] == "TRIGGERED"
        ],
        "not_applicable_codes": [
            str(signal["code"]) for signal in signals if signal["status"] == "NOT_APPLICABLE"
        ],
    }


def _decode(content: bytes, receipt: Receipt) -> tuple[Image.Image, np.ndarray, dict[str, Any]]:
    if hashlib.sha256(content).hexdigest() != receipt.sha256:
        raise ImageForensicsFailure(
            "IMAGE_RECEIPT_HASH_MISMATCH",
            "The stored receipt failed its evidence-integrity check.",
        )
    try:
        with Image.open(io.BytesIO(content), formats=["JPEG", "PNG", "WEBP"]) as opened:
            opened.load()
            decoded_format = str(opened.format or "UNKNOWN").upper()
            decoded_mode = str(opened.mode)
            exif = opened.getexif()
            software = exif.get(305) if exif else None
            safe_software = (
                "".join(character for character in str(software) if character.isprintable())[:120]
                if software
                else None
            )
            oriented = ImageOps.exif_transpose(opened).convert("RGB")
            metadata = {
                "decoded_format": decoded_format,
                "decoded_mode": decoded_mode,
                "decoded_width_px": oriented.width,
                "decoded_height_px": oriented.height,
                "exif_present": bool(exif),
                "software_encoder": safe_software,
            }
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageForensicsFailure(
            "IMAGE_DECODE_FAILED", "The private receipt could not be decoded for image evidence."
        ) from exc
    return oriented, np.asarray(oriented, dtype=np.uint8), metadata


def _metadata_evidence(receipt: Receipt, metadata: dict[str, Any]) -> dict[str, Any]:
    version = "metadata-evidence-v1"
    signals: list[dict[str, Any]] = []
    expected_format = {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
    }.get(receipt.media_type)
    conflict = (
        metadata["decoded_format"] != expected_format
        or metadata["decoded_width_px"] != receipt.width_px
        or metadata["decoded_height_px"] != receipt.height_px
    )
    signals.append(
        _signal(
            "DECODED_IMAGE_METADATA_CONSISTENCY",
            extractor_version=version,
            status="TRIGGERED" if conflict else "OBSERVED",
            severity="MEDIUM" if conflict else "INFORMATIONAL",
            observed={
                **metadata,
                "stored_media_type": receipt.media_type,
                "stored_width_px": receipt.width_px,
                "stored_height_px": receipt.height_px,
            },
            threshold={"stored_and_decoded_values_must_match": True},
            confidence=1.0,
            reason=(
                "The decoded image properties conflict with the stored validated receipt metadata."
                if conflict
                else "The decoded image properties match the stored validated receipt metadata."
            ),
            limitations=["A consistent container does not prove that receipt content is genuine."],
        )
    )
    signals.append(
        _signal(
            "METADATA_ABSENT" if not metadata["exif_present"] else "METADATA_PRESENT",
            extractor_version=version,
            status="NEUTRAL" if not metadata["exif_present"] else "OBSERVED",
            severity="INFORMATIONAL",
            observed={"exif_present": metadata["exif_present"]},
            threshold={"absence_is_suspicious": False},
            confidence=1.0,
            reason=(
                "No EXIF metadata was present; this is common for screenshots and is neutral."
                if not metadata["exif_present"]
                else "EXIF metadata was present; only allowlisted technical fields were inspected."
            ),
            limitations=["Screenshots and messaging applications commonly remove metadata."],
        )
    )
    software = str(metadata.get("software_encoder") or "")
    editing_hint = any(
        keyword in software.casefold()
        for keyword in ("photoshop", "gimp", "canva", "affinity", "lightroom", "snapseed")
    )
    signals.append(
        _signal(
            "EDITING_SOFTWARE_HINT",
            extractor_version=version,
            status="TRIGGERED" if editing_hint else "NOT_APPLICABLE",
            severity="LOW" if editing_hint else "INFORMATIONAL",
            observed={"software_encoder": software or None},
            threshold={"editing_software_keywords": "versioned-allowlist-v1"},
            confidence=0.8 if editing_hint else 1.0,
            reason=(
                "An editing-software encoder hint was found and is supporting evidence only."
                if editing_hint
                else "No editing-software encoder hint was available."
            ),
            limitations=["Legitimate export or optimisation tools may write the same metadata."],
        )
    )
    return _domain(version, signals)


def _duplicate_evidence(receipt: Receipt) -> tuple[dict[str, Any], dict[str, float]]:
    version = "duplicate-evidence-v1"
    rows = db.session.execute(
        select(Receipt.sha256, Receipt.perceptual_hash).where(Receipt.id != receipt.id)
    ).all()
    exact_count = sum(existing_sha == receipt.sha256 for existing_sha, _ in rows)
    maximum_distance = int(current_app.config["UPLOAD_NEAR_DUPLICATE_DISTANCE"])
    near_distances = [
        (int(existing_hash, 16) ^ int(receipt.perceptual_hash, 16)).bit_count()
        for existing_sha, existing_hash in rows
        if existing_sha != receipt.sha256 and existing_hash
    ]
    near_count = sum(distance <= maximum_distance for distance in near_distances)
    minimum_distance = min(near_distances) if near_distances else None
    signals = [
        _signal(
            "EXACT_RECEIPT_REUSE",
            extractor_version=version,
            status="TRIGGERED" if exact_count else "OBSERVED",
            severity="MEDIUM" if exact_count else "INFORMATIONAL",
            observed={"candidate_count": exact_count},
            threshold={"sha256_equal": True},
            confidence=1.0,
            reason=(
                "The exact receipt bytes have appeared in another stored transaction."
                if exact_count
                else "No other stored receipt has the same SHA-256 value."
            ),
            limitations=["A legitimate user may upload the same receipt more than once."],
        ),
        _signal(
            "NEAR_RECEIPT_REUSE",
            extractor_version=version,
            status="TRIGGERED" if near_count else "OBSERVED",
            severity="LOW" if near_count else "INFORMATIONAL",
            observed={
                "candidate_count": near_count,
                "minimum_hamming_distance": minimum_distance,
            },
            threshold={"maximum_hamming_distance": maximum_distance},
            confidence=0.75 if near_count else 1.0,
            reason=(
                "A visually similar stored receipt candidate was found."
                if near_count
                else "No stored receipt was within the configured perceptual-hash distance."
            ),
            limitations=["Perceptual hashes are similarity indicators and may collide."],
        ),
    ]
    return _domain(version, signals), {
        "duplicate_exact_count": float(exact_count),
        "duplicate_near_count": float(near_count),
        "duplicate_minimum_hamming_distance": float(minimum_distance)
        if minimum_distance is not None
        else -1.0,
    }


def _regional_means(values: np.ndarray, rows: int = 4, columns: int = 4) -> list[float]:
    means: list[float] = []
    for vertical in np.array_split(values, rows, axis=0):
        for region in np.array_split(vertical, columns, axis=1):
            if region.size:
                means.append(float(np.mean(region)))
    return means


def _diagnostic_png(values: np.ndarray) -> bytes:
    maximum = float(np.max(values)) if values.size else 0.0
    normalized = (
        np.zeros(values.shape, dtype=np.uint8)
        if maximum <= 0
        else np.clip(values * (255.0 / maximum), 0, 255).astype(np.uint8)
    )
    coloured = cv2.applyColorMap(normalized, cv2.COLORMAP_INFERNO)
    success, encoded = cv2.imencode(".png", coloured, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not success:
        raise ImageForensicsFailure(
            "IMAGE_DIAGNOSTIC_ENCODING_FAILED",
            "A private image diagnostic could not be encoded safely.",
        )
    return bytes(encoded)


def _compression_evidence(
    image: Image.Image,
) -> tuple[dict[str, Any], dict[str, float], bytes | None]:
    version = "recompression-evidence-v1"
    minimum = int(current_app.config["IMAGE_FORENSICS_MIN_DIMENSION_PX"])
    if min(image.size) < minimum:
        signal = _signal(
            "RECOMPRESSION_NOT_APPLICABLE",
            extractor_version=version,
            status="NOT_APPLICABLE",
            severity="INFORMATIONAL",
            observed={"width_px": image.width, "height_px": image.height},
            threshold={"minimum_dimension_px": minimum},
            confidence=1.0,
            reason="The receipt is too small for a stable recompression comparison.",
            limitations=["No recompression values were invented for this receipt."],
        )
        return _domain(version, [signal]), {}, None
    buffer = io.BytesIO()
    quality = int(current_app.config["IMAGE_FORENSICS_JPEG_QUALITY"])
    image.save(buffer, format="JPEG", quality=quality, optimize=False, subsampling=2)
    with Image.open(io.BytesIO(buffer.getvalue()), formats=["JPEG"]) as recompressed:
        recompressed.load()
        recompressed_array = np.asarray(recompressed.convert("RGB"), dtype=np.int16)
    original_array = np.asarray(image, dtype=np.int16)
    difference = np.mean(np.abs(original_array - recompressed_array), axis=2).astype(np.float32)
    regional = _regional_means(difference)
    mean_error = float(np.mean(difference))
    p95_error = float(np.percentile(difference, 95))
    p99_error = float(np.percentile(difference, 99))
    regional_std = float(np.std(regional)) if regional else 0.0
    regional_cv = regional_std / max(float(np.mean(regional)), 0.001) if regional else 0.0
    high_threshold = max(p95_error, 1.0)
    components, _, stats, _ = cv2.connectedComponentsWithStats(
        (difference >= high_threshold).astype(np.uint8), connectivity=8
    )
    high_regions = sum(int(row[cv2.CC_STAT_AREA]) >= 9 for row in stats[1:components])
    configured_cv = float(current_app.config["IMAGE_FORENSICS_ELA_REGIONAL_CV_THRESHOLD"])
    triggered = regional_cv >= configured_cv and p95_error > 0
    observed = {
        "jpeg_quality": quality,
        "mean_absolute_error": _rounded(mean_error),
        "p95_absolute_error": _rounded(p95_error),
        "p99_absolute_error": _rounded(p99_error),
        "regional_standard_deviation": _rounded(regional_std),
        "regional_coefficient_of_variation": _rounded(regional_cv),
        "connected_high_error_regions": high_regions,
    }
    signal = _signal(
        "RECOMPRESSION_REGIONAL_INCONSISTENCY",
        extractor_version=version,
        status="TRIGGERED" if triggered else "OBSERVED",
        severity="LOW" if triggered else "INFORMATIONAL",
        observed=observed,
        threshold={"regional_coefficient_of_variation": configured_cv},
        confidence=0.65 if triggered else 0.8,
        reason=(
            "Controlled recompression produced uneven regional error; this is supporting "
            "evidence only."
            if triggered
            else "Controlled recompression did not exceed the configured regional-variation "
            "threshold."
        ),
        limitations=[
            "ELA is weak on screenshots and previously recompressed images.",
            "Recompression variation is not proof that content was edited.",
        ],
    )
    features = {
        "ela_mean_error": mean_error,
        "ela_p95_error": p95_error,
        "ela_p99_error": p99_error,
        "ela_regional_cv": regional_cv,
        "ela_high_region_count": float(high_regions),
    }
    return _domain(version, [signal]), features, _diagnostic_png(difference)


def _noise_evidence(
    rgb: np.ndarray, quality_score: Decimal | None
) -> tuple[dict[str, Any], dict[str, float], bytes | None]:
    version = "noise-residual-v1"
    minimum = int(current_app.config["IMAGE_FORENSICS_MIN_DIMENSION_PX"])
    minimum_quality = float(current_app.config["IMAGE_FORENSICS_MIN_QUALITY_SCORE"])
    observed_quality = float(quality_score) if quality_score is not None else None
    if min(rgb.shape[:2]) < minimum or (
        observed_quality is not None and observed_quality < minimum_quality
    ):
        signal = _signal(
            "NOISE_RESIDUAL_NOT_APPLICABLE",
            extractor_version=version,
            status="NOT_APPLICABLE",
            severity="INFORMATIONAL",
            observed={
                "width_px": int(rgb.shape[1]),
                "height_px": int(rgb.shape[0]),
                "quality_score": observed_quality,
            },
            threshold={
                "minimum_dimension_px": minimum,
                "minimum_quality_score": minimum_quality,
            },
            confidence=1.0,
            reason="Image size or quality is insufficient for a stable residual comparison.",
            limitations=["No residual consistency value was invented for this receipt."],
        )
        return _domain(version, [signal]), {}, None
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    residual = np.abs(gray - denoised)
    regional = _regional_means(residual)
    mean_residual = float(np.mean(residual))
    regional_std = float(np.std(regional)) if regional else 0.0
    regional_cv = regional_std / max(float(np.mean(regional)), 0.001) if regional else 0.0
    configured_cv = float(current_app.config["IMAGE_FORENSICS_NOISE_REGIONAL_CV_THRESHOLD"])
    triggered = regional_cv >= configured_cv and mean_residual > 0.1
    signal = _signal(
        "NOISE_RESIDUAL_INCONSISTENCY",
        extractor_version=version,
        status="TRIGGERED" if triggered else "OBSERVED",
        severity="LOW" if triggered else "INFORMATIONAL",
        observed={
            "mean_residual": _rounded(mean_residual),
            "regional_standard_deviation": _rounded(regional_std),
            "regional_coefficient_of_variation": _rounded(regional_cv),
        },
        threshold={"regional_coefficient_of_variation": configured_cv},
        confidence=0.6 if triggered else 0.75,
        reason=(
            "Residual energy varies across regions; this is supporting evidence only."
            if triggered
            else "Residual variation did not exceed the configured threshold."
        ),
        limitations=[
            "Text density, compression and camera processing can alter regional residuals.",
            "Noise residuals are not proof that receipt content was edited.",
        ],
    )
    return (
        _domain(version, [signal]),
        {
            "noise_mean_residual": mean_residual,
            "noise_regional_cv": regional_cv,
        },
        _diagnostic_png(residual),
    )


def _overlap(first: dict[str, float], second: dict[str, float]) -> bool:
    return not (
        first["right"] <= second["left"]
        or second["right"] <= first["left"]
        or first["bottom"] <= second["top"]
        or second["bottom"] <= first["top"]
    )


def _layout_evidence(
    tokens: list[Any], width: int, height: int
) -> tuple[dict[str, Any], dict[str, float]]:
    version = "ocr-layout-evidence-v1"
    valid: list[dict[str, Any]] = []
    for raw in tokens:
        if not isinstance(raw, dict):
            continue
        try:
            x = max(0.0, float(raw["x"]))
            y = max(0.0, float(raw["y"]))
            token_width = max(0.0, float(raw["width"]))
            token_height = max(0.0, float(raw["height"]))
        except (KeyError, TypeError, ValueError):
            continue
        if token_width <= 0 or token_height <= 0:
            continue
        valid.append(
            {
                "left": x,
                "top": y,
                "right": min(float(width), x + token_width),
                "bottom": min(float(height), y + token_height),
                "height": token_height,
                "line_id": str(raw.get("line_id", "unknown"))[:80],
            }
        )
    if len(valid) < 3:
        signal = _signal(
            "OCR_LAYOUT_NOT_APPLICABLE",
            extractor_version=version,
            status="NOT_APPLICABLE",
            severity="INFORMATIONAL",
            observed={"usable_token_count": len(valid)},
            threshold={"minimum_usable_token_count": 3},
            confidence=1.0,
            reason="Too few safe OCR boxes were available for layout comparison.",
            limitations=["No alignment or crop value was invented."],
        )
        return _domain(version, [signal]), {}
    heights = np.asarray([token["height"] for token in valid], dtype=np.float64)
    height_cv = float(np.std(heights) / max(float(np.mean(heights)), 0.001))
    baselines: list[float] = []
    spacing_values: list[float] = []
    lines: dict[str, list[dict[str, Any]]] = {}
    for token in valid:
        lines.setdefault(str(token["line_id"]), []).append(token)
    median_height = max(float(np.median(heights)), 1.0)
    for line in lines.values():
        bottoms = np.asarray([token["bottom"] for token in line], dtype=np.float64)
        if len(bottoms) > 1:
            baselines.extend(abs(bottoms - float(np.median(bottoms))) / median_height)
        ordered = sorted(line, key=lambda token: token["left"])
        for previous, following in pairwise(ordered):
            spacing_values.append(max(0.0, following["left"] - previous["right"]) / median_height)
    baseline_deviation = float(np.mean(baselines)) if baselines else 0.0
    spacing_cv = (
        float(np.std(spacing_values) / max(float(np.mean(spacing_values)), 0.001))
        if spacing_values
        else 0.0
    )
    overlap_count = sum(
        _overlap(valid[index], valid[other])
        for index in range(len(valid))
        for other in range(index + 1, len(valid))
        if valid[index]["line_id"] != valid[other]["line_id"]
    )
    margin_fraction = min(
        min(token["left"] for token in valid) / max(width, 1),
        min(token["top"] for token in valid) / max(height, 1),
        (width - max(token["right"] for token in valid)) / max(width, 1),
        (height - max(token["bottom"] for token in valid)) / max(height, 1),
    )
    baseline_threshold = float(current_app.config["IMAGE_FORENSICS_BASELINE_THRESHOLD"])
    height_threshold = float(current_app.config["IMAGE_FORENSICS_HEIGHT_CV_THRESHOLD"])
    margin_threshold = float(current_app.config["IMAGE_FORENSICS_EDGE_MARGIN_THRESHOLD"])
    alignment_triggered = (
        baseline_deviation >= baseline_threshold
        or height_cv >= height_threshold
        or overlap_count > 0
    )
    crop_triggered = margin_fraction <= margin_threshold
    signals = [
        _signal(
            "TEXT_ALIGNMENT_INCONSISTENCY",
            extractor_version=version,
            status="TRIGGERED" if alignment_triggered else "OBSERVED",
            severity="MEDIUM" if alignment_triggered else "INFORMATIONAL",
            observed={
                "usable_token_count": len(valid),
                "baseline_deviation": _rounded(baseline_deviation),
                "box_height_coefficient_of_variation": _rounded(height_cv),
                "spacing_coefficient_of_variation": _rounded(spacing_cv),
                "cross_line_overlap_count": overlap_count,
            },
            threshold={
                "baseline_deviation": baseline_threshold,
                "box_height_coefficient_of_variation": height_threshold,
                "cross_line_overlap_count": 0,
            },
            confidence=min(0.9, 0.5 + len(valid) / 100),
            reason=(
                "OCR box alignment exceeded a configured supporting-evidence threshold."
                if alignment_triggered
                else "OCR box alignment stayed within the configured supporting-evidence "
                "thresholds."
            ),
            limitations=["OCR box errors can create apparent alignment anomalies."],
        ),
        _signal(
            "POSSIBLE_CROP_OR_EDGE_INCOMPLETENESS",
            extractor_version=version,
            status="TRIGGERED" if crop_triggered else "OBSERVED",
            severity="LOW" if crop_triggered else "INFORMATIONAL",
            observed={"minimum_text_edge_margin_fraction": _rounded(margin_fraction)},
            threshold={"minimum_text_edge_margin_fraction": margin_threshold},
            confidence=0.65,
            reason=(
                "Detected text is very close to a receipt edge; this may indicate cropping."
                if crop_triggered
                else "Detected text retained the configured minimum edge margin."
            ),
            limitations=["Some genuine receipt layouts place text close to an edge."],
        ),
    ]
    return _domain(version, signals), {
        "layout_baseline_deviation": baseline_deviation,
        "layout_height_cv": height_cv,
        "layout_spacing_cv": spacing_cv,
        "layout_overlap_count": float(overlap_count),
        "layout_minimum_edge_margin": margin_fraction,
    }


def _quality_evidence(receipt: Receipt, width: int, height: int) -> dict[str, Any]:
    version = "quality-context-v1"
    warnings = [
        str(warning)
        for warning in receipt.quality_warnings
        if not str(warning).startswith("POSSIBLE_")
    ]
    aspect_ratio = width / max(height, 1)
    minimum_aspect = float(current_app.config["IMAGE_FORENSICS_MIN_ASPECT_RATIO"])
    maximum_aspect = float(current_app.config["IMAGE_FORENSICS_MAX_ASPECT_RATIO"])
    unusual_aspect = not minimum_aspect <= aspect_ratio <= maximum_aspect
    signals = [
        _signal(
            "IMAGE_QUALITY_CONTEXT",
            extractor_version=version,
            status="OBSERVED" if not warnings else "TRIGGERED",
            severity="LOW" if warnings else "INFORMATIONAL",
            observed={
                "quality_score": float(receipt.quality_score)
                if receipt.quality_score is not None
                else None,
                "quality_warning_codes": warnings,
            },
            threshold={"quality_warnings_are_context_only": True},
            confidence=1.0,
            reason=(
                "Receipt quality warnings may reduce forensic reliability."
                if warnings
                else "No stored quality warning reduces the current evidence reliability."
            ),
            limitations=["Quality warnings never determine fraud risk by themselves."],
        ),
        _signal(
            "UNUSUAL_RECEIPT_ASPECT_RATIO",
            extractor_version=version,
            status="TRIGGERED" if unusual_aspect else "OBSERVED",
            severity="LOW" if unusual_aspect else "INFORMATIONAL",
            observed={"aspect_ratio": _rounded(aspect_ratio)},
            threshold={"minimum": minimum_aspect, "maximum": maximum_aspect},
            confidence=0.55,
            reason=(
                "The receipt aspect ratio is outside the broad configured range."
                if unusual_aspect
                else "The receipt aspect ratio is inside the broad configured range."
            ),
            limitations=["Provider templates vary and a broad ratio check is weak evidence."],
        ),
    ]
    return _domain(version, signals)


def _store_diagnostic(
    *,
    storage: ObjectStorage,
    transaction: Transaction,
    receipt: Receipt,
    kind: str,
    version: str,
    content: bytes,
) -> tuple[ReceiptDerivative, str | None]:
    digest = sha256_bytes(content)
    existing = db.session.scalar(
        select(ReceiptDerivative).where(
            ReceiptDerivative.receipt_id == receipt.id,
            ReceiptDerivative.kind == kind,
            ReceiptDerivative.version == version,
            ReceiptDerivative.sha256 == digest,
        )
    )
    if existing is not None:
        return existing, None
    key = generated_key(f"receipts/{transaction.user_id}/{transaction.id}/derived/forensics", "png")
    stored = storage.put_bytes(
        key,
        content,
        "image/png",
        {
            "source-sha256": receipt.sha256,
            "analysis-version": current_app.config["IMAGE_FORENSICS_VERSION"],
            "diagnostic-kind": kind,
        },
    )
    derivative = ReceiptDerivative(
        receipt_id=receipt.id,
        kind=kind,
        version=version,
        object_key=stored.key,
        sha256=digest,
        metadata_json={
            "media_type": "image/png",
            "source_sha256": receipt.sha256,
            "algorithm_version": current_app.config["IMAGE_FORENSICS_VERSION"],
            "supporting_evidence_only": True,
        },
    )
    db.session.add(derivative)
    return derivative, stored.key


def run_image_forensics(
    *,
    run: AnalysisRun,
    transaction: Transaction,
    ocr_result: OCRResult,
    storage: ObjectStorage,
) -> ImageForensicsOutcome:
    """Persist deterministic evidence without generating a fraud class or probability."""
    if transaction.receipt is None:
        raise ImageForensicsFailure(
            "IMAGE_RECEIPT_UNAVAILABLE", "The transaction has no receipt image to inspect."
        )
    receipt = transaction.receipt
    existing = db.session.scalar(
        select(ImageAnalysis).where(ImageAnalysis.analysis_run_id == run.id)
    )
    if existing is not None:
        return ImageForensicsOutcome(existing, ())
    try:
        content = storage.read_bytes(receipt.object_key)
    except Exception as exc:
        raise ImageForensicsFailure(
            "IMAGE_STORAGE_UNAVAILABLE",
            "The private receipt is temporarily unavailable for image evidence.",
        ) from exc
    image, rgb, metadata = _decode(content, receipt)
    metadata_evidence = _metadata_evidence(receipt, metadata)
    duplicate_evidence, duplicate_features = _duplicate_evidence(receipt)
    compression_evidence, compression_features, ela_png = _compression_evidence(image)
    noise_evidence, noise_features, noise_png = _noise_evidence(rgb, receipt.quality_score)
    layout_evidence, layout_features = _layout_evidence(
        ocr_result.token_data, image.width, image.height
    )
    quality_evidence = _quality_evidence(receipt, image.width, image.height)
    engineered_features: dict[str, Any] = {
        "schema_version": "deterministic-image-features-v1",
        **{key: _rounded(value) for key, value in duplicate_features.items()},
        **{key: _rounded(value) for key, value in compression_features.items()},
        **{key: _rounded(value) for key, value in noise_features.items()},
        **{key: _rounded(value) for key, value in layout_features.items()},
    }
    domains = (
        metadata_evidence,
        duplicate_evidence,
        compression_evidence,
        noise_evidence,
        layout_evidence,
        quality_evidence,
    )
    triggered = [
        signal
        for domain in domains
        for signal in domain["signals"]
        if signal["status"] == "TRIGGERED"
    ]
    warnings = list(
        dict.fromkeys(
            [str(signal["code"]) for signal in triggered]
            + [
                str(signal["code"])
                for domain in domains
                for signal in domain["signals"]
                if signal["status"] == "NOT_APPLICABLE"
            ]
        )
    )
    engineered_features["supporting_trigger_count"] = len(triggered)
    engineered_features["weak_signal_policy"] = {
        "final_risk_class_emitted": False,
        "image_tamper_probability_emitted": False,
        "single_weak_signal_can_classify_fraud": False,
    }
    image_analysis = ImageAnalysis(
        analysis_run_id=run.id,
        algorithm_version=current_app.config["IMAGE_FORENSICS_VERSION"],
        metadata_evidence=metadata_evidence,
        duplicate_evidence=duplicate_evidence,
        compression_evidence=compression_evidence,
        noise_evidence=noise_evidence,
        layout_evidence=layout_evidence,
        quality_evidence=quality_evidence,
        engineered_features=engineered_features,
        image_tamper_probability=None,
        warnings=warnings,
    )
    db.session.add(image_analysis)
    written: list[str] = []
    try:
        if ela_png is not None:
            _, key = _store_diagnostic(
                storage=storage,
                transaction=transaction,
                receipt=receipt,
                kind="ELA",
                version=f"{current_app.config['IMAGE_FORENSICS_VERSION']}:ela"[:50],
                content=ela_png,
            )
            if key:
                written.append(key)
        if noise_png is not None:
            _, key = _store_diagnostic(
                storage=storage,
                transaction=transaction,
                receipt=receipt,
                kind="NOISE_MAP",
                version=f"{current_app.config['IMAGE_FORENSICS_VERSION']}:noise"[:50],
                content=noise_png,
            )
            if key:
                written.append(key)
        db.session.flush()
    except Exception as exc:
        for key in reversed(written):
            try:
                storage.delete(key)
            except Exception:
                current_app.logger.exception("image_forensics_derivative_cleanup_failed")
        raise ImageForensicsFailure(
            "IMAGE_DIAGNOSTIC_STORAGE_FAILED",
            "Private image diagnostics could not be stored safely.",
        ) from exc
    return ImageForensicsOutcome(image_analysis, tuple(written))


def image_evidence_projection(
    result: ImageAnalysis,
    *,
    transaction_id: Any,
    include_diagnostics: bool,
) -> dict[str, Any]:
    domains = {
        "metadata": result.metadata_evidence,
        "duplicate": result.duplicate_evidence,
        "compression": result.compression_evidence,
        "noise": result.noise_evidence,
        "layout": result.layout_evidence,
        "quality": result.quality_evidence,
    }
    triggered = [
        {
            "code": signal["code"],
            "severity": signal["severity"],
            "reason": signal["reason"],
            "confidence": signal["confidence"],
        }
        for domain in domains.values()
        for signal in domain["signals"]
        if signal["status"] == "TRIGGERED"
    ]
    projection: dict[str, Any] = {
        "status": "COMPLETED",
        "algorithm_version": result.algorithm_version,
        "classification": None,
        "tamper_probability": None,
        "summary": (
            "Deterministic supporting evidence was recorded. It is not proof of fraud and no "
            "final fraud class was produced."
        ),
        "domains": domains,
        "triggered_signals": triggered,
        "warnings": result.warnings,
        "policy": {
            "supporting_evidence_only": True,
            "single_weak_signal_can_classify_fraud": False,
        },
    }
    if include_diagnostics:
        base = f"/api/v1/transactions/{transaction_id}/receipt"
        projection["diagnostic_media"] = {
            "ela_url": f"{base}?variant=ela",
            "noise_map_url": f"{base}?variant=noise-map",
            "access": "AUTHORISED_STAFF_ONLY",
        }
    return projection


def unavailable_image_evidence(reason_code: str) -> dict[str, Any]:
    return {
        "status": "UNAVAILABLE",
        "reason_code": reason_code,
        "classification": None,
        "tamper_probability": None,
        "summary": "Deterministic image evidence was unavailable; no values were invented.",
        "policy": {
            "supporting_evidence_only": True,
            "single_weak_signal_can_classify_fraud": False,
        },
    }


__all__ = [
    "ImageForensicsFailure",
    "ImageForensicsOutcome",
    "image_evidence_projection",
    "run_image_forensics",
    "unavailable_image_evidence",
]
