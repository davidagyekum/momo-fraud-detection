from __future__ import annotations

import copy
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
IMPLEMENTATION_COMMIT_SHA = "1" * 40


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


def _valid_parser_ceiling_report(tmp_path: Path) -> dict[str, object]:
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    report.pop("report_sha256")
    return report


def _assert_parser_ceiling_report_rejected(
    report: dict[str, object],
    *,
    private_values: tuple[str, ...] = (),
) -> None:
    with pytest.raises(OCRBenchmarkError) as error:
        ocr_benchmark._validate_parser_ceiling_report(report)
    message = str(error.value)
    assert message.startswith("OCR parser ceiling ")
    assert all(value not in message for value in private_values)


def _assert_private_io_error(
    error: pytest.ExceptionInfo[OCRBenchmarkError],
    *,
    expected_message: str,
    private_values: tuple[str, ...],
) -> None:
    assert str(error.value) == expected_message
    assert error.value.__cause__ is None
    assert all(value not in str(error.value) for value in private_values)


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


@pytest.mark.parametrize(
    ("transcript", "expected"),
    [
        ("Reference: ABC 12345", ("ABC12345",)),
        ("Reference: (ABC12345).", ("ABC12345",)),
        ("Reference: AＢC12345", ("ABC12345",)),  # noqa: RUF001 - NFKC regression
        ("ABC\n12345", ("12345",)),
        ("unrelated ABC 12345 words", ("12345",)),
    ],
)
def test_reference_like_spans_preserve_boundaries(
    transcript: str, expected: tuple[str, ...]
) -> None:
    assert ocr_benchmark._reference_like_spans(transcript) == expected


def test_anchored_reference_spans_stop_before_unstructured_prose() -> None:
    assert ocr_benchmark._anchored_reference_spans("ABC 12345 status text") == ("ABC12345",)
    assert ocr_benchmark._reference_like_spans("Reference: ABC 12345 status text") == ("ABC12345",)


@pytest.mark.parametrize(
    ("comparison", "truth_present", "expected"),
    [
        (
            ocr_benchmark.FieldComparison(
                "reference", "reference", "reference", "ABC12345", "ABC12345", True, True, ()
            ),
            True,
            "exact_selected",
        ),
        (
            ocr_benchmark.FieldComparison(
                "reference", "reference", "reference", "ABC12345", None, False, False, ()
            ),
            True,
            "truth_present_parser_unavailable",
        ),
        (
            ocr_benchmark.FieldComparison(
                "reference", "reference", "reference", "ABC12345", None, False, False, ()
            ),
            False,
            "truth_absent_parser_unavailable",
        ),
        (
            ocr_benchmark.FieldComparison(
                "reference", "reference", "reference", "ABC12345", "XABC12345", False, True, ()
            ),
            True,
            "selected_contains_truth",
        ),
        (
            ocr_benchmark.FieldComparison(
                "reference", "reference", "reference", "ABC12345X", "ABC12345", False, True, ()
            ),
            True,
            "truth_contains_selected",
        ),
        (
            ocr_benchmark.FieldComparison(
                "reference", "reference", "reference", "ABC12345", "XYZ98765", False, True, ()
            ),
            True,
            "truth_present_not_selected",
        ),
        (
            ocr_benchmark.FieldComparison(
                "reference", "reference", "reference", "ABC12345", "XYZ98765", False, True, ()
            ),
            False,
            "truth_absent_transcript",
        ),
    ],
)
def test_text_attribution_containment_priority(
    comparison: ocr_benchmark.FieldComparison,
    truth_present: bool,
    expected: str,
) -> None:
    assert (
        ocr_benchmark._classify_text_attribution(
            comparison,
            truth_present=truth_present,
        )
        == expected
    )


def test_text_attribution_rejects_available_comparison_without_observed_value() -> None:
    comparison = ocr_benchmark.FieldComparison(
        "reference",
        "reference",
        "reference",
        "ABC12345",
        None,
        False,
        True,
        (),
    )

    with pytest.raises(OCRBenchmarkError, match="availability state is invalid"):
        ocr_benchmark._classify_text_attribution(comparison, truth_present=True)


