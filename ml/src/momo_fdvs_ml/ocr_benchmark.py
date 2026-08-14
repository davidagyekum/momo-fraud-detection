"""Split-bound pretrained OCR adapters, benchmark metrics and private bundles."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
import shutil
import statistics
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Protocol, cast

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from momo_fdvs_ml.ghana_pipeline import load_private_text_development_records
from momo_fdvs_ml.ocr_parser import (
    CRITICAL_FIELDS,
    FIELD_CONFIDENCE_THRESHOLD,
    OCR_FIELD_SCHEMA_VERSION,
    OCR_PARSER_VERSION,
    ParserResult,
    parse_momo_text,
)

OCR_ADAPTER_SCHEMA_VERSION: Final = "ocr-adapter-result-v1"
OCR_DEVELOPMENT_BUNDLE_VERSION: Final = "ghana-ocr-development-bundle-v1"
OCR_BENCHMARK_REPORT_VERSION: Final = "ghana-ocr-benchmark-report-v1"
OCR_SELECTED_BUNDLE_VERSION: Final = "ghana-ocr-selected-bundle-v1"
OCR_BENCHMARK_VERSION: Final = "ghana-ocr-benchmark-v1"
OCR_BENCHMARK_CONFIG_VERSION: Final = "ocr-benchmark-config-v1"
REQUIRED_ENGINES: Final = ("tesseract", "easyocr", "paddleocr")
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


class OCRBenchmarkError(RuntimeError):
    """Raised when OCR benchmarking would violate an integrity or split boundary."""


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
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_hash(value: Mapping[str, object], hash_field: str) -> str:
    canonical = dict(value)
    canonical.pop(hash_field, None)
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _load_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OCRBenchmarkError(f"unable to read {path.name}") from exc
    if not isinstance(value, dict):
        raise OCRBenchmarkError(f"{path.name} must contain an object")
    return value


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    os.replace(temporary, path)


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
                raise OCRBenchmarkError("tesseract engine is unavailable") from exc
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
                raise OCRBenchmarkError("tesseract returned an invalid token schema") from exc
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
                raise OCRBenchmarkError("easyocr engine is unavailable") from exc
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
            raise OCRBenchmarkError("easyocr inference failed") from exc
        tokens: list[OCRToken] = []
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                raise OCRBenchmarkError("easyocr returned an invalid token schema")
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

    def __init__(self, *, pipeline: object | None = None, device: str = "cpu") -> None:
        if pipeline is None:
            try:
                paddleocr = importlib.import_module("paddleocr")
                pipeline = paddleocr.PaddleOCR(
                    lang="en",
                    device=device,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
            except (ImportError, OSError, RuntimeError) as exc:
                raise OCRBenchmarkError("paddleocr engine is unavailable") from exc
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
            raise OCRBenchmarkError("paddleocr inference failed") from exc
        if len(results) != 1:
            raise OCRBenchmarkError("paddleocr returned an invalid result count")
        payload = results[0].json
        if callable(payload):
            payload = payload()
        if not isinstance(payload, dict):
            raise OCRBenchmarkError("paddleocr returned an invalid result schema")
        data = payload.get("res", payload)
        if not isinstance(data, dict):
            raise OCRBenchmarkError("paddleocr returned an invalid result schema")
        texts = data.get("rec_texts", [])
        scores = data.get("rec_scores", [])
        boxes = data.get("rec_boxes", [])
        if not (len(texts) == len(scores) == len(boxes)):
            raise OCRBenchmarkError("paddleocr returned misaligned tokens")
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


def score_parser_result(
    parser: ParserResult, truth: Mapping[str, object]
) -> dict[str, bool | None]:
    """Score exact normalized fields, leaving unavailable truth out of the denominator."""

    expected = _truth_fields(truth)
    observed = parser.fields
    recipient_expected = expected.get("recipient_name") or expected.get("recipient_wallet")
    recipient_observed = (
        observed["recipient"].normalized
        if expected.get("recipient_name")
        else observed["recipient_wallet"].normalized
    )
    pairs = {
        "amount": (expected.get("amount"), observed["amount"].normalized),
        "reference": (expected.get("reference"), observed["reference"].normalized),
        "timestamp": (expected.get("timestamp"), observed["timestamp"].normalized),
        "recipient": (recipient_expected, recipient_observed),
    }
    return {
        name: None if truth_value is None else truth_value == observed_value
        for name, (truth_value, observed_value) in pairs.items()
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
        configuration_reports.append(
            {
                "configuration_id": config.configuration_id,
                "engine": config.engine,
                "variant": config.variant,
                "engine_options": dict(sorted(config.engine_options.items())),
                "engine_versions": sorted(engine_versions.get(config.engine, set())),
                "metrics": metrics,
                "successful_record_count": len(config_rows),
                "failure_count": sum(
                    failure["configuration_id"] == config.configuration_id for failure in failures
                ),
            }
        )
    engine_status = {
        engine: {
            "measured": any(
                report["engine"] == engine and report["successful_record_count"]
                for report in configuration_reports
            ),
            "versions": sorted(engine_versions.get(engine, set())),
            "incompatibility_documented": any(failure["engine"] == engine for failure in failures),
        }
        for engine in REQUIRED_ENGINES
    }
    development_manifest = _load_object(development_manifest_path)
    report: dict[str, object] = {
        "schema_version": OCR_BENCHMARK_REPORT_VERSION,
        "benchmark_version": OCR_BENCHMARK_VERSION,
        "development_manifest_sha256": development_manifest.get("manifest_sha256"),
        "partition": "validation",
        "stage": "screen" if source_group_limit is not None else "full",
        "selection_eligible": source_group_limit is None,
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
            if isinstance(config, dict) and config.get("engine") == engine
        ]
        if not candidates:
            raise OCRBenchmarkError("OCR screen omitted a required engine")

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
        if isinstance(config, dict) and isinstance(config.get("metrics"), dict)
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
        "source_report_sha256": report["report_sha256"],
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
    if (
        bundle.get("schema_version") != OCR_SELECTED_BUNDLE_VERSION
        or bundle.get("parser_version") != OCR_PARSER_VERSION
        or bundle.get("field_schema_version") != OCR_FIELD_SCHEMA_VERSION
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
