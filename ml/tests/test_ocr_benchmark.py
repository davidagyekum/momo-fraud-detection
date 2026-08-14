from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import momo_fdvs_ml.ocr_benchmark as ocr_benchmark
from momo_fdvs_ml.ocr_benchmark import (
    OCR_ADAPTER_SCHEMA_VERSION,
    OCR_BENCHMARK_REPORT_VERSION,
    OCR_DEVELOPMENT_BUNDLE_VERSION,
    OCR_SELECTED_BUNDLE_VERSION,
    EasyOCRAdapter,
    OCRBenchmarkError,
    OCRConfiguration,
    PaddleOCRAdapter,
    TesseractAdapter,
    aggregate_configuration_metrics,
    edit_distance,
    engine_inventory,
    load_ocr_benchmark_config,
    load_ocr_development_bundle,
    load_selected_ocr_bundle,
    prepare_ocr_development_bundle,
    preprocessing_variants,
    replay_parser_bundle,
    run_ocr_validation_benchmark,
    safe_failure_result,
    score_parser_result,
    select_engine_finalists,
    select_ocr_configuration,
    text_error_rates,
)
from momo_fdvs_ml.ocr_parser import parse_momo_text

TRAIN_ID = "GHDEV_TRAIN_0001"
VALIDATION_ID = "GHDEV_VALIDATION_0001"
TEST_ID = "GHLOCK_TEST_0001"


def _canonical(value: dict[str, object], field: str) -> str:
    copy = dict(value)
    copy.pop(field, None)
    return hashlib.sha256(
        json.dumps(copy, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _split_manifest(path: Path) -> None:
    manifest: dict[str, object] = {
        "schema_version": "ghana-private-text-frozen-split-v1",
        "locked_test": True,
        "training_executed": False,
        "records": [
            {
                "record_id": TRAIN_ID,
                "source_group_id": "GHGROUP_TRAIN_0001",
                "source_corpus": "screenshot_ocr",
                "split": "train",
                "locked_test": False,
            },
            {
                "record_id": VALIDATION_ID,
                "source_group_id": "GHGROUP_VALIDATION_0001",
                "source_corpus": "screenshot_ocr",
                "split": "validation",
                "locked_test": False,
            },
            {
                "record_id": TEST_ID,
                "source_group_id": "GHGROUP_TEST_0001",
                "source_corpus": "screenshot_ocr",
                "split": "test",
                "locked_test": True,
            },
            {
                "record_id": "GHOWNER_TRAIN_0001",
                "source_group_id": "GHOWNER_GROUP_0001",
                "source_corpus": "owner_iphone_messages",
                "split": "train",
                "locked_test": False,
            },
        ],
    }
    manifest["manifest_sha256"] = _canonical(manifest, "manifest_sha256")
    _write_json(path, manifest)


def _private_fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, Path], Path]:
    repository = tmp_path / "repository"
    repository.mkdir()
    private = tmp_path / "private"
    split = private / "split.json"
    truth_root = private / "truth-source"
    images = private / "source-images"
    _split_manifest(split)
    bindings: dict[str, Path] = {}
    for position, record_id in enumerate((TRAIN_ID, VALIDATION_ID), start=1):
        image_path = images / f"{record_id}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (80, 60), (position * 40, 255, 255)).save(image_path)
        digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
        bindings[record_id] = image_path
        _write_json(
            truth_root / f"{record_id}.json",
            {
                "record_id": record_id,
                "source_sha256": digest,
                "training_executed": False,
                "full_transcript": "MTN MobileMoney Amount GHS 10.00 Reference ABC12345",
                "fields": [
                    {"name": "amount", "normalized": "10.00"},
                    {"name": "reference", "normalized": "ABC12345"},
                ],
            },
        )
    return repository, private, split, bindings, truth_root


def _tesseract_data() -> dict[str, list[object]]:
    return {
        "text": ["Reference", "ABC12345"],
        "conf": ["90", "80"],
        "left": [0, 30],
        "top": [0, 0],
        "width": [25, 40],
        "height": [10, 10],
        "block_num": [1, 1],
        "par_num": [1, 1],
        "line_num": [1, 1],
    }


class _EasyReader:
    def __init__(self, rows: list[object] | None = None, *, fail: bool = False) -> None:
        self.rows = rows or [([[0, 0], [20, 0], [20, 10], [0, 10]], "Text", 0.8)]
        self.fail = fail

    def readtext(self, *_args: object, **_kwargs: object) -> list[object]:
        if self.fail:
            raise RuntimeError("private text must not escape")
        return self.rows


class _PaddleResult:
    def __init__(self, payload: object) -> None:
        self.json = payload


class _PaddlePipeline:
    def __init__(self, payloads: list[object]) -> None:
        self.payloads = payloads

    def predict(self, _image: object) -> list[_PaddleResult]:
        return [_PaddleResult(payload) for payload in self.payloads]


def test_all_adapters_return_the_same_versioned_schema() -> None:
    image = Image.new("RGB", (40, 20), "white")
    tesseract = TesseractAdapter(
        runner=lambda _image, config: _tesseract_data(), version="5.test"
    ).extract(image, configuration="tesseract-original")
    easy = EasyOCRAdapter(reader=_EasyReader()).extract(image, configuration="easy-original")
    paddle = PaddleOCRAdapter(
        pipeline=_PaddlePipeline(
            [
                {
                    "res": {
                        "rec_texts": ["Text"],
                        "rec_scores": [0.8],
                        "rec_boxes": [[0, 0, 20, 10]],
                    }
                }
            ]
        )
    ).extract(image, configuration="paddle-original")

    for result, engine in (
        (tesseract, "tesseract"),
        (easy, "easyocr"),
        (paddle, "paddleocr"),
    ):
        assert result.schema_version == OCR_ADAPTER_SCHEMA_VERSION
        assert result.engine == engine
        assert result.raw_text
        assert result.tokens
        assert result.as_dict(include_text=False).get("raw_text") is None
        assert result.as_dict(include_text=False)["tokens"] == []
    assert tesseract.tokens[0].text == "Reference"
    assert easy.tokens[0].bbox == (0, 0, 20, 10)
    assert paddle.tokens[0].bbox == (0, 0, 20, 10)


