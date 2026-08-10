from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from momo_fdvs_ml import image_model
from momo_fdvs_ml.image_model import (
    ImageModelError,
    ImageThreshold,
    benchmark_cpu_inference,
    class_weights,
    evaluate_binary_partition,
    load_and_verify_image_artifact,
    select_image_threshold,
    train_and_package_image_model,
    training_policy,
)
from momo_fdvs_ml.image_schema import (
    IMAGE_PREPROCESSING_SCHEMA_HASH,
    ImageSample,
)


def _samples() -> tuple[ImageSample, ImageSample]:
    return (
        ImageSample(
            "original", "group-a", "test", "ORIGINAL", 0, Path("a.png"), "0" * 64, "synthetic"
        ),
        ImageSample(
            "tampered",
            "group-a",
            "test",
            "CONTROLLED_TAMPERED",
            1,
            Path("b.png"),
            "1" * 64,
            "controlled_tamper",
        ),
    )


def test_training_policy_preserves_required_stages() -> None:
    policy = training_policy()
    assert policy["architecture"] == "MobileNetV3Small"
    assert policy["head_stage"]["backbone_frozen"] is True  # type: ignore[index]
    assert policy["fine_tune_stage"]["unfreeze_last_backbone_layers"] == 20  # type: ignore[index]
    assert policy["threshold_partition"] == "validation"


def test_class_weights_use_training_distribution_only() -> None:
    assert class_weights([0, 0, 0, 1]) == {0: pytest.approx(2 / 3), 1: 2.0}
    with pytest.raises(ImageModelError):
        class_weights([0, 0])


def test_threshold_selection_uses_macro_f1_and_fraud_recall() -> None:
    selected = select_image_threshold([0, 1], [0.1, 0.9])
    assert selected.value == 0.15
    assert selected.validation_macro_f1 == 1.0
    assert selected.validation_tampered_recall == 1.0


@pytest.mark.parametrize(
    ("labels", "scores"),
    [([], []), ([0, 0], [0.1, 0.2]), ([0, 1], [0.1, 1.1]), ([0, 1], [0.1])],
)
def test_threshold_selection_rejects_invalid_inputs(labels: list[int], scores: list[float]) -> None:
    with pytest.raises(ImageModelError):
        select_image_threshold(labels, scores)


def test_binary_evaluation_reports_all_required_metrics() -> None:
    result = evaluate_binary_partition(
        [0, 1],
        [0.1, 0.9],
        threshold=ImageThreshold(0.5, 1.0, 1.0),
        samples=_samples(),
    )
    assert result["confusion_matrix"] == [[1, 0], [0, 1]]
    assert result["macro_f1"] == 1.0
    assert result["pr_auc"] == 1.0
    assert result["roc_auc"] == 1.0
    assert result["source_group_count"] == 1
    assert result["calibration"]["calibration_applied"] is False  # type: ignore[index]


@pytest.mark.parametrize("scores", [[0.5], [float("nan"), 0.5], [-0.1, 0.5]])
def test_binary_evaluation_rejects_invalid_shapes_or_scores(scores: list[float]) -> None:
    with pytest.raises(ImageModelError):
        evaluate_binary_partition(
            [0, 1],
            scores,
            threshold=ImageThreshold(0.5, 0.0, 0.0),
            samples=_samples(),
        )


class _PredictModel:
    def __init__(self, output: np.ndarray | None = None) -> None:
        self.output = output
        self.calls = 0

    def predict(self, features: np.ndarray, *, verbose: int) -> np.ndarray:
        assert verbose == 0
        self.calls += 1
        if self.output is not None:
            return self.output
        return np.full((len(features), 1), 0.5, dtype=float)


def test_probability_shape_and_latency_guards() -> None:
    features = np.zeros((2, 224, 224, 3), dtype=np.float32)
    assert image_model._predict_probabilities(_PredictModel(), features) == [0.5, 0.5]
    with pytest.raises(ImageModelError):
        image_model._predict_probabilities(_PredictModel(np.zeros((2, 2))), features)
    with pytest.raises(ImageModelError):
        image_model._predict_probabilities(_PredictModel(np.asarray([[0.2], [1.2]])), features)
    model = _PredictModel()
    benchmark = benchmark_cpu_inference(model, features[0], iterations=3)
    assert benchmark["iterations"] == 3
    assert model.calls == 4
    with pytest.raises(ImageModelError):
        benchmark_cpu_inference(model, features[0], iterations=2)