@pytest.mark.parametrize(
    ("truth_subtype", "observed_field"),
    [
        ("recipient_name_truth", "recipient_wallet"),
        ("recipient_wallet_truth", "recipient"),
        ("unsupported_truth_subtype", "recipient"),
    ],
)
def test_recipient_truth_presence_rejects_mismatched_comparison_contract(
    truth_subtype: str,
    observed_field: str,
) -> None:
    comparison = ocr_benchmark.FieldComparison(
        "recipient",
        "recipient",
        observed_field,
        "DEMO PERSON",
        None,
        False,
        False,
        (),
        truth_subtype=truth_subtype,
    )

    with pytest.raises(OCRBenchmarkError, match=r"recipient .* is invalid"):
        ocr_benchmark._recipient_truth_present(comparison, "Recipient: Demo Person")


def test_recipient_name_truth_presence_removes_only_surrounding_punctuation() -> None:
    comparison = ocr_benchmark.FieldComparison(
        "recipient",
        "recipient_name",
        "recipient",
        "«ANNE-MARIE O'NEIL»",
        "OTHER PERSON",
        False,
        True,
        (),
        truth_subtype="recipient_name_truth",
    )

    assert ocr_benchmark._recipient_truth_present(
        comparison,
        "Recipient: (Anne-Marie O'Neil),",
    )


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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "ghana-ocr-parser-ceiling-report-v4"
    assert report["diagnostic_contract_version"] == "ghana-ocr-mismatch-attribution-v1"
    assert report["implementation_commit_sha"] == IMPLEMENTATION_COMMIT_SHA
    assert report["development_manifest_sha256"] == manifest["manifest_sha256"]
    assert report["source_split_manifest_sha256"] == manifest["source_split_manifest_sha256"]
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


@pytest.mark.parametrize(
    ("path", "key", "private_value"),
    [
        ((), "debug_transcript", "PRIVATE TRANSCRIPT FRAGMENT"),
        (
            ("mismatch_attribution_counts", "amount"),
            "PRIVATE_AMOUNT_10_00",
            "PRIVATE_AMOUNT_10_00",
        ),
        (("amount_candidate_count_buckets", "active"), "4", "4"),
        (("parser_warning_counts",), "PRIVATE_WARNING_CODE", "PRIVATE_WARNING_CODE"),
    ],
)
def test_parser_ceiling_report_allowlist_rejects_unexpected_keys_without_echoing_values(
    tmp_path: Path,
    path: tuple[str, ...],
    key: str,
    private_value: str,
) -> None:
    report = copy.deepcopy(_valid_parser_ceiling_report(tmp_path))
    target: dict[str, object] = report
    for part in path:
        target = target[part]  # type: ignore[assignment]
    target[key] = 1 if path else private_value

    _assert_parser_ceiling_report_rejected(report, private_values=(private_value,))


@pytest.mark.parametrize(
    "mutation",
    [
        "outcome_partition",
        "presence_exceeds_denominator",
        "both_exceeds_labelled",
    ],
)
def test_parser_ceiling_report_denominator_relationships_fail_closed(
    tmp_path: Path,
    mutation: str,
) -> None:
    report = _valid_parser_ceiling_report(tmp_path)
    if mutation == "outcome_partition":
        report["field_outcome_counts"]["amount"]["exact"] += 1  # type: ignore[index,operator]
    elif mutation == "presence_exceeds_denominator":
        denominator = report["field_scored_record_count"]["amount"]  # type: ignore[index]
        report["amount_candidate_pool_presence"]["labelled_nonempty"] = (  # type: ignore[index]
            denominator + 1  # type: ignore[operator]
        )
    else:
        report["amount_candidate_pool_presence"]["labelled_nonempty"] = 0  # type: ignore[index]
        report["amount_candidate_pool_presence"]["both_nonempty"] = 1  # type: ignore[index]

    _assert_parser_ceiling_report_rejected(report)


