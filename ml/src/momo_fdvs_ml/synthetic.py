"""Deterministic generic receipt and controlled-tamper fixture generation."""

from __future__ import annotations

import json
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageFont

from momo_fdvs_ml.manifest import (
    MANIFEST_SCHEMA_VERSION,
    DatasetManifest,
    ManifestRecord,
    ValidationReport,
    sha256_file,
    validate_manifest,
    write_manifest,
)

GENERATOR_VERSION: Final = "generic-ghana-receipt-generator-v1"
DEFAULT_SEED: Final = 20260810
WIDTH: Final = 640
HEIGHT: Final = 900
GENERIC_PROVIDER: Final = "GENERIC_MOMO"
PERMISSION_REFERENCE: Final = "SYNTHETIC_GENERATOR_V1"
CONTROLLED_OPERATION_SETS: Final[tuple[tuple[str, ...], ...]] = (
    ("amount_replace", "clone_paste"),
    ("reference_replace", "recompress"),
    ("recipient_replace", "font_mismatch"),
    ("crop", "misalignment"),
    ("amount_replace", "reference_replace", "recompress"),
    ("recipient_replace", "clone_paste", "crop"),
)


@dataclass(frozen=True)
class GeneratedDataset:
    """Paths and hashes produced by one controlled generation run."""

    root: Path
    manifest: DatasetManifest
    validation: ValidationReport
    report_json: Path
    report_markdown: Path


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def assign_group_splits(group_ids: Sequence[str], *, seed: int) -> dict[str, str]:
    """Assign complete source groups before any derivative is generated."""

    unique = sorted(set(group_ids))
    if len(unique) < 3:
        raise ValueError("at least three source groups are required for train/validation/test")
    shuffled = list(unique)
    random.Random(seed).shuffle(shuffled)  # noqa: S311 - deterministic research split
    validation_count = max(1, round(len(shuffled) * 0.2))
    test_count = max(1, round(len(shuffled) * 0.2))
    train_count = len(shuffled) - validation_count - test_count
    if train_count < 1:
        raise ValueError("split allocation leaves no training source group")
    split_by_group: dict[str, str] = {}
    for group in shuffled[:train_count]:
        split_by_group[group] = "train"
    for group in shuffled[train_count : train_count + validation_count]:
        split_by_group[group] = "validation"
    for group in shuffled[train_count + validation_count :]:
        split_by_group[group] = "test"
    return split_by_group


def render_generic_receipt(*, group_number: int, seed: int) -> Image.Image:
    """Render a non-branded receipt containing only explicit demonstration data."""

    rng = random.Random(seed)  # noqa: S311 - deterministic synthetic texture
    image = Image.new("RGB", (WIDTH, HEIGHT), (247, 244, 235))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (42, 28, 598, 870), radius=18, fill=(255, 255, 252), outline=(43, 63, 58), width=3
    )
    draw.rectangle((42, 28, 598, 152), fill=(27, 78, 68))
    draw.text((80, 56), "GENERIC MOBILE MONEY", font=_font(30), fill="white")
    draw.text((133, 102), "DEMONSTRATION RECEIPT", font=_font(19), fill=(220, 244, 235))
    draw.text((90, 188), "TRANSACTION COMPLETE", font=_font(28), fill=(24, 94, 61))
    draw.line((80, 238, 560, 238), fill=(190, 197, 191), width=2)

    fields = (
        ("Amount", f"GHS {25 + group_number * 7}.00", 288),
        ("Recipient", f"DEMO RECIPIENT {group_number:04d}", 366),
        ("Reference", f"DEMO-{group_number:04d}", 444),
        ("Phone", f"XXX XXX {group_number:04d}", 522),
        ("Date", f"2026-08-{group_number:02d} 10:30", 600),
    )
    for label, value, y in fields:
        draw.text((82, y), label.upper(), font=_font(17), fill=(93, 105, 100))
        draw.text((255, y - 4), value, font=_font(23), fill=(28, 34, 32))
        draw.line((80, y + 45, 560, y + 45), fill=(229, 232, 228), width=1)

    for _ in range(90):
        x = rng.randrange(56, 584)
        y = rng.randrange(170, 840)
        shade = rng.randrange(230, 246)
        draw.point((x, y), fill=(shade, shade, shade))

    draw.text((105, 713), "SYNTHETIC / NO PERSONAL DATA", font=_font(22), fill=(126, 72, 37))
    draw.text((98, 760), "NOT A PROVIDER OR CUSTOMER RECORD", font=_font(17), fill=(89, 89, 89))
    draw.rectangle((80, 806, 560, 835), outline=(190, 197, 191), width=1)
    draw.text((153, 811), GENERATOR_VERSION, font=_font(13), fill=(96, 103, 100))
    return image


def _replace_text(
    image: Image.Image,
    *,
    box: tuple[int, int, int, int],
    text: str,
    font_size: int = 23,
    offset_x: int = 0,
) -> None:
    draw = ImageDraw.Draw(image)
    draw.rectangle(box, fill=(255, 255, 252))
    draw.text((box[0] + offset_x, box[1] + 4), text, font=_font(font_size), fill=(34, 35, 34))