def test_verified_artifact_hash_and_shapes_precede_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "model.keras"
    artifact.write_bytes(b"trusted-test-artifact")
    loaded = SimpleNamespace(input_shape=(None, 224, 224, 3), output_shape=(None, 1))
    loader = SimpleNamespace(load_model=lambda *args, **kwargs: loaded)
    fake_tf = SimpleNamespace(keras=SimpleNamespace(models=loader))
    monkeypatch.setattr(image_model, "_tensorflow", lambda: fake_tf)
    verified = load_and_verify_image_artifact(
        artifact,
        expected_sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        expected_schema_hash=IMAGE_PREPROCESSING_SCHEMA_HASH,
    )
    assert verified is loaded


def test_artifact_verification_rejects_path_hash_schema_load_and_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "model.keras"
    artifact.write_bytes(b"artifact")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    with pytest.raises(ImageModelError):
        load_and_verify_image_artifact(
            artifact.with_suffix(".bin"),
            expected_sha256=digest,
            expected_schema_hash=IMAGE_PREPROCESSING_SCHEMA_HASH,
        )
    with pytest.raises(ImageModelError):
        load_and_verify_image_artifact(
            artifact, expected_sha256=digest, expected_schema_hash="0" * 64
        )
    with pytest.raises(ImageModelError):
        load_and_verify_image_artifact(
            artifact, expected_sha256="0" * 64, expected_schema_hash=IMAGE_PREPROCESSING_SCHEMA_HASH
        )

    def broken_loader(*args: object, **kwargs: object) -> object:
        raise ValueError("broken")

    monkeypatch.setattr(
        image_model,
        "_tensorflow",
        lambda: SimpleNamespace(
            keras=SimpleNamespace(models=SimpleNamespace(load_model=broken_loader))
        ),
    )
    with pytest.raises(ImageModelError):
        load_and_verify_image_artifact(
            artifact, expected_sha256=digest, expected_schema_hash=IMAGE_PREPROCESSING_SCHEMA_HASH
        )

    wrong = SimpleNamespace(input_shape=(None, 1, 1, 3), output_shape=(None, 2))
    monkeypatch.setattr(
        image_model,
        "_tensorflow",
        lambda: SimpleNamespace(
            keras=SimpleNamespace(models=SimpleNamespace(load_model=lambda *a, **k: wrong))
        ),
    )
    with pytest.raises(ImageModelError):
        load_and_verify_image_artifact(
            artifact, expected_sha256=digest, expected_schema_hash=IMAGE_PREPROCESSING_SCHEMA_HASH
        )


def test_tensorflow_missing_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_name: str) -> object:
        raise ImportError

    monkeypatch.setattr(image_model.importlib, "import_module", missing)
    with pytest.raises(ImageModelError, match="Google Colab"):
        image_model._tensorflow()


class _Layer:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.trainable = True

    def __call__(self, value: object, **kwargs: object) -> object:
        return object()


class _Backbone(_Layer):
    def __init__(self) -> None:
        super().__init__()
        self.layers = [_Layer() for _ in range(25)]


class _BuiltModel:
    pass


def _architecture_tf() -> tuple[SimpleNamespace, _Backbone]:
    backbone = _Backbone()
    layers = SimpleNamespace(
        RandomRotation=_Layer,
        RandomZoom=_Layer,
        RandomContrast=_Layer,
        RandomTranslation=_Layer,
        GlobalAveragePooling2D=_Layer,
        Dropout=_Layer,
        Dense=_Layer,
    )
    keras = SimpleNamespace(
        utils=SimpleNamespace(set_random_seed=lambda _seed: None),
        Input=lambda **kwargs: object(),
        Sequential=_Layer,
        applications=SimpleNamespace(MobileNetV3Small=lambda **kwargs: backbone),
        layers=layers,
        Model=lambda **kwargs: _BuiltModel(),
    )
    config = SimpleNamespace(experimental=SimpleNamespace(enable_op_determinism=lambda: None))
    return SimpleNamespace(keras=keras, config=config), backbone