@pytest.mark.parametrize(
    ("path", "invalid_count"),
    [
        (("record_count",), True),
        (("recipient_secondary_truth_present_count",), -1),
    ],
)
def test_parser_ceiling_report_count_type_requires_nonnegative_integer_not_bool(
    tmp_path: Path,
    path: tuple[str, ...],
    invalid_count: object,
) -> None:
    report = _valid_parser_ceiling_report(tmp_path)
    report[path[0]] = invalid_count

    _assert_parser_ceiling_report_rejected(report)


@pytest.mark.parametrize(
    "identity",
    [
        "schema_version",
        "diagnostic_contract_version",
        "benchmark_version",
        "parser_version",
        "field_schema_version",
        "implementation_commit_sha",
        "development_manifest_sha256",
        "source_split_manifest_sha256",
        "partition",
    ],
)
def test_parser_ceiling_report_metadata_requires_every_identity(
    tmp_path: Path,
    identity: str,
) -> None:
    report = _valid_parser_ceiling_report(tmp_path)
    report.pop(identity)

    _assert_parser_ceiling_report_rejected(report)


@pytest.mark.parametrize(
    ("identity", "invalid_value"),
    [
        ("schema_version", "ghana-ocr-parser-ceiling-report-v3"),
        ("diagnostic_contract_version", "unsupported-attribution-contract"),
        ("benchmark_version", "unsupported-benchmark"),
        ("parser_version", "unsupported-parser"),
        ("field_schema_version", "unsupported-field-schema"),
        ("partition", "train"),
    ],
)
def test_parser_ceiling_report_rejects_wrong_identity_values(
    tmp_path: Path,
    identity: str,
    invalid_value: str,
) -> None:
    report = _valid_parser_ceiling_report(tmp_path)
    report[identity] = invalid_value

    _assert_parser_ceiling_report_rejected(report)


@pytest.mark.parametrize(
    "flag",
    [
        "raw_text_persisted",
        "field_values_persisted",
        "record_identifiers_persisted",
        "locked_test_accessed",
        "training_executed",
    ],
)
def test_parser_ceiling_report_privacy_flags_must_remain_false(
    tmp_path: Path,
    flag: str,
) -> None:
    report = _valid_parser_ceiling_report(tmp_path)
    report[flag] = True

    _assert_parser_ceiling_report_rejected(report)


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "record_id",
        "source_group_id",
        "truth_value",
        "candidate_values",
        "private_path",
        "full_transcript",
    ],
)
def test_parser_ceiling_report_privacy_allowlist_rejects_forbidden_fields_without_echo(
    tmp_path: Path,
    forbidden_key: str,
) -> None:
    report = _valid_parser_ceiling_report(tmp_path)
    private_value = "PRIVATE VALUE FROM VALIDATION RECORD"
    report[forbidden_key] = private_value

    _assert_parser_ceiling_report_rejected(
        report,
        private_values=(forbidden_key, private_value),
    )


def test_parser_ceiling_report_validation_precedes_self_hash_and_atomic_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
    calls: list[str] = []
    real_validate = ocr_benchmark._validate_parser_ceiling_report
    real_hash = ocr_benchmark._canonical_hash
    real_write = ocr_benchmark._write_json

    def validate(report: dict[str, object]) -> None:
        calls.append("validate")
        real_validate(report)

    def canonical_hash(report: dict[str, object], hash_field: str) -> str:
        calls.append("hash")
        return real_hash(report, hash_field)

    def write_json(path: Path, report: object) -> None:
        calls.append("write")
        real_write(path, report)

    monkeypatch.setattr(ocr_benchmark, "_validate_parser_ceiling_report", validate)
    monkeypatch.setattr(ocr_benchmark, "_canonical_hash", canonical_hash)
    monkeypatch.setattr(ocr_benchmark, "_write_json", write_json)

    ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
        development_manifest_path=manifest_path,
        output_path=output,
        repository_root=repository,
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    assert calls[-3:] == ["validate", "hash", "write"]


