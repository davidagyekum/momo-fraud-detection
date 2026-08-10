"""Private Keras image-model verification, deterministic preprocessing and inference."""

from __future__ import annotations

import hashlib
import importlib
import io
import json
import math
import re
import time
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlparse

import numpy as np
from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from momo_fdvs.models import ModelVersion

IMAGE_INPUT_HEIGHT: Final = 224
IMAGE_INPUT_WIDTH: Final = 224
IMAGE_INPUT_CHANNELS: Final = 3
IMAGE_PREPROCESSING_VERSION: Final = "image-rgb224-minus1-to1-v1"
IMAGE_RANDOM_SEED: Final = 20260812
SHA256_PATTERN: Final = re.compile(r"[0-9a-f]{64}")


class ImageModelFailure(RuntimeError):
    """A safe, machine-readable image-model failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def preprocessing_schema_payload() -> dict[str, object]:
    return {
        "version": IMAGE_PREPROCESSING_VERSION,
        "input": {
            "height": IMAGE_INPUT_HEIGHT,
            "width": IMAGE_INPUT_WIDTH,
            "channels": IMAGE_INPUT_CHANNELS,
            "colour_mode": "RGB",
            "exif_orientation": "transpose_before_colour_conversion",
            "resize": "Pillow_BILINEAR",
            "dtype": "float32",
            "normalisation": "pixel / 127.5 - 1.0",
            "range": [-1.0, 1.0],
        },
        "classes": ["ORIGINAL", "CONTROLLED_TAMPERED"],
        "positive_class": "CONTROLLED_TAMPERED",
        "augmentation": {
            "training_only": True,
            "seed": IMAGE_RANDOM_SEED,
            "operations": [
                {"name": "RandomRotation", "factor": 0.02},
                {"name": "RandomZoom", "height_factor": 0.05, "width_factor": 0.05},
                {"name": "RandomContrast", "factor": 0.08},
                {
                    "name": "RandomTranslation",
                    "height_factor": 0.02,
                    "width_factor": 0.02,
                },
            ],
            "forbidden": ["horizontal_flip", "vertical_flip", "validation", "test"],
        },
    }


def _canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


IMAGE_PREPROCESSING_SCHEMA_HASH: Final = _canonical_hash(preprocessing_schema_payload())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tensorflow() -> Any:
    try:
        return importlib.import_module("tensorflow")
    except ImportError as exc:
        raise ImageModelFailure(
            "IMAGE_MODEL_RUNTIME_UNAVAILABLE",
            "The TensorFlow image-model runtime is unavailable.",
        ) from exc


def resolve_private_image_artifact(artifact_uri: str) -> Path:
    parsed = urlparse(artifact_uri)
    if parsed.scheme != "private" or parsed.netloc != "image":
        raise ImageModelFailure(
            "IMAGE_MODEL_URI_INVALID", "The image model artifact URI is not supported."
        )
    relative = parsed.path.lstrip("/")
    if not relative or not relative.endswith(".keras"):
        raise ImageModelFailure(
            "IMAGE_MODEL_URI_INVALID", "The image model artifact URI is invalid."
        )
    root = Path(current_app.config["IMAGE_MODEL_ROOT"]).resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ImageModelFailure(
            "IMAGE_MODEL_URI_INVALID", "The image model artifact URI escapes its private root."
        )
    if not candidate.is_file():
        raise ImageModelFailure(
            "IMAGE_MODEL_ARTIFACT_MISSING", "The registered image model artifact is unavailable."
        )
    if candidate.stat().st_size > int(current_app.config["IMAGE_MODEL_MAX_BYTES"]):
        raise ImageModelFailure(
            "IMAGE_MODEL_ARTIFACT_TOO_LARGE",
            "The registered image model artifact exceeds the configured limit.",
        )
    return candidate


def preprocess_image_bytes(payload: bytes) -> np.ndarray:
    """Apply the exact training/inference image contract."""

    if not payload:
        raise ImageModelFailure("IMAGE_MODEL_INPUT_INVALID", "The image payload is empty.")
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.load()
            oriented = ImageOps.exif_transpose(source)
            image = oriented.convert("RGB").resize(
                (IMAGE_INPUT_WIDTH, IMAGE_INPUT_HEIGHT),
                resample=Image.Resampling.BILINEAR,
            )
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise ImageModelFailure(
            "IMAGE_MODEL_INPUT_INVALID", "The image cannot be decoded for model inference."
        ) from exc
    array = np.asarray(image, dtype=np.float32)
    if array.shape != (IMAGE_INPUT_HEIGHT, IMAGE_INPUT_WIDTH, IMAGE_INPUT_CHANNELS):
        raise ImageModelFailure(
            "IMAGE_MODEL_INPUT_INVALID", "The decoded image tensor shape is invalid."
        )
    normalised = array / np.float32(127.5) - np.float32(1.0)
    if not np.isfinite(normalised).all():
        raise ImageModelFailure(
            "IMAGE_MODEL_INPUT_INVALID", "The decoded image tensor is not finite."
        )
    return normalised


def load_verified_image_model(model: ModelVersion) -> Any:
    """Verify type, schema, file bytes and shapes before returning a trusted model."""

    if model.model_type != "IMAGE":
        raise ImageModelFailure("IMAGE_MODEL_TYPE_INVALID", "The registered model is not IMAGE.")
    if not SHA256_PATTERN.fullmatch(model.artifact_sha256):
        raise ImageModelFailure(
            "IMAGE_MODEL_HASH_INVALID", "The registered image artifact hash is invalid."
        )
    if (
        model.input_schema_hash != IMAGE_PREPROCESSING_SCHEMA_HASH
        or model.preprocessing_version != IMAGE_PREPROCESSING_VERSION
    ):
        raise ImageModelFailure(
            "IMAGE_MODEL_SCHEMA_MISMATCH",
            "The image model preprocessing contract does not match the runtime.",
        )
    path = resolve_private_image_artifact(model.artifact_uri)
    if _sha256_file(path) != model.artifact_sha256:
        raise ImageModelFailure(
            "IMAGE_MODEL_HASH_MISMATCH", "The image model artifact failed integrity verification."
        )
    tf = _tensorflow()
    try:
        loaded = tf.keras.models.load_model(path, compile=False, safe_mode=True)
    except Exception as exc:
        raise ImageModelFailure(
            "IMAGE_MODEL_DESERIALISATION_FAILED",
            "The verified image model artifact could not be loaded.",
        ) from exc
    if tuple(loaded.input_shape) != (
        None,
        IMAGE_INPUT_HEIGHT,
        IMAGE_INPUT_WIDTH,
        IMAGE_INPUT_CHANNELS,
    ) or tuple(loaded.output_shape) != (None, 1):
        raise ImageModelFailure(
            "IMAGE_MODEL_SHAPE_INVALID", "The image model input/output shapes are incompatible."
        )
    return loaded


def _threshold(model: ModelVersion) -> float:
    value = model.metrics.get("threshold")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ImageModelFailure(
            "IMAGE_MODEL_THRESHOLD_INVALID", "The image model threshold is missing."
        )
    threshold = float(value)
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise ImageModelFailure(
            "IMAGE_MODEL_THRESHOLD_INVALID", "The image model threshold is invalid."
        )
    return threshold


def predict_image_tampering(model: ModelVersion, payload: bytes) -> dict[str, object]:
    """Return one bounded tamper probability from a verified active artifact."""

    if model.status != "ACTIVE":
        raise ImageModelFailure("IMAGE_MODEL_NOT_ACTIVE", "No active image model is available.")
    started = time.perf_counter()
    loaded = load_verified_image_model(model)
    tensor = preprocess_image_bytes(payload)[np.newaxis, ...]
    try:
        raw = np.asarray(loaded.predict(tensor, verbose=0), dtype=float)
    except Exception as exc:
        raise ImageModelFailure(
            "IMAGE_MODEL_INFERENCE_FAILED", "The image model could not process this receipt."
        ) from exc
    if raw.shape != (1, 1) or not math.isfinite(float(raw[0, 0])):
        raise ImageModelFailure(
            "IMAGE_MODEL_OUTPUT_INVALID", "The image model returned an invalid output."
        )
    probability = float(raw[0, 0])
    if not 0 <= probability <= 1:
        raise ImageModelFailure(
            "IMAGE_MODEL_OUTPUT_INVALID", "The image model returned an invalid probability."
        )
    threshold = _threshold(model)
    return {
        "status": "SUCCESS",
        "model_version_id": str(model.id),
        "model_name": model.name,
        "model_version": model.version,
        "tamper_probability": round(probability, 8),
        "predicted_class": ("CONTROLLED_TAMPERED" if probability >= threshold else "ORIGINAL"),
        "threshold": threshold,
        "preprocessing_version": model.preprocessing_version,
        "preprocessing_schema_hash": model.input_schema_hash,
        "inference_ms": max(0, round((time.perf_counter() - started) * 1000)),
    }