def test_build_image_model_freezes_pretrained_backbone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_tf, backbone = _architecture_tf()
    monkeypatch.setattr(image_model, "_tensorflow", lambda: fake_tf)
    model, returned_backbone = image_model.build_image_model(pretrained=False)
    assert isinstance(model, _BuiltModel)
    assert returned_backbone is backbone
    assert backbone.trainable is False


class _History:
    def __init__(self) -> None:
        self.epoch = [0]


class _TrainingModel:
    input_shape = (None, 224, 224, 3)
    output_shape = (None, 1)

    def __init__(self) -> None:
        self.compile_calls = 0
        self.fit_calls = 0

    def compile(self, **kwargs: object) -> None:
        self.compile_calls += 1

    def fit(self, *args: object, **kwargs: object) -> _History:
        self.fit_calls += 1
        return _History()

    def predict(self, features: np.ndarray, *, verbose: int) -> np.ndarray:
        assert verbose == 0
        if len(features) == 2:
            return np.asarray([[0.1], [0.9]], dtype=float)
        return np.full((len(features), 1), 0.5, dtype=float)

    def save(self, path: Path) -> None:
        path.write_bytes(b"controlled-fake-keras-artifact")


def _training_tf(selected: _TrainingModel) -> SimpleNamespace:
    def callback(*args: object, **kwargs: object) -> object:
        return object()

    def metric(*args: object, **kwargs: object) -> object:
        return object()

    keras = SimpleNamespace(
        callbacks=SimpleNamespace(ModelCheckpoint=callback, EarlyStopping=callback),
        optimizers=SimpleNamespace(Adam=metric),
        metrics=SimpleNamespace(
            BinaryAccuracy=metric,
            Precision=metric,
            Recall=metric,
            AUC=metric,
        ),
        models=SimpleNamespace(load_model=lambda *args, **kwargs: selected),
    )
    return SimpleNamespace(keras=keras)


def test_training_orchestrator_packages_evidence_without_real_fit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controlled_root = Path(__file__).parents[1] / "data" / "controlled"
    training_model = _TrainingModel()
    selected = _TrainingModel()
    backbone = _Backbone()
    monkeypatch.setattr(image_model, "_tensorflow", lambda: _training_tf(selected))
    monkeypatch.setattr(
        image_model, "build_image_model", lambda pretrained=True: (training_model, backbone)
    )
    monkeypatch.setattr(
        image_model,
        "runtime_fingerprint",
        lambda: {
            "python": "test",
            "implementation": "test",
            "tensorflow": "2.21.0-test",
            "numpy": "test",
            "pillow": "test",
            "scikit_learn": "test",
        },
    )
    outputs = train_and_package_image_model(
        manifest_path=controlled_root / "manifest.csv",
        dataset_root=controlled_root,
        output_dir=tmp_path / "outputs",
        model_version="image-controlled-test-v1",
        training_commit_sha="a" * 40,
    )
    assert training_model.compile_calls == 2
    assert training_model.fit_calls == 2
    assert outputs.artifact_path.read_bytes() == b"controlled-fake-keras-artifact"
    assert outputs.report["held_out_test"]["macro_f1"] == 1.0  # type: ignore[index]
    assert outputs.report["dataset_scope"] == "controlled_synthetic_only"
    assert outputs.report["acceptance_passed"] is True
    assert outputs.confusion_matrix_path.is_file()
    registry = json.loads(outputs.registry_payload_path.read_text())
    assert registry["artifact_uri"].startswith("private://image/")
    assert registry["metrics"]["threshold"] == 0.15


def test_training_orchestrator_rejects_nonimmutable_commit(tmp_path: Path) -> None:
    with pytest.raises(ImageModelError):
        train_and_package_image_model(
            manifest_path=tmp_path / "missing.csv",
            dataset_root=tmp_path,
            output_dir=tmp_path,
            model_version="v1",
            training_commit_sha="not-a-sha",
        )
