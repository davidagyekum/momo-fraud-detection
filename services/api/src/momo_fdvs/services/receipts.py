"""Hostile receipt validation and atomic private evidence persistence."""

from __future__ import annotations

import hashlib
import io
import json
import math
import uuid
import warnings
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import PurePath
from typing import Any, cast

from flask import current_app
from PIL import Image, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from momo_fdvs.extensions import db
from momo_fdvs.models import IdempotencyRecord, Receipt, ReceiptDerivative, Transaction, User
from momo_fdvs.services.audit import audit_event
from momo_fdvs.storage.base import ObjectStorage, generated_key, sha256_bytes

FORMAT_DETAILS = {
    "JPEG": ("image/jpeg", {"jpg", "jpeg"}, "jpg"),
    "PNG": ("image/png", {"png"}, "png"),
    "WEBP": ("image/webp", {"webp"}, "webp"),
}
THUMBNAIL_VERSION = "thumbnail-v1"
STORAGE_VERSION = "private-v1"


class ReceiptFailure(RuntimeError):
    """A safe, intentionally public upload failure."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


@dataclass(frozen=True)
class InspectedReceipt:
    content: bytes
    display_filename: str
    media_type: str
    extension: str
    width_px: int
    height_px: int
    sha256: str
    perceptual_hash: str
    quality_score: Decimal
    quality_warnings: list[str]
    thumbnail: bytes
    thumbnail_width_px: int
    thumbnail_height_px: int


@dataclass(frozen=True)
class UploadResult:
    transaction: Transaction
    receipt: Receipt
    duplicate_warning: dict[str, Any]
    replayed: bool


def _clean_filename(filename: str | None) -> tuple[str, str]:
    normalized = (filename or "receipt").replace("\\", "/")
    display = PurePath(normalized).name.strip() or "receipt"
    display = "".join(character for character in display if character.isprintable())[:255]
    extension = display.rsplit(".", 1)[-1].lower() if "." in display else ""
    if not extension:
        raise ReceiptFailure(
            "UNSUPPORTED_RECEIPT_FORMAT",
            "The receipt filename must use .jpg, .jpeg, .png, or .webp.",
            415,
        )
    return display, extension


def _reject_trailing_payload(content: bytes, image_format: str) -> None:
    if image_format == "JPEG":
        offset = 2
        in_scan = False
        valid_end = False
        while offset < len(content):
            if content[offset] != 0xFF:
                if in_scan:
                    offset += 1
                    continue
                break
            while offset < len(content) and content[offset] == 0xFF:
                offset += 1
            if offset >= len(content):
                break
            marker = content[offset]
            offset += 1
            if marker == 0x00 and in_scan:
                continue
            if marker == 0xD9:
                valid_end = offset == len(content)
                break
            if 0xD0 <= marker <= 0xD7 and in_scan:
                continue
            if marker in {0x01, 0xD8}:
                continue
            if offset + 2 > len(content):
                break
            segment_length = int.from_bytes(content[offset : offset + 2], "big")
            if segment_length < 2 or offset + segment_length > len(content):
                break
            offset += segment_length
            in_scan = marker == 0xDA
        if not valid_end:
            raise ReceiptFailure(
                "INVALID_RECEIPT_CONTENT", "The JPEG contains an invalid trailing payload.", 415
            )
    if image_format == "WEBP":
        if len(content) < 12 or content[:4] != b"RIFF" or content[8:12] != b"WEBP":
            raise ReceiptFailure("INVALID_RECEIPT_CONTENT", "The WebP header is invalid.", 415)
        if int.from_bytes(content[4:8], "little") + 8 != len(content):
            raise ReceiptFailure(
                "INVALID_RECEIPT_CONTENT", "The WebP contains an invalid trailing payload.", 415
            )
    if image_format == "PNG":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ReceiptFailure("INVALID_RECEIPT_CONTENT", "The PNG header is invalid.", 415)
        offset = 8
        found_iend = False
        while offset + 12 <= len(content):
            chunk_length = int.from_bytes(content[offset : offset + 4], "big")
            chunk_end = offset + 12 + chunk_length
            if chunk_end > len(content):
                break
            if content[offset + 4 : offset + 8] == b"IEND":
                found_iend = True
                if chunk_length != 0 or chunk_end != len(content):
                    raise ReceiptFailure(
                        "INVALID_RECEIPT_CONTENT",
                        "The PNG contains an invalid trailing payload.",
                        415,
                    )
                break
            offset = chunk_end
        if not found_iend:
            raise ReceiptFailure("INVALID_RECEIPT_CONTENT", "The PNG is incomplete.", 415)


def _quality_and_thumbnail(image: Image.Image) -> tuple[Decimal, list[str], str, bytes, int, int]:
    normalized = ImageOps.exif_transpose(image).convert("RGB")
    gray = normalized.convert("L")
    statistics = ImageStat.Stat(gray)
    brightness = float(statistics.mean[0])
    contrast = float(statistics.stddev[0])
    edge_strength = float(ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).stddev[0])

    quality_warnings: list[str] = []
    score = 1.0
    if (
        normalized.width < current_app.config["UPLOAD_MIN_WIDTH_PX"]
        or normalized.height < current_app.config["UPLOAD_MIN_HEIGHT_PX"]
    ):
        quality_warnings.append("IMAGE_TOO_SMALL")
        score -= 0.25
    if contrast < 22:
        quality_warnings.append("LOW_CONTRAST")
        score -= 0.20
    if edge_strength < 10:
        quality_warnings.append("POSSIBLY_BLURRY")
        score -= 0.20
    if brightness < 45:
        quality_warnings.append("TOO_DARK")
        score -= 0.20
    elif brightness > 225:
        quality_warnings.append("TOO_BRIGHT")
        score -= 0.20

    hash_image = gray.resize((9, 8), Image.Resampling.LANCZOS)
    pixels = cast(list[int], list(hash_image.get_flattened_data()))
    bits = 0
    for row in range(8):
        for column in range(8):
            bits = (bits << 1) | int(pixels[row * 9 + column] > pixels[row * 9 + column + 1])
    perceptual_hash = f"{bits:016x}"

    thumbnail = normalized.copy()
    thumbnail.thumbnail((512, 512), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    thumbnail.save(output, format="JPEG", quality=85, optimize=True)
    return (
        Decimal(f"{max(0.0, score):.4f}"),
        quality_warnings,
        perceptual_hash,
        output.getvalue(),
        thumbnail.width,
        thumbnail.height,
    )


def inspect_receipt(content: bytes, filename: str | None) -> InspectedReceipt:
    """Decode bounded image bytes and derive non-evidential quality signals."""
    if not content:
        raise ReceiptFailure("RECEIPT_REQUIRED", "A receipt image is required.", 400)
    max_bytes = int(current_app.config["UPLOAD_MAX_BYTES"])
    if len(content) > max_bytes:
        raise ReceiptFailure(
            "RECEIPT_TOO_LARGE", f"The receipt must be {max_bytes} bytes or smaller.", 413
        )
    display_filename, client_extension = _clean_filename(filename)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content), formats=["JPEG", "PNG", "WEBP"]) as probe:
                image_format = (probe.format or "").upper()
                if image_format not in FORMAT_DETAILS:
                    raise ReceiptFailure(
                        "UNSUPPORTED_RECEIPT_FORMAT",
                        "Only decoded JPEG, PNG, and WebP receipt images are accepted.",
                        415,
                    )
                media_type, allowed_extensions, canonical_extension = FORMAT_DETAILS[image_format]
                if client_extension not in allowed_extensions:
                    raise ReceiptFailure(
                        "RECEIPT_EXTENSION_MISMATCH",
                        "The filename extension does not match the decoded image.",
                        415,
                    )
                if int(getattr(probe, "n_frames", 1)) != 1 or bool(
                    getattr(probe, "is_animated", False)
                ):
                    raise ReceiptFailure(
                        "ANIMATED_RECEIPT_NOT_ALLOWED",
                        "Animated or multi-frame receipt images are not accepted.",
                        415,
                    )
                width, height = probe.size
                max_dimension = int(current_app.config["UPLOAD_MAX_DIMENSION_PX"])
                max_pixels = int(current_app.config["UPLOAD_MAX_PIXEL_COUNT"])
                if width < 1 or height < 1 or width > max_dimension or height > max_dimension:
                    raise ReceiptFailure(
                        "RECEIPT_DIMENSIONS_INVALID",
                        "The receipt dimensions are outside the safe processing range.",
                        415,
                    )
                if width * height > max_pixels:
                    raise ReceiptFailure(
                        "RECEIPT_PIXEL_LIMIT_EXCEEDED",
                        "The receipt exceeds the safe decoded-pixel limit.",
                        413,
                    )
                probe.verify()
            _reject_trailing_payload(content, image_format)
            with Image.open(io.BytesIO(content), formats=["JPEG", "PNG", "WEBP"]) as decoded:
                decoded.load()
                score, quality_warnings, phash, thumbnail, thumb_width, thumb_height = (
                    _quality_and_thumbnail(decoded)
                )
    except ReceiptFailure:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ReceiptFailure(
            "RECEIPT_PIXEL_LIMIT_EXCEEDED",
            "The receipt exceeds the safe decoded-pixel limit.",
            413,
        ) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ReceiptFailure(
            "INVALID_RECEIPT_CONTENT",
            "The uploaded file is corrupt or is not a supported receipt image.",
            415,
        ) from exc
    return InspectedReceipt(
        content=content,
        display_filename=display_filename,
        media_type=media_type,
        extension=canonical_extension,
        width_px=width,
        height_px=height,
        sha256=sha256_bytes(content),
        perceptual_hash=phash,
        quality_score=score,
        quality_warnings=quality_warnings,
        thumbnail=thumbnail,
        thumbnail_width_px=thumb_width,
        thumbnail_height_px=thumb_height,
    )


def validate_client_metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    if len(raw.encode("utf-8")) > current_app.config["UPLOAD_CLIENT_METADATA_MAX_BYTES"]:
        raise ReceiptFailure(
            "CLIENT_METADATA_TOO_LARGE", "Client metadata exceeds the allowed size.", 400
        )
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ReceiptFailure(
            "CLIENT_METADATA_INVALID", "Client metadata must be JSON.", 400
        ) from exc
    if not isinstance(value, dict) or len(value) > 20:
        raise ReceiptFailure(
            "CLIENT_METADATA_INVALID", "Client metadata must be a small JSON object.", 400
        )
    if any(not isinstance(key, str) or len(key) > 80 for key in value):
        raise ReceiptFailure("CLIENT_METADATA_INVALID", "Client metadata keys are invalid.", 400)
    if any(not isinstance(item, (str, int, float, bool, type(None))) for item in value.values()):
        raise ReceiptFailure(
            "CLIENT_METADATA_INVALID", "Client metadata values must be scalar values.", 400
        )
    if any(isinstance(item, float) and not math.isfinite(item) for item in value.values()):
        raise ReceiptFailure(
            "CLIENT_METADATA_INVALID", "Client metadata numbers must be finite.", 400
        )
    return value


def parse_client_captured_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptFailure(
            "CLIENT_CAPTURED_AT_INVALID", "Client capture time must be ISO 8601.", 400
        ) from exc
    if parsed.tzinfo is None:
        raise ReceiptFailure(
            "CLIENT_CAPTURED_AT_INVALID", "Client capture time must include a timezone.", 400
        )
    return parsed.astimezone(UTC)


def _request_hash(
    inspected: InspectedReceipt,
    source: str,
    captured_at: datetime | None,
    metadata: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "receipt_sha256": inspected.sha256,
            "source": source,
            "client_captured_at": captured_at.isoformat() if captured_at else None,
            "client_metadata": metadata,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _duplicate_counts(inspected: InspectedReceipt) -> tuple[int, int]:
    exact_count = len(
        db.session.scalars(select(Receipt.id).where(Receipt.sha256 == inspected.sha256)).all()
    )
    distance = int(current_app.config["UPLOAD_NEAR_DUPLICATE_DISTANCE"])
    existing_hashes = db.session.execute(select(Receipt.sha256, Receipt.perceptual_hash)).all()
    near_count = sum(
        1
        for existing_sha, existing_hash in existing_hashes
        if existing_sha != inspected.sha256
        and (int(existing_hash, 16) ^ int(inspected.perceptual_hash, 16)).bit_count() <= distance
    )
    return exact_count, near_count


def _projection(transaction: Transaction, receipt: Receipt, replayed: bool) -> UploadResult:
    warnings_list = list(receipt.quality_warnings)
    return UploadResult(
        transaction=transaction,
        receipt=receipt,
        duplicate_warning={
            "exact_match_found": "POSSIBLE_EXACT_DUPLICATE" in warnings_list,
            "near_match_found": "POSSIBLE_NEAR_DUPLICATE" in warnings_list,
        },
        replayed=replayed,
    )


def _claim_idempotency(user: User, key: str, request_hash: str) -> tuple[IdempotencyRecord, bool]:
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    lookup = select(IdempotencyRecord).where(
        IdempotencyRecord.principal_id == user.id,
        IdempotencyRecord.scope == "POST:/api/v1/transactions",
        IdempotencyRecord.key_hash == key_hash,
    )
    record = db.session.scalar(lookup.with_for_update())
    if record is not None:
        return record, False
    candidate = IdempotencyRecord(
        principal_id=user.id,
        scope="POST:/api/v1/transactions",
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


def store_receipt(
    *,
    user: User,
    roles: set[str],
    inspected: InspectedReceipt,
    source: str,
    captured_at: datetime | None,
    client_metadata: dict[str, Any],
    idempotency_key: str,
    storage: ObjectStorage,
) -> UploadResult:
    if source not in {"CAMERA", "GALLERY"}:
        raise ReceiptFailure("UPLOAD_SOURCE_INVALID", "Source must be CAMERA or GALLERY.", 400)
    if not 8 <= len(idempotency_key) <= 200:
        raise ReceiptFailure(
            "IDEMPOTENCY_KEY_INVALID", "Idempotency-Key must contain 8 to 200 characters.", 400
        )

    request_hash = _request_hash(inspected, source, captured_at, client_metadata)
    record, claimed = _claim_idempotency(user, idempotency_key, request_hash)
    if not claimed:
        if record.request_hash != request_hash:
            raise ReceiptFailure(
                "IDEMPOTENCY_KEY_REUSED",
                "This Idempotency-Key was already used for a different request.",
                409,
            )
        if record.resource_type != "transaction" or record.resource_id is None:
            raise ReceiptFailure(
                "IDEMPOTENCY_REQUEST_IN_PROGRESS",
                "The original upload is still being processed. Retry shortly.",
                409,
            )
        transaction = db.session.get(Transaction, record.resource_id)
        if transaction is None or transaction.user_id != user.id or transaction.receipt is None:
            raise ReceiptFailure(
                "IDEMPOTENCY_RESOURCE_UNAVAILABLE",
                "The original upload result is unavailable.",
                409,
            )
        audit_event(
            "receipt.upload_replayed",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="transaction",
            target_id=transaction.id,
        )
        db.session.commit()
        return _projection(transaction, transaction.receipt, True)

    transaction_id = uuid.uuid4()
    receipt_id = uuid.uuid4()
    original_key = generated_key(
        f"receipts/{user.id}/{transaction_id}/original", inspected.extension
    )
    thumbnail_key = generated_key(
        f"receipts/{user.id}/{transaction_id}/derived/{THUMBNAIL_VERSION}", "jpg"
    )
    written_keys: list[str] = []
    try:
        exact_count, near_count = _duplicate_counts(inspected)
        quality_warnings = list(inspected.quality_warnings)
        if exact_count:
            quality_warnings.append("POSSIBLE_EXACT_DUPLICATE")
        if near_count:
            quality_warnings.append("POSSIBLE_NEAR_DUPLICATE")

        original = storage.put_bytes(
            original_key,
            inspected.content,
            inspected.media_type,
            {"sha256": inspected.sha256, "evidence": "immutable-original"},
        )
        written_keys.append(original.key)
        derivative = storage.put_bytes(
            thumbnail_key,
            inspected.thumbnail,
            "image/jpeg",
            {"source-sha256": inspected.sha256, "version": THUMBNAIL_VERSION},
        )
        written_keys.append(derivative.key)

        transaction = Transaction(id=transaction_id, user_id=user.id, status="UPLOADED")
        receipt = Receipt(
            id=receipt_id,
            transaction_id=transaction_id,
            object_key=original.key,
            original_filename=inspected.display_filename,
            media_type=inspected.media_type,
            size_bytes=len(inspected.content),
            width_px=inspected.width_px,
            height_px=inspected.height_px,
            sha256=inspected.sha256,
            perceptual_hash=inspected.perceptual_hash,
            quality_score=inspected.quality_score,
            quality_warnings=quality_warnings,
            storage_version=STORAGE_VERSION,
        )
        receipt_derivative = ReceiptDerivative(
            receipt_id=receipt_id,
            kind="THUMBNAIL",
            version=THUMBNAIL_VERSION,
            object_key=derivative.key,
            sha256=sha256_bytes(inspected.thumbnail),
            metadata_json={
                "media_type": "image/jpeg",
                "width_px": inspected.thumbnail_width_px,
                "height_px": inspected.thumbnail_height_px,
                "exif_orientation_applied": True,
            },
        )
        db.session.add_all([transaction, receipt, receipt_derivative])
        record.resource_type = "transaction"
        record.resource_id = transaction_id
        record.response_status = 201
        audit_event(
            "receipt.uploaded",
            "SUCCESS",
            actor_id=user.id,
            roles=roles,
            target_type="transaction",
            target_id=transaction_id,
            metadata={
                "source": source,
                "client_captured_at_present": captured_at is not None,
                "client_metadata_keys": sorted(client_metadata),
                "media_type": inspected.media_type,
                "size_bytes": len(inspected.content),
                "sha256": inspected.sha256,
                "exact_duplicate_candidates": exact_count,
                "near_duplicate_candidates": near_count,
            },
        )
        db.session.commit()
        return _projection(transaction, receipt, False)
    except ReceiptFailure:
        db.session.rollback()
        for key in reversed(written_keys):
            storage.delete(key)
        raise
    except Exception as exc:
        db.session.rollback()
        cleanup_failed = False
        for key in reversed(written_keys):
            try:
                storage.delete(key)
            except Exception:
                cleanup_failed = True
                current_app.logger.exception("receipt_upload_cleanup_failed", extra={"key": key})
        current_app.logger.exception(
            "receipt_upload_failed",
            exc_info=exc,
            extra={"cleanup_failed": cleanup_failed, "transaction_id": str(transaction_id)},
        )
        raise ReceiptFailure(
            "RECEIPT_STORAGE_UNAVAILABLE",
            "The receipt could not be stored safely. No successful upload was recorded.",
            503,
        ) from exc


def receipt_derivative(
    receipt: Receipt, kind: str, *, version: str | None = None
) -> ReceiptDerivative | None:
    query = select(ReceiptDerivative).where(
        ReceiptDerivative.receipt_id == receipt.id,
        ReceiptDerivative.kind == kind,
    )
    if version is not None:
        query = query.where(ReceiptDerivative.version == version)
    return db.session.scalar(
        query.order_by(ReceiptDerivative.created_at.desc(), ReceiptDerivative.id.desc())
    )