def apply_controlled_operations(
    source: Image.Image, operations: Sequence[str]
) -> tuple[Image.Image, list[dict[str, object]], bool]:
    """Apply declared controlled edits and return evidence coordinates."""

    image = source.copy()
    metadata: list[dict[str, object]] = []
    should_recompress = False
    for operation in operations:
        if operation == "amount_replace":
            box = (250, 275, 545, 330)
            _replace_text(image, box=box, text="GHS 9,999.00")
            metadata.append({"name": operation, "box": list(box)})
        elif operation == "reference_replace":
            box = (250, 430, 545, 485)
            _replace_text(image, box=box, text="DEMO-ALTERED")
            metadata.append({"name": operation, "box": list(box)})
        elif operation == "recipient_replace":
            box = (250, 352, 545, 407)
            _replace_text(image, box=box, text="DEMO RECIPIENT ALTERED")
            metadata.append({"name": operation, "box": list(box)})
        elif operation == "crop":
            box = (18, 24, WIDTH - 14, HEIGHT - 20)
            image = image.crop(box).resize((WIDTH, HEIGHT), Image.Resampling.BICUBIC)
            metadata.append({"name": operation, "box": list(box)})
        elif operation == "clone_paste":
            source_box = (440, 620, 540, 680)
            target_box = (92, 620, 192, 680)
            image.paste(image.crop(source_box), target_box)
            metadata.append(
                {
                    "name": operation,
                    "box": list(target_box),
                    "source_box": list(source_box),
                }
            )
        elif operation == "misalignment":
            box = (250, 275, 545, 330)
            _replace_text(image, box=box, text="GHS 777.00", offset_x=38)
            metadata.append({"name": operation, "box": list(box)})
        elif operation == "font_mismatch":
            box = (250, 352, 560, 412)
            _replace_text(image, box=box, text="DEMO RECIPIENT ALTERED", font_size=30)
            metadata.append({"name": operation, "box": list(box)})
        elif operation == "recompress":
            should_recompress = True
            metadata.append({"name": operation, "box": [0, 0, WIDTH, HEIGHT], "quality": 46})
        else:
            raise ValueError(f"unsupported controlled operation: {operation}")
    return image, metadata, should_recompress


def _save_image(image: Image.Image, path: Path, *, recompress: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if recompress:
        image.save(
            path, format="JPEG", quality=46, optimize=False, progressive=False, subsampling=2
        )
    else:
        image.save(path, format="PNG", compress_level=9, optimize=False)


def _record(
    *,
    sample_id: str,
    relative_path: str,
    path: Path,
    source_group_id: str,
    parent_sample_id: str,
    source_type: str,
    label: str,
    operations: Sequence[str],
    metadata: Sequence[dict[str, object]],
    split: str,
    seed: int,
) -> ManifestRecord:
    return ManifestRecord(
        sample_id=sample_id,
        relative_path=relative_path,
        private_object_id="",
        sha256=sha256_file(path),
        source_group_id=source_group_id,
        parent_sample_id=parent_sample_id,
        source_type=source_type,
        provider_code=GENERIC_PROVIDER,
        label=label,
        tamper_operations=tuple(operations),
        tamper_metadata=(
            ""
            if not operations
            else json.dumps({"operations": metadata}, sort_keys=True, separators=(",", ":"))
        ),
        split=split,
        consent_or_licence_reference=PERMISSION_REFERENCE,
        contains_personal_data=False,
        anonymisation_status="not_applicable",
        generated_seed=seed,
        notes="Generic controlled demonstration; no provider branding or personal data.",
    )


def _write_split_files(root: Path, manifest: DatasetManifest) -> None:
    split_root = root / "splits"
    split_root.mkdir(parents=True, exist_ok=True)
    for split in ("train", "validation", "test"):
        lines = sorted(record.sample_id for record in manifest.records if record.split == split)
        (split_root / f"{split}.txt").write_text(
            "".join(f"{line}\n" for line in lines), encoding="utf-8", newline="\n"
        )


def _dataset_report(
    *, manifest: DatasetManifest, validation: ValidationReport, seed: int
) -> dict[str, object]:
    group_distribution = Counter(
        {
            split: len(
                {record.source_group_id for record in manifest.records if record.split == split}
            )
            for split in ("train", "validation", "test")
        }
    )
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generation_seed": seed,
        "dataset_scope": "synthetic_and_controlled_only",
        "provider_scope": "generic_demonstration_not_provider_specific",
        "manifest_hash": manifest.manifest_hash,
        "split_hash": manifest.split_hash,
        "record_count": validation.record_count,
        "source_group_count": validation.group_count,
        "split_sample_counts": dict(sorted(validation.split_counts.items())),
        "split_group_counts": dict(sorted(group_distribution.items())),
        "label_counts": dict(sorted(validation.label_counts.items())),
        "source_type_counts": dict(sorted(validation.source_type_counts.items())),
        "validation_error_count": len(validation.errors),
        "validation_warning_count": len(validation.warnings),
        "training_executed": False,
        "model_metrics": None,
        "limitations": [
            "All committed images are generic controlled demonstrations.",
            "They do not represent provider-wide layouts, users or real fraud prevalence.",
            "Controlled edits do not cover all real manipulation techniques.",
            "No model was fit or evaluated in P10; no performance claim is available.",
        ],
    }