def test_tesseract_rejects_invalid_token_schema_and_reports_empty_text() -> None:
    image = Image.new("RGB", (20, 20))
    empty = {key: [] for key in _tesseract_data()}
    result = TesseractAdapter(runner=lambda *_: empty, version="5.test").extract(
        image, configuration="empty"
    )
    assert result.warnings == ("OCR_NO_TEXT",)
    broken = _tesseract_data()
    broken["conf"] = []
    with pytest.raises(OCRBenchmarkError, match="invalid token schema"):
        TesseractAdapter(runner=lambda *_: broken).extract(image, configuration="broken")


def test_easyocr_and_paddle_fail_closed_on_bad_runtime_results() -> None:
    image = Image.new("RGB", (20, 20))
    with pytest.raises(OCRBenchmarkError, match="inference failed"):
        EasyOCRAdapter(reader=_EasyReader(fail=True)).extract(image, configuration="bad")
    with pytest.raises(OCRBenchmarkError, match="invalid token schema"):
        EasyOCRAdapter(reader=_EasyReader(rows=[["bad"]])).extract(image, configuration="bad")
    with pytest.raises(OCRBenchmarkError, match="result count"):
        PaddleOCRAdapter(pipeline=_PaddlePipeline([])).extract(image, configuration="bad")
    with pytest.raises(OCRBenchmarkError, match="result schema"):
        PaddleOCRAdapter(pipeline=_PaddlePipeline(["bad"])).extract(image, configuration="bad")
    with pytest.raises(OCRBenchmarkError, match="misaligned"):
        PaddleOCRAdapter(
            pipeline=_PaddlePipeline([{"rec_texts": ["a"], "rec_scores": [], "rec_boxes": []}])
        ).extract(image, configuration="bad")


def test_paddleocr_disables_mkldnn_for_ppocrv6_cpu_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class PaddleModule:
        @staticmethod
        def PaddleOCR(**options: object) -> _PaddlePipeline:
            captured.update(options)
            return _PaddlePipeline(
                [{"rec_texts": ["Text"], "rec_scores": [0.8], "rec_boxes": [[0, 0, 20, 10]]}]
            )

    real_import = ocr_benchmark.importlib.import_module
    monkeypatch.setattr(
        ocr_benchmark.importlib,
        "import_module",
        lambda name: PaddleModule if name == "paddleocr" else real_import(name),
    )

    PaddleOCRAdapter(device="cpu")

    assert captured["device"] == "cpu"
    assert captured["ocr_version"] == "PP-OCRv6"
    assert captured["enable_mkldnn"] is False


def test_preprocessing_grid_is_deterministic_and_field_crop_is_bounded() -> None:
    import io

    stream = io.BytesIO()
    Image.new("RGB", (100, 80), "white").save(stream, format="PNG")
    first = preprocessing_variants(stream.getvalue(), field_boxes=[[10, 15, 40, 20]])
    second = preprocessing_variants(stream.getvalue(), field_boxes=[[10, 15, 40, 20]])
    assert {"original_rgb", "normalized_rgb", "grayscale_contrast", "field_region"}.issubset(first)
    assert first["normalized_rgb"].width == 300
    assert first["field_region"].size == (40, 20)
    assert first["grayscale_contrast"].tobytes() == second["grayscale_contrast"].tobytes()
    with pytest.raises(OCRBenchmarkError, match="could not be decoded"):
        preprocessing_variants(b"not-an-image")


def test_configuration_identity_and_inventory_are_stable() -> None:
    left = OCRConfiguration("tesseract", "original_rgb", {"psm": 6})
    right = OCRConfiguration("tesseract", "original_rgb", {"psm": 6})
    changed = OCRConfiguration("tesseract", "original_rgb", {"psm": 11})
    assert left.configuration_id == right.configuration_id
    assert left.configuration_id != changed.configuration_id
    inventory = engine_inventory()
    assert set(inventory) == {"tesseract", "easyocr", "paddleocr"}
    assert inventory["tesseract"]["license"] == "Apache-2.0"


