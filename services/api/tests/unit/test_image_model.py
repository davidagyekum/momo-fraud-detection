from __future__ import annotations

import hashlib
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from flask import Flask

from momo_fdvs.models import ModelVersion
from momo_fdvs.services import image_model
from momo_fdvs.services.image_model import (
    IMAGE_PREPROCESSING_SCHEMA_HASH,
    IMAGE_PREPROCESSING_VERSION,
    ImageModelFailure,
    load_verified_image_model,
    predict_image_tampering,
    preprocess_image_bytes,
    resolve_private_image_artifact,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY_ROOT / "ml" / "src"))

from momo_fdvs_ml.image_schema import (  # noqa: E402
    IMAGE_PREPROCESSING_SCHEMA_HASH as ML_SCHEMA_HASH,
)
from momo_fdvs_ml.image_schema import preprocess_image_bytes as ml_preprocess  # noqa: E402


class _LoadedModel:
    input_shape = (None, 224, 224, 3)
    output_shape = (None, 1)

    def __init__(self, output: object = 0.8, *, raises: bool = False) -> None:
        self.output = output
        self.raises = raises

    def predict(self, tensor: np.ndarray, *, verbose: int) -> np.ndarray:
        assert tensor.shape == (1, 224, 224, 3)
        assert verbose == 0
        if self.raises:
            raise RuntimeError("inference failed")
        return np.asarray([[self.output]])


def _model_and_artifact(
    app: Flask,
    tmp_path: Path,
    *,
    status: str = "ACTIVE",
    metrics: dict[str, object] | None = None,
) -> tuple[ModelVersion, Path]:
    root = tmp_path / "image-models"
    root.mkdir(exist_ok=True)
    app.config["IMAGE_MODEL_ROOT"] = root
    app.config["IMAGE_MODEL_MAX_BYTES"] = 10_000_000
    artifact = root / "controlled.keras"
    artifact.write_bytes(b"controlled-keras-test")
    model = ModelVersion(
        id=uuid.uuid4(),
        model_type="IMAGE",
        name="controlled-image",
        version="v1",
        status=status,
        artifact_uri=f"private://image/{artifact.name}",
        artifact_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        input_schema_hash=IMAGE_PREPROCESSING_SCHEMA_HASH,
        preprocessing_version=IMAGE_PREPROCESSING_VERSION,
        framework_versions={"tensorflow": "test"},
        metrics={"threshold": 0.5} if metrics is None else metrics,
    )
    return model, artifact


def _set_loader(monkeypatch: pytest.MonkeyPatch, loaded: object) -> None:
    loader = SimpleNamespace(load_model=lambda *args, **kwargs: loaded)
    fake_tf = SimpleNamespace(keras=SimpleNamespace(models=loader))
    monkeypatch.setattr(image_model, "_tensorflow", lambda: fake_tf)


def _receipt_bytes() -> bytes:
    return (
        REPOSITORY_ROOT / "ml" / "data" / "controlled" / "images" / "controlled-original-0001.png"
    ).read_bytes()


def test_api_and_training_preprocessing_are_byte_identical() -> None:
    payload = _receipt_bytes()
    assert IMAGE_PREPROCESSING_SCHEMA_HASH == ML_SCHEMA_HASH
    assert np.array_equal(preprocess_image_bytes(payload), ml_preprocess(payload))


def test_verified_active_image_model_returns_bounded_probability(
    app: Flask, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path)
        loaded = _LoadedModel(0.8)
        _set_loader(monkeypatch, loaded)
        assert load_verified_image_model(model) is loaded
        result = predict_image_tampering(model, _receipt_bytes())
    assert result["status"] == "SUCCESS"
    assert result["tamper_probability"] == 0.8
    assert result["predicted_class"] == "CONTROLLED_TAMPERED"
    assert result["preprocessing_schema_hash"] == IMAGE_PREPROCESSING_SCHEMA_HASH


def test_hash_mismatch_is_rejected_before_tensorflow_load(
    app: Flask, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.app_context():
        model, artifact = _model_and_artifact(app, tmp_path)
        artifact.write_bytes(b"tampered")
        called = False

        def fail_if_called() -> object:
            nonlocal called
            called = True
            raise AssertionError("TensorFlow must not load before hash verification")

        monkeypatch.setattr(image_model, "_tensorflow", fail_if_called)
        with pytest.raises(ImageModelFailure) as failure:
            load_verified_image_model(model)
    assert failure.value.code == "IMAGE_MODEL_HASH_MISMATCH"
    assert called is False


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda model: setattr(model, "model_type", "STRUCTURED"), "IMAGE_MODEL_TYPE_INVALID"),
        (lambda model: setattr(model, "artifact_sha256", "invalid"), "IMAGE_MODEL_HASH_INVALID"),
        (
            lambda model: setattr(model, "input_schema_hash", "0" * 64),
            "IMAGE_MODEL_SCHEMA_MISMATCH",
        ),
    ],
)
def test_registry_metadata_must_match_image_runtime(
    app: Flask,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation,
    code: str,
) -> None:  # type: ignore[no-untyped-def]
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path)
        mutation(model)
        _set_loader(monkeypatch, _LoadedModel())
        with pytest.raises(ImageModelFailure) as failure:
            load_verified_image_model(model)
    assert failure.value.code == code