def _write_report(root: Path, report: dict[str, object]) -> tuple[Path, Path]:
    json_path = root / "dataset_report.json"
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    markdown_path = root / "DATASET_REPORT.md"
    split_counts = report["split_sample_counts"]
    label_counts = report["label_counts"]
    source_counts = report["source_type_counts"]
    assert isinstance(split_counts, dict)
    assert isinstance(label_counts, dict)
    assert isinstance(source_counts, dict)
    lines = [
        "# P10 Controlled Dataset Report",
        "",
        f"- Manifest schema: `{report['schema_version']}`",
        f"- Generator: `{report['generator_version']}`",
        f"- Generation seed: `{report['generation_seed']}`",
        f"- Canonical manifest SHA-256: `{report['manifest_hash']}`",
        f"- Source-group split SHA-256: `{report['split_hash']}`",
        (
            f"- Samples: `{report['record_count']}` across "
            f"`{report['source_group_count']}` source groups"
        ),
        f"- Split samples: `{json.dumps(split_counts, sort_keys=True)}`",
        f"- Labels: `{json.dumps(label_counts, sort_keys=True)}`",
        f"- Source types: `{json.dumps(source_counts, sort_keys=True)}`",
        "- Validation: `0 errors`; no source group crosses splits",
        "- Training executed: `false`",
        "- Model metrics: `not available`",
        "",
        "## Scope and limitations",
        "",
    ]
    limitations = report["limitations"]
    assert isinstance(limitations, list)
    lines.extend(f"- {item}" for item in limitations)
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return json_path, markdown_path


def generate_controlled_dataset(
    root: Path, *, seed: int = DEFAULT_SEED, group_count: int = 6
) -> GeneratedDataset:
    """Generate governed originals and tamper variants with stable hashes."""

    if group_count < 3:
        raise ValueError("group_count must be at least three")
    root.mkdir(parents=True, exist_ok=True)
    image_root = root / "images"
    group_ids = [f"controlled-group-{index:04d}" for index in range(1, group_count + 1)]
    split_by_group = assign_group_splits(group_ids, seed=seed)
    records: list[ManifestRecord] = []
    for index, group_id in enumerate(group_ids, start=1):
        sample_seed = seed + index
        split = split_by_group[group_id]
        original_id = f"controlled-original-{index:04d}"
        original_relative = f"images/{original_id}.png"
        original_path = image_root / f"{original_id}.png"
        original = render_generic_receipt(group_number=index, seed=sample_seed)
        _save_image(original, original_path)
        records.append(
            _record(
                sample_id=original_id,
                relative_path=original_relative,
                path=original_path,
                source_group_id=group_id,
                parent_sample_id="",
                source_type="synthetic",
                label="genuine",
                operations=(),
                metadata=(),
                split=split,
                seed=sample_seed,
            )
        )

        operations = CONTROLLED_OPERATION_SETS[(index - 1) % len(CONTROLLED_OPERATION_SETS)]
        tampered, metadata, recompress = apply_controlled_operations(original, operations)
        tamper_id = f"controlled-tamper-{index:04d}"
        suffix = ".jpg" if recompress else ".png"
        tamper_relative = f"images/{tamper_id}{suffix}"
        tamper_path = image_root / f"{tamper_id}{suffix}"
        _save_image(tampered, tamper_path, recompress=recompress)
        records.append(
            _record(
                sample_id=tamper_id,
                relative_path=tamper_relative,
                path=tamper_path,
                source_group_id=group_id,
                parent_sample_id=original_id,
                source_type="controlled_tamper",
                label="fraudulent",
                operations=operations,
                metadata=metadata,
                split=split,
                seed=sample_seed,
            )
        )

    manifest = write_manifest(root / "manifest.csv", records)
    validation = validate_manifest(manifest, root=root)
    validation.raise_for_errors()
    _write_split_files(root, manifest)
    report = _dataset_report(manifest=manifest, validation=validation, seed=seed)
    report_json, report_markdown = _write_report(root, report)
    return GeneratedDataset(
        root=root,
        manifest=manifest,
        validation=validation,
        report_json=report_json,
        report_markdown=report_markdown,
    )


def verify_recorded_report(root: Path, manifest: DatasetManifest) -> tuple[str, ...]:
    """Compare recorded report hashes/counts to current canonical manifest state."""

    path = root / "dataset_report.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (f"unable to read dataset_report.json: {exc}",)
    errors: list[str] = []
    expected = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_hash": manifest.manifest_hash,
        "split_hash": manifest.split_hash,
        "record_count": len(manifest.records),
        "training_executed": False,
        "model_metrics": None,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"recorded {key} does not match manifest")
    return tuple(errors)