def test_parser_ceiling_report_self_hash_is_deterministic_with_fixed_aware_clock(
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
    outputs = (
        private / "results" / "parser-ceiling-first.json",
        private / "results" / "parser-ceiling-second.json",
    )
    reports: list[dict[str, object]] = []
    for output in outputs:
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )
        reports.append(json.loads(output.read_text(encoding="utf-8")))

    assert reports[0] == reports[1]
    assert reports[0]["report_sha256"] == _canonical(reports[0], "report_sha256")
    assert reports[1]["report_sha256"] == _canonical(reports[1], "report_sha256")


def test_parser_ceiling_diagnostic_does_not_touch_adapters_models_training_or_locked_test(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("forbidden adapter or model boundary touched")

    for adapter_name in ("TesseractAdapter", "EasyOCRAdapter", "PaddleOCRAdapter"):
        monkeypatch.setattr(ocr_benchmark, adapter_name, forbidden)
    monkeypatch.setattr(ocr_benchmark.importlib, "import_module", forbidden)

    ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
        development_manifest_path=manifest_path,
        output_path=output,
        repository_root=repository,
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["partition"] == "validation"
    assert report["locked_test_accessed"] is False
    assert report["training_executed"] is False


def test_parser_ceiling_diagnostic_attributes_truth_in_suppressed_amount_pool(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = "Amount GHS 20.00\nTransfer value GHS 10.00"
    truth["fields"] = [{"name": "amount", "normalized": "10.00"}]
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["mismatch_attribution_counts"]["amount"] == {
        "exact_selected": 0,
        "no_valid_currency_candidate": 0,
        "truth_in_active_pool_not_exact": 0,
        "truth_in_suppressed_currency_pool": 1,
        "truth_absent_all_candidate_pools": 0,
    }
    assert report["amount_candidate_count_buckets"] == {
        "labelled": {"0": 0, "1": 1, "2": 0, "3_plus": 0},
        "currency": {"0": 0, "1": 0, "2": 1, "3_plus": 0},
        "active": {"0": 0, "1": 1, "2": 0, "3_plus": 0},
    }
    assert report["amount_candidate_pool_presence"] == {
        "labelled_nonempty": 1,
        "currency_nonempty": 1,
        "both_nonempty": 1,
        "labelled_active": 1,
        "currency_fallback_active": 0,
    }
    assert "20.00" not in json.dumps(report)
    assert "10.00" not in json.dumps(report)


def test_parser_ceiling_accepts_raw_labelled_active_with_no_valid_labelled_amount(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = "Amount GHS 1000000000.00\nGHS 20.00"
    truth["fields"] = [{"name": "amount", "normalized": "20.00"}]
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["amount_candidate_pool_presence"] == {
        "labelled_nonempty": 0,
        "currency_nonempty": 1,
        "both_nonempty": 0,
        "labelled_active": 1,
        "currency_fallback_active": 0,
    }
    assert report["amount_candidate_count_buckets"] == {
        "labelled": {"0": 1, "1": 0, "2": 0, "3_plus": 0},
        "currency": {"0": 0, "1": 1, "2": 0, "3_plus": 0},
        "active": {"0": 1, "1": 0, "2": 0, "3_plus": 0},
    }
    assert report["mismatch_attribution_counts"]["amount"] == {
        "exact_selected": 0,
        "no_valid_currency_candidate": 0,
        "truth_in_active_pool_not_exact": 0,
        "truth_in_suppressed_currency_pool": 1,
        "truth_absent_all_candidate_pools": 0,
    }
    assert report["report_sha256"] == _canonical(report, "report_sha256")
    assert output.is_file()


@pytest.mark.parametrize(
    ("transcript", "truth_amount", "attribution", "expected_bucket_counts"),
    [
        (
            "No currency candidate",
            "10.00",
            "no_valid_currency_candidate",
            {
                "labelled": {"0": 1, "1": 0, "2": 0, "3_plus": 0},
                "currency": {"0": 1, "1": 0, "2": 0, "3_plus": 0},
                "active": {"0": 1, "1": 0, "2": 0, "3_plus": 0},
            },
        ),
        (
            "GHS 10.00 and GHS 20.00",
            "10.00",
            "truth_in_active_pool_not_exact",
            {
                "labelled": {"0": 1, "1": 0, "2": 0, "3_plus": 0},
                "currency": {"0": 0, "1": 0, "2": 1, "3_plus": 0},
                "active": {"0": 0, "1": 0, "2": 1, "3_plus": 0},
            },
        ),
        (
            "GHS 10.00 GHS 20.00 GHS 30.00",
            "99.00",
            "truth_absent_all_candidate_pools",
            {
                "labelled": {"0": 1, "1": 0, "2": 0, "3_plus": 0},
                "currency": {"0": 0, "1": 0, "2": 0, "3_plus": 1},
                "active": {"0": 0, "1": 0, "2": 0, "3_plus": 1},
            },
        ),
    ],
)
def test_parser_ceiling_diagnostic_attributes_amount_candidate_boundaries(
    tmp_path: Path,
    transcript: str,
    truth_amount: str,
    attribution: str,
    expected_bucket_counts: dict[str, dict[str, int]],
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = transcript
    truth["fields"] = [{"name": "amount", "normalized": truth_amount}]
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    amount_attributions = report["mismatch_attribution_counts"]["amount"]
    assert amount_attributions[attribution] == 1
    assert sum(amount_attributions.values()) == 1
    assert report["amount_candidate_count_buckets"] == expected_bucket_counts
    assert transcript not in json.dumps(report)
    assert truth_amount not in json.dumps(report)


def test_parser_ceiling_reference_fragments_do_not_create_truth_presence(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = "ABC\n12345"
    truth["fields"] = [{"name": "reference", "normalized": "ABC12345"}]
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["mismatch_attribution_counts"]["reference"] == {
        "exact_selected": 0,
        "truth_present_parser_unavailable": 0,
        "truth_absent_parser_unavailable": 1,
        "selected_contains_truth": 0,
        "truth_contains_selected": 0,
        "truth_present_not_selected": 0,
        "truth_absent_transcript": 0,
    }


def test_parser_ceiling_anchored_reference_prose_does_not_manufacture_truth(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = "Reference: ABC 12345 status text"
    truth["fields"] = [{"name": "reference", "normalized": "ABC12345STATUS"}]
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["mismatch_attribution_counts"]["reference"] == {
        "exact_selected": 0,
        "truth_present_parser_unavailable": 0,
        "truth_absent_parser_unavailable": 1,
        "selected_contains_truth": 0,
        "truth_contains_selected": 0,
        "truth_present_not_selected": 0,
        "truth_absent_transcript": 0,
    }


def test_parser_ceiling_malformed_manifest_error_is_generic_and_creates_no_output(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private = tmp_path / "owner-secret-private-root"
    manifest_path = private / "manifest-GHPRIVATE_RECORD_0042.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{", encoding="utf-8")
    output = private / "results" / "report-GHPRIVATE_RECORD_0042.json"

    with pytest.raises(OCRBenchmarkError) as error:
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    _assert_private_io_error(
        error,
        expected_message="unable to read JSON object",
        private_values=(str(private), manifest_path.name, "GHPRIVATE_RECORD_0042"),
    )
    assert not output.exists()


def test_parser_ceiling_unreadable_manifest_error_is_generic_and_creates_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    private = tmp_path / "owner-secret-private-root"
    manifest_path = private / "manifest-GHPRIVATE_RECORD_0043.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text("{}", encoding="utf-8")
    output = private / "results" / "report-GHPRIVATE_RECORD_0043.json"
    real_read_text = Path.read_text

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.resolve() == manifest_path.resolve():
            raise PermissionError(13, "private path denied", str(path))
        return real_read_text(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    with pytest.raises(OCRBenchmarkError) as error:
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    _assert_private_io_error(
        error,
        expected_message="unable to read JSON object",
        private_values=(str(private), manifest_path.name, "GHPRIVATE_RECORD_0043"),
    )
    assert not output.exists()


def test_parser_ceiling_malformed_truth_error_is_generic_and_creates_no_output(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "owner-secret-bundle",
        repository_root=repository,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation_record = next(
        record for record in manifest["records"] if record["record_id"] == VALIDATION_ID
    )
    bundled_truth = manifest_path.parent / validation_record["truth_path"]
    bundled_truth.write_text("{", encoding="utf-8")
    validation_record["truth_sha256"] = hashlib.sha256(bundled_truth.read_bytes()).hexdigest()
    manifest["manifest_sha256"] = _canonical(manifest, "manifest_sha256")
    _write_json(manifest_path, manifest)
    output = private / "results" / "report-GHPRIVATE_RECORD_0044.json"

    with pytest.raises(OCRBenchmarkError) as error:
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    _assert_private_io_error(
        error,
        expected_message="unable to read JSON object",
        private_values=(str(private), bundled_truth.name, VALIDATION_ID),
    )
    assert not output.exists()


def test_parser_ceiling_unreadable_truth_error_is_generic_and_creates_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "owner-secret-bundle",
        repository_root=repository,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation_record = next(
        record for record in manifest["records"] if record["record_id"] == VALIDATION_ID
    )
    bundled_truth = (manifest_path.parent / validation_record["truth_path"]).resolve()
    output = private / "results" / "report-GHPRIVATE_RECORD_0047.json"
    real_read_text = Path.read_text

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path.resolve() == bundled_truth:
            raise PermissionError(13, "private path denied", str(path))
        return real_read_text(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    with pytest.raises(OCRBenchmarkError) as error:
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    _assert_private_io_error(
        error,
        expected_message="unable to read JSON object",
        private_values=(str(private), bundled_truth.name, VALIDATION_ID),
    )
    assert not output.exists()


def test_parser_ceiling_hash_read_error_is_generic_and_creates_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "owner-secret-bundle",
        repository_root=repository,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation_record = next(
        record for record in manifest["records"] if record["record_id"] == VALIDATION_ID
    )
    bundled_truth = (manifest_path.parent / validation_record["truth_path"]).resolve()
    output = private / "results" / "report-GHPRIVATE_RECORD_0045.json"
    real_open = Path.open

    def guarded_open(path: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if path.resolve() == bundled_truth:
            raise PermissionError(13, "private path denied", str(path))
        return real_open(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(OCRBenchmarkError) as error:
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    _assert_private_io_error(
        error,
        expected_message="unable to hash file",
        private_values=(str(private), bundled_truth.name, VALIDATION_ID),
    )
    assert not output.exists()


def test_parser_ceiling_failed_atomic_write_is_generic_and_leaves_no_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "owner-secret-bundle",
        repository_root=repository,
    )
    output = private / "results" / "report-GHPRIVATE_RECORD_0046.json"

    def denied_replace(source: object, destination: object) -> None:
        raise PermissionError(13, "private output denied", str(destination))

    monkeypatch.setattr(ocr_benchmark.os, "replace", denied_replace)
    with pytest.raises(OCRBenchmarkError) as error:
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    _assert_private_io_error(
        error,
        expected_message="unable to write JSON output",
        private_values=(str(private), output.name, "GHPRIVATE_RECORD_0046"),
    )
    assert not output.exists()
    assert not tuple(output.parent.glob(".*.tmp"))


def test_parser_ceiling_timestamp_attribution_is_deferred(
    tmp_path: Path,
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = "Date 14/08/2026 10:30"
    truth["fields"] = [
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["mismatch_attribution_counts"]["timestamp"] == {
        "deferred_insufficient_support": report["field_scored_record_count"]["timestamp"]
    }


@pytest.mark.parametrize("implementation_commit_sha", ["f" * 39, "F" * 40, "not-a-commit-sha"])
def test_parser_ceiling_diagnostic_rejects_malformed_implementation_identity(
    tmp_path: Path, implementation_commit_sha: str
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

    with pytest.raises(OCRBenchmarkError):
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=implementation_commit_sha,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    assert not output.exists()


@pytest.mark.parametrize("source_split_manifest_sha256", [None, "not-a-sha256"])
def test_parser_ceiling_diagnostic_rejects_invalid_source_split_identity(
    tmp_path: Path, source_split_manifest_sha256: str | None
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    manifest_path = prepare_ocr_development_bundle(
        split_manifest_path=split,
        image_bindings=bindings,
        truth_root=truth_root,
        output_root=private / "bundle",
        repository_root=repository,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_split_manifest_sha256 is None:
        manifest.pop("source_split_manifest_sha256")
        manifest["manifest_sha256"] = _canonical(manifest, "manifest_sha256")
    else:
        manifest["source_split_manifest_sha256"] = source_split_manifest_sha256
    _write_json(manifest_path, manifest)
    output = private / "results" / "parser-ceiling.json"

    with pytest.raises(OCRBenchmarkError):
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14, tzinfo=UTC),
        )

    assert not output.exists()


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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert report["schema_version"] == "ghana-ocr-parser-ceiling-report-v4"
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
    truth["full_transcript"] = "Fictional wallet +233240000012 transaction"
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(report)
    assert report["schema_version"] == "ghana-ocr-parser-ceiling-report-v4"
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
    assert report["mismatch_attribution_counts"]["recipient"] == {
        "exact_selected": 0,
        "truth_present_parser_unavailable": 0,
        "truth_absent_parser_unavailable": 0,
        "selected_contains_truth": 0,
        "truth_contains_selected": 0,
        "truth_present_not_selected": 1,
        "truth_absent_transcript": 0,
    }
    assert report["raw_text_persisted"] is False
    assert report["field_values_persisted"] is False
    assert report["record_identifiers_persisted"] is False
    assert report["locked_test_accessed"] is False
    assert report["training_executed"] is False
    assert "+233240000012" not in serialized
    assert "+233240000013" not in serialized
    assert VALIDATION_ID not in serialized


def test_parser_ceiling_recipient_name_attribution_ignores_secondary_wallet_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, private, split, bindings, truth_root = _private_fixture(tmp_path)
    truth_path = truth_root / f"{VALIDATION_ID}.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    truth["full_transcript"] = "Sent to Demo Person wallet +233240000012"
    truth["fields"] = [
        {"name": "recipient_name", "normalized": "DEMO PERSON"},
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
        raw="Other Person",
        normalized="OTHER PERSON",
        confidence=0.8,
        available=True,
        warnings=(),
    )
    fields["recipient_wallet"] = replace(
        fields["recipient_wallet"],
        raw="+233240000012",
        normalized="+233240000012",
        confidence=0.8,
        available=True,
        warnings=(),
    )
    monkeypatch.setattr(
        ocr_benchmark,
        "parse_momo_text",
        lambda *args, **kwargs: replace(parser, fields=fields),
    )

    ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
        development_manifest_path=manifest_path,
        output_path=output,
        repository_root=repository,
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
        now=datetime(2026, 8, 14, tzinfo=UTC),
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["recipient_truth_subtype_counts"] == {
        "recipient_name_truth": 1,
        "recipient_wallet_truth": 0,
    }
    assert report["recipient_secondary_truth_present_count"] == 1
    assert report["mismatch_attribution_counts"]["recipient"] == {
        "exact_selected": 0,
        "truth_present_parser_unavailable": 0,
        "truth_absent_parser_unavailable": 0,
        "selected_contains_truth": 0,
        "truth_contains_selected": 0,
        "truth_present_not_selected": 1,
        "truth_absent_transcript": 0,
    }


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
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
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
        implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
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
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
            now=datetime(2026, 8, 14),
        )

    monkeypatch.setattr(ocr_benchmark, "load_ocr_development_bundle", lambda *_args, **_kw: ())
    with pytest.raises(OCRBenchmarkError, match="has no validation records"):
        ocr_benchmark.run_ocr_parser_ceiling_diagnostic(
            development_manifest_path=manifest_path,
            output_path=output,
            repository_root=repository,
            implementation_commit_sha=IMPLEMENTATION_COMMIT_SHA,
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