def test_committed_benchmark_config_matches_code_policy_and_rejects_drift(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    config_path = repository_root / "ml/configs/ocr_benchmark_v2.json"
    config = load_ocr_benchmark_config(config_path)
    assert config["data_policy"]["locked_test_access_allowed"] is False  # type: ignore[index]
    assert config["selection_policy"] == {
        "complete_record_coverage_required": True,
        "required_engines_available": True,
    }
    drifted = json.loads(config_path.read_text(encoding="utf-8"))
    drifted["release_gates"]["amount_exact"] = 0.5
    drifted_path = tmp_path / "drifted.json"
    _write_json(drifted_path, drifted)
    with pytest.raises(OCRBenchmarkError, match="drifted"):
        load_ocr_benchmark_config(drifted_path)

    incompatible = json.loads(config_path.read_text(encoding="utf-8"))
    paddle = next(engine for engine in incompatible["engines"] if engine["engine"] == "paddleocr")
    paddle["options"]["enable_mkldnn"] = True
    incompatible_path = tmp_path / "incompatible.json"
    _write_json(incompatible_path, incompatible)
    with pytest.raises(OCRBenchmarkError, match="drifted"):
        load_ocr_benchmark_config(incompatible_path)


def test_private_development_bundle_contains_only_train_and_validation(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == OCR_DEVELOPMENT_BUNDLE_VERSION
    assert manifest["benchmark_version"] == "ghana-ocr-benchmark-v1"
    assert manifest["record_count"] == 2
    assert manifest["locked_test_included"] is False
    assert {record["record_id"] for record in manifest["records"]} == {
        TRAIN_ID,
        VALIDATION_ID,
    }
    assert len(load_ocr_development_bundle(manifest_path, partition="train")) == 1
    assert len(load_ocr_development_bundle(manifest_path, partition="validation")) == 1
    with pytest.raises(OCRBenchmarkError, match="train or validation"):
        load_ocr_development_bundle(manifest_path, partition="test")


def test_private_bundle_packager_writes_deterministic_posix_members(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    packager = getattr(ocr_benchmark, "package_ocr_development_bundle", None)
    assert packager is not None
    first = private / "first.zip"
    second = private / "second.zip"
    first_hash = packager(
        manifest_path=manifest_path,
        output_path=first,
        repository_root=repository,
    )
    second_hash = packager(
        manifest_path=manifest_path,
        output_path=second,
        repository_root=repository,
    )

    assert first_hash == second_hash == hashlib.sha256(first.read_bytes()).hexdigest()
    with zipfile.ZipFile(first) as archive:
        members = archive.namelist()
        assert members == sorted(members)
        assert all("\\" not in member for member in members)
        assert "development-manifest.json" in members
        assert f"images/{TRAIN_ID}.png" in members
        assert f"truth/{VALIDATION_ID}.json" in members
        extracted = private / "extracted"
        archive.extractall(extracted)
    assert (
        len(
            load_ocr_development_bundle(
                extracted / "development-manifest.json", partition="validation"
            )
        )
        == 1
    )
    assert (extracted / f"images/{VALIDATION_ID}.png").is_file()


def test_private_bundle_packager_rejects_unsafe_or_drifted_inputs(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )

    with pytest.raises(OCRBenchmarkError, match="outside the repository"):
        ocr_benchmark.package_ocr_development_bundle(
            manifest_path=manifest_path,
            output_path=repository / "private-leak.zip",
            repository_root=repository,
        )
    with pytest.raises(OCRBenchmarkError, match=r"\.zip extension"):
        ocr_benchmark.package_ocr_development_bundle(
            manifest_path=manifest_path,
            output_path=private / "bundle.tar",
            repository_root=repository,
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["records"][0]["image_path"] = f"images\\{TRAIN_ID}.png"
    manifest["manifest_sha256"] = ocr_benchmark._canonical_hash(manifest, "manifest_sha256")
    _write_json(manifest_path, manifest)
    with pytest.raises(OCRBenchmarkError, match="POSIX separators"):
        ocr_benchmark.package_ocr_development_bundle(
            manifest_path=manifest_path,
            output_path=private / "bad-member.zip",
            repository_root=repository,
        )


def test_private_bundle_packager_rejects_duplicate_and_hash_drift(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    train = next(record for record in manifest["records"] if record["split"] == "train")
    validation = next(record for record in manifest["records"] if record["split"] == "validation")
    validation["image_path"] = train["image_path"]
    validation["image_sha256"] = train["image_sha256"]
    manifest["manifest_sha256"] = ocr_benchmark._canonical_hash(manifest, "manifest_sha256")
    _write_json(manifest_path, manifest)
    with pytest.raises(OCRBenchmarkError, match="duplicated"):
        ocr_benchmark.package_ocr_development_bundle(
            manifest_path=manifest_path,
            output_path=private / "duplicate.zip",
            repository_root=repository,
        )

    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "fresh-bundle",
        repository_root=repository,
    )
    (manifest_path.parent / f"images/{TRAIN_ID}.png").write_bytes(b"changed")
    with pytest.raises(OCRBenchmarkError, match="hash changed"):
        ocr_benchmark.package_ocr_development_bundle(
            manifest_path=manifest_path,
            output_path=private / "drifted.zip",
            repository_root=repository,
        )


def test_private_bundle_packager_cleans_temporary_file_on_publish_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated publish failure")

    monkeypatch.setattr(ocr_benchmark.os, "replace", fail_replace)
    with pytest.raises(OCRBenchmarkError, match="unable to package"):
        ocr_benchmark.package_ocr_development_bundle(
            manifest_path=manifest_path,
            output_path=private / "failed.zip",
            repository_root=repository,
        )
    assert list(private.glob(".failed.zip.*.tmp")) == []


def test_bundle_builder_rejects_locked_extra_missing_and_identity_drift(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    with pytest.raises(OCRBenchmarkError, match="locked-test"):
        prepare_ocr_development_bundle(
            split_manifest_path=split,
            image_bindings={**bindings, TEST_ID: next(iter(bindings.values()))},
            truth_root=truth_root,
            output_root=private / "extra",
            repository_root=repository,
        )
    with pytest.raises(OCRBenchmarkError, match="do not cover"):
        prepare_ocr_development_bundle(
            split_manifest_path=split,
            image_bindings={TRAIN_ID: bindings[TRAIN_ID]},
            truth_root=truth_root,
            output_root=private / "missing",
            repository_root=repository,
        )
    bindings[TRAIN_ID].write_bytes(b"changed")
    with pytest.raises(OCRBenchmarkError, match="identity mismatch"):
        prepare_ocr_development_bundle(
            split_manifest_path=split,
            image_bindings=bindings,
            truth_root=truth_root,
            output_root=private / "drift",
            repository_root=repository,
        )


def test_bundle_builder_rejects_repository_paths_and_bad_extensions(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    with pytest.raises(OCRBenchmarkError, match="outside the repository"):
        prepare_ocr_development_bundle(
            split_manifest_path=split,
            image_bindings=bindings,
            truth_root=truth_root,
            output_root=repository / "private-leak",
            repository_root=repository,
        )
    bad = private / "source-images" / "bad.txt"
    bad.write_bytes(bindings[TRAIN_ID].read_bytes())
    bindings[TRAIN_ID] = bad
    truth = json.loads((truth_root / f"{TRAIN_ID}.json").read_text(encoding="utf-8"))
    truth["source_sha256"] = hashlib.sha256(bad.read_bytes()).hexdigest()
    _write_json(truth_root / f"{TRAIN_ID}.json", truth)
    with pytest.raises(OCRBenchmarkError, match="extension"):
        prepare_ocr_development_bundle(
            split_manifest_path=split,
            image_bindings=bindings,
            truth_root=truth_root,
            output_root=private / "bad-extension",
            repository_root=repository,
        )


def test_bundle_loader_rejects_hash_lock_and_record_drift(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["locked_test_included"] = True
    _write_json(manifest_path, manifest)
    with pytest.raises(OCRBenchmarkError, match="lock state"):
        load_ocr_development_bundle(manifest_path, partition="validation")
    manifest["locked_test_included"] = False
    manifest["manifest_sha256"] = _canonical(manifest, "manifest_sha256")
    manifest["records"] = "bad"
    manifest["manifest_sha256"] = _canonical(manifest, "manifest_sha256")
    _write_json(manifest_path, manifest)
    with pytest.raises(OCRBenchmarkError, match="records are invalid"):
        load_ocr_development_bundle(manifest_path, partition="validation")


def test_edit_distance_and_text_error_rates_cover_empty_and_word_changes() -> None:
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance([], []) == 0
    assert text_error_rates("Mobile Money", "Mobile Money") == (0.0, 0.0)
    cer, wer = text_error_rates("Mobile Money", "Mobile Cash")
    assert 0 < cer < 1
    assert wer == 0.5


def test_field_scoring_uses_normalized_truth_and_excludes_unavailable_fields() -> None:
    parser = parse_momo_text("Amount GHS 10.00 Reference: ABC12345")
    truth = {
        "fields": [
            {"name": "amount", "normalized": "10.00"},
            {"name": "reference", "normalized": "ABC12345"},
        ]
    }
    scores = score_parser_result(parser, truth)
    assert scores == {
        "amount": True,
        "reference": True,
        "timestamp": None,
        "recipient": None,
    }
    with pytest.raises(OCRBenchmarkError, match="truth fields"):
        score_parser_result(parser, {"fields": "bad"})


def test_field_comparison_uses_wallet_identity_for_match_availability_and_warnings() -> None:
    parser = parse_momo_text("Reference ABC12345")
    fields = dict(parser.fields)
    fields["recipient"] = replace(
        fields["recipient"],
        raw=None,
        normalized=None,
        confidence=0.0,
        available=False,
        warnings=("RECIPIENT_NOT_FOUND",),
    )
    fields["recipient_wallet"] = replace(
        fields["recipient_wallet"],
        raw="+233240000013",
        normalized="+233240000013",
        confidence=0.8,
        available=True,
        warnings=("WALLET_UNLABELLED",),
    )

    comparisons = ocr_benchmark.compare_parser_result(
        replace(parser, fields=fields),
        {
            "fields": [
                {"name": "recipient_wallet", "normalized": "+233240000012"},
            ]
        },
    )

    recipient = comparisons["recipient"]
    assert recipient is not None
    assert recipient.aggregate_field == "recipient"
    assert recipient.truth_field == "recipient_wallet"
    assert recipient.observed_field == "recipient_wallet"
    assert recipient.expected_normalized == "+233240000012"
    assert recipient.observed_normalized == "+233240000013"
    assert recipient.matched is False
    assert recipient.available is True
    assert recipient.warnings == ("WALLET_UNLABELLED",)
    assert recipient.truth_subtype == "recipient_wallet_truth"
    assert recipient.secondary_truth_present is False


def test_field_comparison_preserves_name_precedence_and_exposes_secondary_truth() -> None:
    parser = parse_momo_text("Sent to Demo Person +233240000012")

    comparison = ocr_benchmark.compare_parser_result(
        parser,
        {
            "fields": [
                {"name": "recipient_name", "normalized": "DEMO PERSON"},
                {"name": "recipient_wallet", "normalized": "+233240000012"},
            ]
        },
    )["recipient"]

    assert comparison is not None
    assert comparison.truth_field == "recipient_name"
    assert comparison.observed_field == "recipient"
    assert comparison.truth_subtype == "recipient_name_truth"
    assert comparison.secondary_truth_present is True


def test_field_comparison_fails_closed_for_missing_observed_field() -> None:
    parser = parse_momo_text("Reference ABC12345")
    fields = dict(parser.fields)
    fields.pop("recipient_wallet")

    with pytest.raises(OCRBenchmarkError, match="missing required field recipient_wallet"):
        ocr_benchmark.compare_parser_result(
            replace(parser, fields=fields),
            {
                "fields": [
                    {"name": "recipient_wallet", "normalized": "+233240000012"},
                ]
            },
        )


def test_field_comparison_fails_closed_for_missing_unscored_parser_field() -> None:
    parser = parse_momo_text("Amount GHS 10.00 Reference ABC12345")
    fields = dict(parser.fields)
    fields.pop("timestamp")

    with pytest.raises(OCRBenchmarkError, match="missing required field timestamp"):
        ocr_benchmark.compare_parser_result(
            replace(parser, fields=fields),
            {
                "fields": [
                    {"name": "amount", "normalized": "10.00"},
                    {"name": "reference", "normalized": "ABC12345"},
                ]
            },
        )


def test_field_comparison_rejects_normalized_but_unavailable_parser_field() -> None:
    parser = parse_momo_text("Reference ABC12345")
    fields = dict(parser.fields)
    fields["recipient_wallet"] = replace(
        fields["recipient_wallet"],
        raw="+233240000012",
        normalized="+233240000012",
        confidence=0.0,
        available=False,
        warnings=("WALLET_UNAVAILABLE",),
    )

    with pytest.raises(
        OCRBenchmarkError,
        match="availability state is invalid for recipient_wallet",
    ):
        ocr_benchmark.compare_parser_result(
            replace(parser, fields=fields),
            {
                "fields": [
                    {"name": "recipient_wallet", "normalized": "+233240000012"},
                ]
            },
        )


def test_field_scoring_uses_first_ordered_truth_occurrence() -> None:
    parser = parse_momo_text("Amount GHS 10.00")
    truth = {
        "fields": [
            {"name": "amount", "normalized": "10.00"},
            {"name": "amount", "normalized": "11.00"},
        ]
    }

    comparison = ocr_benchmark.compare_parser_result(parser, truth)["amount"]

    assert comparison is not None
    assert comparison.expected_normalized == "10.00"
    assert comparison.matched is True
    assert score_parser_result(parser, truth)["amount"] is True


def test_parser_ceiling_diagnostic_is_aggregate_redacted_and_validation_only(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = (
        "MTN MobileMoney Amount GHS 10.00 sent to Demo Person "
        "on 14/08/2026 10:30. Reference ABC12345"
    )
    truth["fields"] = [
        {"name": "amount", "normalized": "10.00"},
        {"name": "reference", "normalized": "ABC12345"},
        {"name": "recipient_name", "normalized": "DEMO PERSON"},
        {"name": "timestamp", "normalized": "2026-08-14T10:30:00Z"},
    ]
    _write_json(truth_path, truth)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    output = private / "results" / "parser-ceiling.json"

    ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
        development_manifest_path=manifest_path,
        output_path=output,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert report["schema_version"] == "ghana-ocr-parser-ceiling-report-v3"
    assert report["partition"] == "validation"
    assert report["record_count"] == 1
    assert report["field_scored_record_count"] == {
        "amount": 1,
        "reference": 1,
        "timestamp": 1,
        "recipient": 1,
    }
    assert report["field_exact"] == {
        "amount": 1.0,
        "reference": 1.0,
        "timestamp": 1.0,
        "recipient": 1.0,
    }
    assert report["required_field_scored_record_count"] == 1
    assert report["required_field_parse_success"] == 1.0
    assert report["parser_inconclusive_rate"] == 0.0
    assert report["recipient_truth_subtype_counts"] == {
        "recipient_name_truth": 1,
        "recipient_wallet_truth": 0,
    }
    assert report["recipient_secondary_truth_present_count"] == 0
    assert report["raw_text_persisted"] is False
    assert report["field_values_persisted"] is False
    assert report["record_identifiers_persisted"] is False
    assert report["locked_test_accessed"] is False
    assert "Demo Person" not in serialized
    assert "ABC12345" not in serialized
    assert VALIDATION_ID not in serialized
    assert report["report_sha256"] == _canonical(report, "report_sha256")


def test_parser_ceiling_diagnostic_separates_outcomes_and_counts_stable_warnings(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = (
        "MTN MobileMoney Amount GHS 10.00 sent to Demo Person. Reference ZXCVB123"
    )
    truth["fields"] = [
        {"name": "amount", "normalized": "10.00"},
        {"name": "reference", "normalized": "ABCDE123"},
        {"name": "recipient_name", "normalized": "DEMO PERSON"},
        {"name": "timestamp", "normalized": "2026-08-14T10:30:00Z"},
    ]
    _write_json(truth_path, truth)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    output = private / "results" / "parser-ceiling.json"

    ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
        development_manifest_path=manifest_path,
        output_path=output,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert report["schema_version"] == "ghana-ocr-parser-ceiling-report-v3"
    assert report["field_outcome_counts"] == {
        "amount": {"exact": 1, "mismatch": 0, "unavailable": 0},
        "reference": {"exact": 0, "mismatch": 1, "unavailable": 0},
        "timestamp": {"exact": 0, "mismatch": 0, "unavailable": 1},
        "recipient": {"exact": 1, "mismatch": 0, "unavailable": 0},
    }
    assert report["parser_warning_counts"] == {"TIMESTAMP_NOT_FOUND": 1}
    assert "Demo Person" not in serialized
    assert "ZXCVB123" not in serialized
    assert "ABCDE123" not in serialized
    assert VALIDATION_ID not in serialized


def test_parser_ceiling_diagnostic_uses_wallet_field_for_outcome_and_warning_aggregates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = "Fictional wallet-only transaction"
    truth["fields"] = [
        {"name": "recipient_wallet", "normalized": "+233240000012"},
    ]
    _write_json(truth_path, truth)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    output = private / "results" / "parser-ceiling.json"
    parser = parse_momo_text("Reference ABC12345")
    fields = dict(parser.fields)
    fields["recipient"] = replace(
        fields["recipient"],
        raw=None,
        normalized=None,
        confidence=0.0,
        available=False,
        warnings=("RECIPIENT_NOT_FOUND",),
    )
    fields["recipient_wallet"] = replace(
        fields["recipient_wallet"],
        raw="+233240000013",
        normalized="+233240000013",
        confidence=0.8,
        available=True,
        warnings=("WALLET_UNLABELLED",),
    )
    parser = replace(parser, fields=fields)
    monkeypatch.setattr(ocr_benchmark, "parse_momo_text", lambda *args, **kwargs: parser)

    ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
        development_manifest_path=manifest_path,
        output_path=output,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert report["schema_version"] == "ghana-ocr-parser-ceiling-report-v3"
    assert report["field_scored_record_count"]["recipient"] == 1
    assert report["field_outcome_counts"]["recipient"] == {
        "exact": 0,
        "mismatch": 1,
        "unavailable": 0,
    }
    assert report["recipient_truth_subtype_counts"] == {
        "recipient_name_truth": 0,
        "recipient_wallet_truth": 1,
    }
    assert report["recipient_secondary_truth_present_count"] == 0
    assert report["parser_warning_counts"] == {
        "AMOUNT_NOT_FOUND": 1,
        "RECIPIENT_NOT_FOUND": 1,
        "TIMESTAMP_NOT_FOUND": 1,
    }
    assert report["parser_warning_counts_by_observed_field"] == {
        "recipient_wallet": {"WALLET_UNLABELLED": 1}
    }
    assert report["raw_text_persisted"] is False
    assert report["field_values_persisted"] is False
    assert report["record_identifiers_persisted"] is False
    assert report["locked_test_accessed"] is False
    assert report["training_executed"] is False
    assert "+233240000012" not in serialized
    assert "+233240000013" not in serialized
    assert VALIDATION_ID not in serialized


def test_parser_ceiling_diagnostic_rejects_noncanonical_warning_codes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    output = private / "results" / "parser-ceiling.json"
    real_parse = ocr_benchmark.parse_momo_text

    def parse_with_sensitive_warning(text: str, **kwargs: object) -> object:
        result = real_parse(text, **kwargs)
        fields = dict(result.fields)
        fields["amount"] = replace(fields["amount"], warnings=("AMOUNT_NOT_FOUND: +233555123456",))
        return replace(result, fields=fields)

    monkeypatch.setattr(ocr_benchmark, "parse_momo_text", parse_with_sensitive_warning)
    with pytest.raises(OCRBenchmarkError, match="warning code is invalid"):
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )
    assert not output.exists()


def test_parser_ceiling_diagnostic_reports_sparse_truth_without_inventing_denominators(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    output = private / "results" / "parser-ceiling.json"

    ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
        development_manifest_path=manifest_path,
        output_path=output,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["field_scored_record_count"] == {
        "amount": 1,
        "reference": 1,
        "timestamp": 0,
        "recipient": 0,
    }
    assert report["field_exact"] == {
        "amount": 1.0,
        "reference": 1.0,
        "timestamp": None,
        "recipient": None,
    }
    assert report["required_field_scored_record_count"] == 0
    assert report["required_field_parse_success"] is None
    assert report["parser_warning_counts"] == {
        "RECIPIENT_NOT_FOUND": 1,
        "TIMESTAMP_NOT_FOUND": 1,
    }


def test_parser_ceiling_diagnostic_rejects_invalid_execution_boundaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    output = private / "results" / "parser-ceiling.json"
    with pytest.raises(OCRBenchmarkError, match="clock must be timezone-aware"):
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            now=datetime(2026, 8, 14),
        )

    monkeypatch.setattr(ocr_benchmark, "load_ocr_development_bundle", lambda *_args, **_kw: ())
    with pytest.raises(OCRBenchmarkError, match="has no validation records"):
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )


def _metric_row(
    *,
    matches: dict[str, bool | None] | None = None,
    cer: float = 0.0,
    wer: float = 0.0,
    latency_ms: float = 100.0,
) -> dict[str, Any]:
    return {
        "field_matches": matches
        or {"amount": True, "reference": True, "timestamp": True, "recipient": True},
        "cer": cer,
        "wer": wer,
        "latency_ms": latency_ms,
    }


def test_weighted_selector_applies_declared_weights_gates_and_latency() -> None:
    passing = aggregate_configuration_metrics([_metric_row(), _metric_row(latency_ms=200)])
    assert passing["field_exact"] == {
        "amount": 1.0,
        "reference": 1.0,
        "timestamp": 1.0,
        "recipient": 1.0,
    }
    assert passing["required_field_parse_success"] == 1.0
    assert passing["all_release_gates_passed"] is True
    assert passing["weighted_selection_score"] <= 1.0
    failed = aggregate_configuration_metrics(
        [
            _metric_row(
                matches={
                    "amount": False,
                    "reference": True,
                    "timestamp": None,
                    "recipient": None,
                },
                cer=1,
                wer=1,
            )
        ]
    )
    assert failed["field_exact"]["timestamp"] is None  # type: ignore[index]
    assert failed["required_field_parse_success"] is None
    assert failed["all_release_gates_passed"] is False
    with pytest.raises(OCRBenchmarkError, match="no successful"):
        aggregate_configuration_metrics([])


def test_failure_result_is_unavailable_redacted_and_inconclusive() -> None:
    failure = safe_failure_result(
        engine="easyocr",
        engine_version="1.7.2",
        configuration="easy-original",
        reason_code="OCR_ENGINE_FAILED",
    )
    assert failure["available"] is False
    assert failure["inconclusive"] is True
    assert set(failure["fields"]) == {"amount", "reference", "timestamp", "recipient"}
    assert "raw_text" not in failure


def _full_tesseract_data() -> dict[str, list[object]]:
    text = "MTN MobileMoney Amount GHS 10.00 Reference: ABC12345"
    return {
        "text": [text],
        "conf": ["95"],
        "left": [0],
        "top": [0],
        "width": [70],
        "height": [20],
        "block_num": [1],
        "par_num": [1],
        "line_num": [1],
    }


def _benchmark_configs() -> list[OCRConfiguration]:
    return [
        OCRConfiguration("tesseract", "original_rgb", {"psm": 6}),
        OCRConfiguration("easyocr", "original_rgb", {"gpu": False}),
        OCRConfiguration("paddleocr", "original_rgb", {"device": "cpu"}),
    ]


def test_validation_benchmark_is_redacted_grouped_and_test_locked(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    output = private / "results" / "benchmark.json"
    run_ocr_validation_benchmark(
        development_manifest_path=manifest_path,
        configurations=_benchmark_configs(),
        adapters={
            "tesseract": TesseractAdapter(
                runner=lambda *_: _full_tesseract_data(), version="5.test"
            ),
            "easyocr": EasyOCRAdapter(reader=_EasyReader()),
            "paddleocr": PaddleOCRAdapter(
                pipeline=_PaddlePipeline(
                    [
                        {
                            "rec_texts": ["Text"],
                            "rec_scores": [0.8],
                            "rec_boxes": [[0, 0, 20, 10]],
                        }
                    ]
                )
            ),
        },
        output_path=output,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert report["schema_version"] == OCR_BENCHMARK_REPORT_VERSION
    assert report["partition"] == "validation"
    assert report["record_count"] == 1
    assert report["source_group_count"] == 1
    assert report["locked_test_accessed"] is False
    assert report["raw_text_persisted"] is False
    assert report["tampered_derivative_slice_available"] is False
    assert all(status["measured"] for status in report["engine_status"].values())
    assert "MTN MobileMoney" not in serialized
    assert "ABC12345" not in serialized
    assert "GHLOCK_TEST_0001" not in serialized
    assert report["report_sha256"] == _canonical(report, "report_sha256")


def test_validation_benchmark_documents_engine_incompatibility_and_blocks_selection(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    report_path = private / "results" / "benchmark.json"
    run_ocr_validation_benchmark(
        development_manifest_path=manifest_path,
        configurations=_benchmark_configs(),
        adapters={
            "tesseract": TesseractAdapter(
                runner=lambda *_: _full_tesseract_data(), version="5.test"
            )
        },
        output_path=report_path,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["engine_status"]["tesseract"]["measured"] is True
    assert report["engine_status"]["easyocr"]["incompatibility_documented"] is True
    assert report["engine_status"]["paddleocr"]["incompatibility_documented"] is True
    assert report["selection_eligible"] is False
    with pytest.raises(OCRBenchmarkError, match="boundary"):
        select_ocr_configuration(
            report_path=report_path,
            output_path=private / "results" / "selected.json",
            repository_root=repository,
        )


def test_screen_selection_excludes_high_scoring_partial_coverage_candidate(
    tmp_path: Path,
) -> None:
    partial = OCRConfiguration("tesseract", "field_region", {"psm": 6})
    complete = OCRConfiguration("tesseract", "original_rgb", {"psm": 6})
    easy = OCRConfiguration("easyocr", "original_rgb", {"gpu": False})
    paddle = OCRConfiguration("paddleocr", "original_rgb", {"device": "cpu"})

    def candidate(
        configuration: OCRConfiguration, *, score: float, coverage_complete: bool
    ) -> dict[str, object]:
        return {
            "configuration_id": configuration.configuration_id,
            "engine": configuration.engine,
            "variant": configuration.variant,
            "engine_options": dict(configuration.engine_options),
            "engine_versions": ["5.5.3"] if configuration.engine == "tesseract" else ["test"],
            "metrics": {
                "all_release_gates_passed": score == 1.0,
                "weighted_selection_score": score,
            },
            "successful_record_count": 1 if not coverage_complete else 2,
            "failure_count": 1 if not coverage_complete else 0,
            "record_coverage": 0.5 if not coverage_complete else 1.0,
            "coverage_complete": coverage_complete,
        }

    report: dict[str, object] = {
        "schema_version": OCR_BENCHMARK_REPORT_VERSION,
        "stage": "screen",
        "selection_eligible": False,
        "locked_test_accessed": False,
        "configurations": [
            candidate(partial, score=1.0, coverage_complete=False),
            candidate(complete, score=0.2, coverage_complete=True),
            candidate(easy, score=0.2, coverage_complete=True),
            candidate(paddle, score=0.2, coverage_complete=True),
        ],
    }
    report["report_sha256"] = _canonical(report, "report_sha256")
    report_path = tmp_path / "screen.json"
    _write_json(report_path, report)

    finalists = select_engine_finalists(report_path)

    assert next(item for item in finalists if item.engine == "tesseract").variant == "original_rgb"


def test_tesseract_four_is_recorded_as_unsupported_and_blocks_selection(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    report_path = private / "results" / "benchmark.json"
    run_ocr_validation_benchmark(
        development_manifest_path=manifest_path,
        configurations=_benchmark_configs(),
        adapters={
            "tesseract": TesseractAdapter(
                runner=lambda *_: _full_tesseract_data(), version="4.1.1"
            ),
            "easyocr": EasyOCRAdapter(reader=_EasyReader()),
            "paddleocr": PaddleOCRAdapter(
                pipeline=_PaddlePipeline(
                    [{"rec_texts": ["Text"], "rec_scores": [0.8], "rec_boxes": [[0, 0, 20, 10]]}]
                )
            ),
        },
        output_path=report_path,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["engine_status"]["tesseract"]["required_version_satisfied"] is False
    assert any(
        failure["reason_code"] == "OCR_ENGINE_VERSION_UNSUPPORTED"
        for failure in report["failures"]
        if failure["engine"] == "tesseract"
    )
    assert report["selection_eligible"] is False


def test_complete_full_report_creates_coverage_bound_experimental_bundle(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    report_path = private / "results" / "benchmark.json"
    run_ocr_validation_benchmark(
        development_manifest_path=manifest_path,
        configurations=_benchmark_configs(),
        adapters={
            "tesseract": TesseractAdapter(
                runner=lambda *_: _full_tesseract_data(), version="5.5.3"
            ),
            "easyocr": EasyOCRAdapter(reader=_EasyReader()),
            "paddleocr": PaddleOCRAdapter(
                pipeline=_PaddlePipeline(
                    [{"rec_texts": ["Text"], "rec_scores": [0.8], "rec_boxes": [[0, 0, 20, 10]]}]
                )
            ),
        },
        output_path=report_path,
        repository_root=repository,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["selection_eligible"] is True
    assert report["comparison_complete"] is True

    bundle_path = private / "results" / "selected.json"
    select_ocr_configuration(
        report_path=report_path,
        output_path=bundle_path,
        repository_root=repository,
    )
    bundle = load_selected_ocr_bundle(bundle_path)
    assert bundle["source_report_schema_version"] == OCR_BENCHMARK_REPORT_VERSION
    assert bundle["comparison_complete"] is True
    assert bundle["coverage_complete"] is True
    assert bundle["record_coverage"] == 1.0
    assert bundle["validation_record_count"] == 1
    assert bundle["status"] == "experimental"
    assert bundle["promotable"] is False
    replay = replay_parser_bundle(
        bundle_path,
        "MTN MobileMoney Amount GHS 10.00 Reference: ABC12345",
        engine_confidence=0.95,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )
    assert (
        replay.as_dict()
        == parse_momo_text(
            "MTN MobileMoney Amount GHS 10.00 Reference: ABC12345",
            engine_confidence=0.95,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        ).as_dict()
    )

    bundle["coverage_complete"] = False
    bundle["bundle_sha256"] = _canonical(bundle, "bundle_sha256")
    _write_json(bundle_path, bundle)
    with pytest.raises(OCRBenchmarkError, match="compatibility"):
        load_selected_ocr_bundle(bundle_path)


def test_benchmark_rejects_partial_matrix_duplicates_naive_clock_and_no_validation(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    common = {
        "development_manifest_path": manifest_path,
        "adapters": {},
        "output_path": private / "result.json",
        "repository_root": repository,
    }
    with pytest.raises(OCRBenchmarkError, match="every required engine"):
        run_ocr_validation_benchmark(
            configurations=[_benchmark_configs()[0]],
            **common,  # type: ignore[arg-type]
        )
    duplicated = [*_benchmark_configs(), _benchmark_configs()[0]]
    with pytest.raises(OCRBenchmarkError, match="duplicated"):
        run_ocr_validation_benchmark(
            configurations=duplicated,
            **common,  # type: ignore[arg-type]
        )
    with pytest.raises(OCRBenchmarkError, match="timezone-aware"):
        run_ocr_validation_benchmark(
            configurations=_benchmark_configs(),
            now=datetime(2026, 8, 14),
            **common,  # type: ignore[arg-type]
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for record in manifest["records"]:
        record["split"] = "train"
    manifest["manifest_sha256"] = _canonical(manifest, "manifest_sha256")
    _write_json(manifest_path, manifest)
    with pytest.raises(OCRBenchmarkError, match="no validation"):
        run_ocr_validation_benchmark(
            configurations=_benchmark_configs(),
            **common,  # type: ignore[arg-type]
        )


def test_selected_bundle_rejects_report_and_bundle_tampering(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private = tmp_path / "private"
    report_path = private / "report.json"
    report: dict[str, object] = {
        "schema_version": OCR_BENCHMARK_REPORT_VERSION,
        "partition": "validation",
        "stage": "full",
        "selection_eligible": True,
        "locked_test_accessed": False,
        "training_executed": False,
        "configurations": [],
    }
    report["report_sha256"] = _canonical(report, "report_sha256")
    _write_json(report_path, report)
    with pytest.raises(OCRBenchmarkError, match="no selectable"):
        select_ocr_configuration(
            report_path=report_path,
            output_path=private / "selected.json",
            repository_root=repository,
        )
    report["partition"] = "test"
    _write_json(report_path, report)
    with pytest.raises(OCRBenchmarkError, match="boundary"):
        select_ocr_configuration(
            report_path=report_path,
            output_path=private / "selected.json",
            repository_root=repository,
        )

    bundle_path = private / "bundle.json"
    bundle: dict[str, object] = {
        "schema_version": OCR_SELECTED_BUNDLE_VERSION,
        "parser_version": "wrong",
        "field_schema_version": "wrong",
        "locked_test_accessed": False,
        "training_executed": False,
    }
    bundle["bundle_sha256"] = _canonical(bundle, "bundle_sha256")
    _write_json(bundle_path, bundle)
    with pytest.raises(OCRBenchmarkError, match="compatibility"):
        load_selected_ocr_bundle(bundle_path)


def test_two_stage_screen_selects_one_finalist_per_engine(tmp_path: Path) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    screen_path = private / "screen.json"
    run_ocr_validation_benchmark(
        development_manifest_path=manifest_path,
        configurations=_benchmark_configs(),
        adapters={
            "tesseract": TesseractAdapter(
                runner=lambda *_: _full_tesseract_data(), version="5.test"
            ),
            "easyocr": EasyOCRAdapter(reader=_EasyReader()),
            "paddleocr": PaddleOCRAdapter(
                pipeline=_PaddlePipeline(
                    [{"rec_texts": ["Text"], "rec_scores": [0.8], "rec_boxes": [[0, 0, 20, 10]]}]
                )
            ),
        },
        output_path=screen_path,
        repository_root=repository,
        source_group_limit=1,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    assert screen["stage"] == "screen"
    assert screen["selection_eligible"] is False
    assert screen["comparison_complete"] is True
    finalists = select_engine_finalists(screen_path)
    assert [config.engine for config in finalists] == [
        "tesseract",
        "easyocr",
        "paddleocr",
    ]
    with pytest.raises(OCRBenchmarkError, match="boundary"):
        select_ocr_configuration(
            report_path=screen_path,
            output_path=private / "selected.json",
            repository_root=repository,
        )
    with pytest.raises(OCRBenchmarkError, match="positive integer"):
        run_ocr_validation_benchmark(
            development_manifest_path=manifest_path,
            configurations=_benchmark_configs(),
            adapters={},
            output_path=private / "bad-screen.json",
            repository_root=repository,
            source_group_limit=0,
        )