def test_uri_missing_large_and_escape_fail_safely(app: Flask, tmp_path: Path) -> None:
    with app.app_context():
        model, artifact = _model_and_artifact(app, tmp_path)
        with pytest.raises(ImageModelFailure) as invalid:
            resolve_private_image_artifact("private://structured/model.keras")
        assert invalid.value.code == "IMAGE_MODEL_URI_INVALID"
        with pytest.raises(ImageModelFailure) as escape:
            resolve_private_image_artifact("private://image/../../model.keras")
        assert escape.value.code == "IMAGE_MODEL_URI_INVALID"
        artifact.unlink()
        with pytest.raises(ImageModelFailure) as missing:
            resolve_private_image_artifact(model.artifact_uri)
        assert missing.value.code == "IMAGE_MODEL_ARTIFACT_MISSING"
        artifact.write_bytes(b"large")
        app.config["IMAGE_MODEL_MAX_BYTES"] = 1
        with pytest.raises(ImageModelFailure) as large:
            resolve_private_image_artifact(model.artifact_uri)
        assert large.value.code == "IMAGE_MODEL_ARTIFACT_TOO_LARGE"


@pytest.mark.parametrize("payload", [b"", b"not-an-image"])
def test_corrupt_or_empty_input_is_explicit(payload: bytes) -> None:
    with pytest.raises(ImageModelFailure) as failure:
        preprocess_image_bytes(payload)
    assert failure.value.code == "IMAGE_MODEL_INPUT_INVALID"


def test_runtime_load_shape_and_deserialisation_failures_are_explicit(
    app: Flask, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path)

        def broken(*args: object, **kwargs: object) -> object:
            raise ValueError("broken")

        _set_loader(monkeypatch, SimpleNamespace())
        monkeypatch.setattr(
            image_model,
            "_tensorflow",
            lambda: SimpleNamespace(
                keras=SimpleNamespace(models=SimpleNamespace(load_model=broken))
            ),
        )
        with pytest.raises(ImageModelFailure) as deserialise:
            load_verified_image_model(model)
        assert deserialise.value.code == "IMAGE_MODEL_DESERIALISATION_FAILED"

        wrong = SimpleNamespace(input_shape=(None, 1, 1, 3), output_shape=(None, 2))
        _set_loader(monkeypatch, wrong)
        with pytest.raises(ImageModelFailure) as shape:
            load_verified_image_model(model)
        assert shape.value.code == "IMAGE_MODEL_SHAPE_INVALID"


@pytest.mark.parametrize("metrics", [{}, {"threshold": True}, {"threshold": 1.0}])
def test_threshold_and_inactive_model_fail_safely(
    app: Flask,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metrics: dict[str, object],
) -> None:
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path, metrics=metrics)
        _set_loader(monkeypatch, _LoadedModel())
        with pytest.raises(ImageModelFailure) as threshold:
            predict_image_tampering(model, _receipt_bytes())
        assert threshold.value.code == "IMAGE_MODEL_THRESHOLD_INVALID"

        model.status = "READY"
        with pytest.raises(ImageModelFailure) as inactive:
            predict_image_tampering(model, _receipt_bytes())
        assert inactive.value.code == "IMAGE_MODEL_NOT_ACTIVE"


@pytest.mark.parametrize(
    ("loaded", "code"),
    [
        (_LoadedModel(raises=True), "IMAGE_MODEL_INFERENCE_FAILED"),
        (_LoadedModel(float("nan")), "IMAGE_MODEL_OUTPUT_INVALID"),
        (_LoadedModel(1.5), "IMAGE_MODEL_OUTPUT_INVALID"),
    ],
)
def test_inference_runtime_and_output_failures_are_explicit(
    app: Flask,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    loaded: _LoadedModel,
    code: str,
) -> None:
    with app.app_context():
        model, _ = _model_and_artifact(app, tmp_path)
        _set_loader(monkeypatch, loaded)
        with pytest.raises(ImageModelFailure) as failure:
            predict_image_tampering(model, _receipt_bytes())
    assert failure.value.code == code


def test_missing_tensorflow_runtime_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_name: str) -> object:
        raise ImportError

    monkeypatch.setattr(image_model.importlib, "import_module", missing)
    with pytest.raises(ImageModelFailure) as failure:
        image_model._tensorflow()
    assert failure.value.code == "IMAGE_MODEL_RUNTIME_UNAVAILABLE"
