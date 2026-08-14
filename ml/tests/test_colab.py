from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import momo_fdvs_ml.colab as colab
from momo_fdvs_ml.colab import (
    ColabFoundationError,
    ColabPaths,
    SecretBundle,
    artifact_record,
    atomic_write_bytes,
    atomic_write_json,
    canonical_json_hash,
    colab_preflight_report,
    complete_run,
    complete_session,
    install_lock_contract,
    isoformat_utc,
    load_checkpoint,
    load_checkpoint_ledger,
    load_colab_secrets,
    load_json_object,
    make_run_id,
    mark_interrupted_session,
    new_run_manifest,
    prepare_repository_checkout,
    repository_state,
    runtime_inventory,
    seed_runtime,
    sha256_bytes,
    sha256_file,
    start_session,
    sync_verified_file,
    validate_run_manifest,
    write_checkpoint,
)
from momo_fdvs_ml.execution import ExecutionProfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STARTED_AT = datetime(2026, 8, 10, 14, 31, tzinfo=UTC)
COMMIT = "a" * 40
SHA256 = "b" * 64
ABSOLUTE_ROOT = Path(Path.cwd().anchor) / "momo-fdvs-test-root"


def _manifest() -> dict[str, object]:
    run_id = make_run_id("smoke-foundation", COMMIT, 42, started_at=STARTED_AT)
    return new_run_manifest(
        run_id=run_id,
        profile=ExecutionProfile.SMOKE,
        git_state={"commit": COMMIT, "dirty": False},
        notebook="ml/notebooks/colab/01_tiny_restart_safe_smoke.ipynb",
        inventory={"python_version": "3.12.10"},
        seed=42,
        dependency_lock_path="ml/requirements-runtime.lock",
        dependency_lock_sha256=SHA256,
        dataset_manifest_sha256="c" * 64,
        split_manifest_sha256="d" * 64,
        config_sha256="e" * 64,
        feature_schema_versions=["fixture-v1"],
        started_at=STARTED_AT,
    )


def test_hash_json_and_atomic_file_primitives(tmp_path: Path) -> None:
    payload = {"b": 2, "a": 1}
    assert canonical_json_hash(payload) == canonical_json_hash({"a": 1, "b": 2})

    raw = tmp_path / "raw.bin"
    atomic_write_bytes(raw, b"fixture")
    assert sha256_file(raw) == sha256_bytes(b"fixture")
    document = tmp_path / "document.json"
    digest = atomic_write_json(document, payload)
    assert digest == sha256_file(document)
    assert load_json_object(document) == payload
    assert not list(tmp_path.glob("*.tmp"))


def test_json_and_hash_loaders_reject_missing_malformed_and_non_objects(tmp_path: Path) -> None:
    with pytest.raises(ColabFoundationError, match="unable to hash"):
        sha256_file(tmp_path / "missing")
    with pytest.raises(ColabFoundationError, match="unable to load"):
        load_json_object(tmp_path / "missing.json")
    malformed = tmp_path / "malformed.json"
    malformed.write_text("not-json", encoding="utf-8")
    with pytest.raises(ColabFoundationError, match="unable to load"):
        load_json_object(malformed)
    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")
    with pytest.raises(ColabFoundationError, match="must contain"):
        load_json_object(array)


def test_isoformat_requires_timezone() -> None:
    assert isoformat_utc(STARTED_AT) == "2026-08-10T14:31:00Z"
    with pytest.raises(ColabFoundationError, match="timezone-aware"):
        isoformat_utc(datetime(2026, 8, 10))


def test_colab_paths_use_generic_environment_and_create_layout(tmp_path: Path) -> None:
    paths = ColabPaths.from_environment(
        {
            "MOMO_FDVS_DRIVE_ROOT": str(tmp_path / "drive"),
            "MOMO_FDVS_VM_ROOT": str(tmp_path / "vm"),
        }
    )
    layout = paths.create()
    assert set(layout) == {
        "drive_datasets",
        "drive_checkpoints",
        "drive_runs",
        "drive_registry",
        "drive_governance",
        "vm_repo",
        "vm_data",
        "vm_cache",
        "vm_outputs",
        "vm_checkpoints",
    }
    assert all(path.is_dir() for path in layout.values())
    defaults = ColabPaths.from_environment({})
    assert defaults.drive_root.as_posix().endswith("/content/drive/MyDrive/momo-fraud")
    assert defaults.vm_root.as_posix().endswith("/content/momo-work")


@pytest.mark.parametrize(
    ("drive", "vm", "message"),
    [
        (Path("relative-drive"), ABSOLUTE_ROOT / "vm", "must be absolute"),
        (ABSOLUTE_ROOT / "same", ABSOLUTE_ROOT / "same", "distinct non-nested"),
        (ABSOLUTE_ROOT / "root", ABSOLUTE_ROOT / "root/vm", "distinct non-nested"),
    ],
)
def test_colab_paths_reject_unsafe_layouts(drive: Path, vm: Path, message: str) -> None:
    with pytest.raises(ColabFoundationError, match=message):
        ColabPaths(drive_root=drive, vm_root=vm)


def test_run_id_is_reproducible_and_validated() -> None:
    assert (
        make_run_id("Smoke Foundation", COMMIT, 42, started_at=STARTED_AT)
        == "20260810T143100Z_smoke-foundation_aaaaaaaa_seed42"
    )
    for task, commit, seed, message in (
        ("!", COMMIT, 42, "task"),
        ("x" * 40, COMMIT, 42, "task"),
        ("smoke", "bad", 42, "commit"),
        ("smoke", COMMIT, -1, "seed"),
        ("smoke", COMMIT, True, "seed"),
    ):
        with pytest.raises(ColabFoundationError, match=message):
            make_run_id(task, commit, seed, started_at=STARTED_AT)  # type: ignore[arg-type]


def test_runtime_seeding_is_repeatable_and_rejects_invalid_values() -> None:
    seed_runtime(10)
    first = (np.random.random(), os.environ["PYTHONHASHSEED"])
    seed_runtime(10)
    second = (np.random.random(), os.environ["PYTHONHASHSEED"])
    assert first == second
    for invalid in (-1, True, 1.5):
        with pytest.raises(ColabFoundationError, match="non-negative"):
            seed_runtime(invalid)  # type: ignore[arg-type]


def test_runtime_inventory_is_allowlisted_and_accelerator_aware(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(colab, "_total_memory_bytes", lambda: 123)
    inventory = runtime_inventory(
        environment={"CUDA_VISIBLE_DEVICES": "0", "SECRET_TOKEN": "never-record"},
        packages=("numpy", "definitely-absent-package"),
    )
    assert inventory["accelerator"] == "gpu"
    assert inventory["ram_bytes"] == 123
    assert "SECRET_TOKEN" not in json.dumps(inventory)
    assert inventory["package_versions"]["numpy"]  # type: ignore[index]
    assert inventory["package_versions"]["definitely-absent-package"] is None  # type: ignore[index]
    assert runtime_inventory(environment={"COLAB_TPU_ADDR": "present"})["accelerator"] == "tpu"


def test_total_memory_handles_missing_and_valid_sysconf(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        colab.os,
        "sysconf",
        lambda name: {"SC_PHYS_PAGES": 4, "SC_PAGE_SIZE": 8}[name],
        raising=False,
    )
    assert colab._total_memory_bytes() == 32
    monkeypatch.setattr(colab.os, "sysconf", lambda _name: "bad", raising=False)
    assert colab._total_memory_bytes() is None


def test_repository_state_records_commit_and_dirty_without_remote(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    outputs = iter([COMMIT, " M fixture.txt"])

    def fake_run(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(stdout=next(outputs))

    monkeypatch.setattr(colab.shutil, "which", lambda _name: "C:/Git/git.exe")
    monkeypatch.setattr(colab.subprocess, "run", fake_run)
    assert repository_state(tmp_path) == {"commit": COMMIT, "dirty": True}


def test_repository_state_rejects_missing_git_bad_sha_and_command_error(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(colab.shutil, "which", lambda _name: None)
    with pytest.raises(ColabFoundationError, match="Git is unavailable"):
        repository_state(tmp_path)

    monkeypatch.setattr(colab.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(
        colab.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout="bad")
    )
    with pytest.raises(ColabFoundationError, match="HEAD"):
        repository_state(tmp_path)

    def fail(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(colab.subprocess, "run", fail)
    with pytest.raises(ColabFoundationError, match="unable to inspect"):
        repository_state(tmp_path)


def test_prepare_checkout_builds_safe_clone_and_update_commands(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(colab.shutil, "which", lambda _name: "git")
    commands: list[tuple[str, ...]] = []

    def runner(command) -> None:  # type: ignore[no-untyped-def]
        commands.append(tuple(command))

    destination = tmp_path / "repo"
    prepare_repository_checkout(
        "https://github.com/example/project.git", COMMIT, destination, command_runner=runner
    )
    assert commands[0][:3] == ("git", "clone", "--no-checkout")
    assert commands[-1][-2:] == ("--detach", COMMIT)

    (destination / ".git").mkdir(parents=True)
    commands.clear()
    prepare_repository_checkout(
        "https://github.com/example/project.git", COMMIT, destination, command_runner=runner
    )
    assert "fetch" in commands[0]


def test_prepare_checkout_rejects_credentials_sha_and_nonempty_destination(
    monkeypatch, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(colab.shutil, "which", lambda _name: "git")
    for url, commit, message in (
        ("https://token@github.com/example/project.git", COMMIT, "credential-free"),
        ("https://example.com/project.git", COMMIT, "GitHub HTTPS"),
        ("https://github.com/example/project.git", "bad", "full lowercase"),
    ):
        with pytest.raises(ColabFoundationError, match=message):
            prepare_repository_checkout(
                url, commit, tmp_path / "repo", command_runner=lambda _: None
            )
    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "file.txt").write_text("occupied", encoding="utf-8")
    with pytest.raises(ColabFoundationError, match="not an empty"):
        prepare_repository_checkout(
            "https://github.com/example/project.git",
            COMMIT,
            destination,
            command_runner=lambda _: None,
        )


def test_secret_bundle_redacts_values_and_loads_by_name() -> None:
    bundle = load_colab_secrets(["kaggle_api_token"], getter=lambda _name: "super-sensitive-value")
    assert bundle.names == ("kaggle_api_token",)
    assert bundle.get("kaggle_api_token") == "super-sensitive-value"
    assert "super-sensitive-value" not in repr(bundle)
    with pytest.raises(ColabFoundationError, match="was not loaded"):
        bundle.get("missing")


def test_secret_loader_rejects_duplicate_unsafe_and_missing_names() -> None:
    for names in (["same", "same"], ["unsafe name"]):
        with pytest.raises(ColabFoundationError, match="unique and use safe"):
            load_colab_secrets(names, getter=lambda _name: "value")
    with pytest.raises(ColabFoundationError, match="unavailable"):
        load_colab_secrets(["missing"], getter=lambda _name: None)
    assert "values=<redacted>" in repr(SecretBundle({"name": "value"}))


def test_new_manifest_session_and_completion_lifecycle() -> None:
    manifest = _manifest()
    start_session(manifest, started_at=STARTED_AT, resumed_from_sha256=None)
    assert manifest["status"] == "running"
    complete_run(manifest, completed_at=datetime(2026, 8, 10, 14, 32, tzinfo=UTC))
    assert manifest["status"] == "completed"
    validate_run_manifest(manifest)
    with pytest.raises(ColabFoundationError, match="terminal"):
        start_session(manifest, started_at=STARTED_AT, resumed_from_sha256=None)


def test_portable_colab_manifest_schema_aligns_with_executable_contract() -> None:
    schema = json.loads(
        (REPOSITORY_ROOT / "ml/contracts/colab-run-manifest-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    manifest = _manifest()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(manifest)
    assert set(schema["properties"]) == set(manifest)


def test_interrupted_session_can_resume_with_same_run_id() -> None:
    manifest = _manifest()
    start_session(manifest, started_at=STARTED_AT, resumed_from_sha256=None)
    mark_interrupted_session(manifest, detected_at=datetime(2026, 8, 10, 14, 32, tzinfo=UTC))
    start_session(
        manifest,
        started_at=datetime(2026, 8, 10, 14, 33, tzinfo=UTC),
        resumed_from_sha256=SHA256,
    )
    sessions = manifest["sessions"]
    assert isinstance(sessions, list)
    assert sessions[0]["outcome"] == "interrupted"
    assert sessions[1]["resumed_from_checkpoint_sha256"] == SHA256


def test_session_helpers_reject_missing_open_or_duplicate_sessions() -> None:
    manifest = _manifest()
    with pytest.raises(ColabFoundationError, match="no open session"):
        complete_session(manifest, completed_at=STARTED_AT)
    with pytest.raises(ColabFoundationError, match="no session"):
        mark_interrupted_session(manifest, detected_at=STARTED_AT)
    start_session(manifest, started_at=STARTED_AT, resumed_from_sha256=None)
    with pytest.raises(ColabFoundationError, match="still open"):
        start_session(manifest, started_at=STARTED_AT, resumed_from_sha256=None)
    complete_session(manifest, completed_at=STARTED_AT)
    with pytest.raises(ColabFoundationError, match="already complete"):
        complete_session(manifest, completed_at=STARTED_AT)
    with pytest.raises(ColabFoundationError, match="not active"):
        mark_interrupted_session(manifest, detected_at=STARTED_AT)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda value: value.pop("notebook"), "fields"),
        (lambda value: value.update(schema_version="bad"), "manifest version"),
        (lambda value: value.update(foundation_version="bad"), "foundation version"),
        (lambda value: value.update(run_id="bad"), "run_id"),
        (lambda value: value.update(profile="turbo"), "profile"),
        (lambda value: value.update(status="ok"), "status"),
        (lambda value: value.update(started_at="bad"), "ISO-8601"),
        (lambda value: value.update(git=[]), "Git state"),
        (lambda value: value.update(git={"commit": COMMIT, "dirty": True}), "immutable"),
        (lambda value: value.update(notebook="/absolute.ipynb"), "relative"),
        (lambda value: value.update(runtime_inventory=[]), "runtime_inventory"),
        (lambda value: value.update(seed=True), "seed"),
        (lambda value: value.update(dependency_lock=[]), "dependency_lock"),
        (lambda value: value.update(dataset_manifest_sha256="bad"), "SHA-256"),
        (lambda value: value.update(feature_schema_versions=[]), "non-empty"),
        (lambda value: value.update(artifacts={}), "artifacts must"),
        (lambda value: value.update(checkpoints={}), "checkpoints must"),
        (lambda value: value.update(sessions={}), "sessions must"),
        (lambda value: value.update(limitations=[]), "limitations"),
        (lambda value: value.update(promotable=True), "smoke runs cannot"),
    ],
)
def test_manifest_validator_rejects_invalid_contracts(mutation, message: str) -> None:  # type: ignore[no-untyped-def]
    manifest = _manifest()
    mutation(manifest)
    with pytest.raises(ColabFoundationError, match=message):
        validate_run_manifest(manifest)


def test_manifest_validator_rejects_bad_nested_entries_and_completed_without_time() -> None:
    for field, entry, message in (
        ("artifacts", [{}], "artifact entries"),
        ("checkpoints", [{}], "checkpoint entries"),
        ("sessions", [{}], "session history"),
    ):
        manifest = _manifest()
        manifest[field] = entry
        with pytest.raises(ColabFoundationError, match=message):
            validate_run_manifest(manifest)
    manifest = _manifest()
    manifest["status"] = "completed"
    with pytest.raises(ColabFoundationError, match="require completed_at"):
        validate_run_manifest(manifest)


def test_artifact_record_is_contained_and_hashed(tmp_path: Path) -> None:
    artifact = tmp_path / "run" / "artifact.json"
    atomic_write_json(artifact, {"fixture": True})
    record = artifact_record("smoke_artifact", artifact, relative_to=tmp_path / "run")
    assert record["path"] == "artifact.json"
    assert record["sha256"] == sha256_file(artifact)
    with pytest.raises(ColabFoundationError, match="name"):
        artifact_record("Bad Name", artifact, relative_to=tmp_path / "run")
    with pytest.raises(ColabFoundationError, match="escapes"):
        artifact_record("safe", artifact, relative_to=tmp_path / "elsewhere")


def test_checkpoint_write_mirror_restore_and_corruption_rejection(tmp_path: Path) -> None:
    run_id = _manifest()["run_id"]
    assert isinstance(run_id, str)
    local = tmp_path / "local"
    mirror = tmp_path / "mirror"
    entry = write_checkpoint(
        local,
        run_id=run_id,
        checkpoint_id="transaction",
        state={"step": 1},
        created_at=STARTED_AT,
        mirror_root=mirror,
    )
    assert entry["sha256"] == sha256_file(local / "transaction.json")
    state, restored_entry = load_checkpoint(
        local, run_id=run_id, checkpoint_id="transaction", mirror_root=mirror
    )
    assert state == {"step": 1}
    assert restored_entry == entry

    (local / "transaction.json").unlink()
    state, _ = load_checkpoint(
        local, run_id=run_id, checkpoint_id="transaction", mirror_root=mirror
    )
    assert state == {"step": 1}
    (local / "transaction.json").write_bytes(b"corrupt")
    with pytest.raises(ColabFoundationError, match="hash verification"):
        load_checkpoint(local, run_id=run_id, checkpoint_id="transaction", mirror_root=mirror)


def test_checkpoint_guards_identity_immutability_and_ledger_shape(tmp_path: Path) -> None:
    run_id = _manifest()["run_id"]
    assert isinstance(run_id, str)
    root = tmp_path / "checkpoints"
    assert load_checkpoint_ledger(root, run_id=run_id)["entries"] == []
    write_checkpoint(
        root,
        run_id=run_id,
        checkpoint_id="one",
        state={"ok": True},
        created_at=STARTED_AT,
    )
    with pytest.raises(ColabFoundationError, match="cannot be overwritten"):
        write_checkpoint(
            root,
            run_id=run_id,
            checkpoint_id="one",
            state={"ok": True},
            created_at=STARTED_AT,
        )
    with pytest.raises(ColabFoundationError, match="absent"):
        load_checkpoint(root, run_id=run_id, checkpoint_id="missing")
    ledger_path = root / "checkpoint-ledger.json"
    ledger = load_json_object(ledger_path)
    ledger["run_id"] = "wrong"
    atomic_write_json(ledger_path, ledger)
    with pytest.raises(ColabFoundationError, match="identity"):
        load_checkpoint_ledger(root, run_id=run_id)


def test_sync_verified_file_checks_source_and_destination(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(b"fixture")
    digest = sha256_file(source)
    sync_verified_file(source, destination, expected_sha256=digest)
    assert destination.read_bytes() == b"fixture"
    with pytest.raises(ColabFoundationError, match="source file"):
        sync_verified_file(source, destination, expected_sha256="0" * 64)
    with pytest.raises(ColabFoundationError, match="must be"):
        sync_verified_file(source, destination, expected_sha256="bad")


def test_lock_contract_records_exact_repository_files() -> None:
    contract = install_lock_contract(REPOSITORY_ROOT)
    assert contract["schema_version"] == "colab-lock-contract-v1"
    assert len(contract["locks"]) == 4  # type: ignore[arg-type]
    assert all(len(lock["sha256"]) == 64 for lock in contract["locks"])  # type: ignore[union-attr]


def test_lock_contract_rejects_unpinned_or_empty_files(tmp_path: Path) -> None:
    (tmp_path / "ml").mkdir()
    for name in ("runtime", "training", "dev"):
        (tmp_path / "ml" / f"requirements-{name}.lock").write_text(
            "package>=1\n" if name == "runtime" else "package==1\n", encoding="utf-8"
        )
    with pytest.raises(ColabFoundationError, match="unpinned"):
        install_lock_contract(tmp_path)


def test_lock_contract_rejects_numpy_incompatible_with_paddleocr(tmp_path: Path) -> None:
    ml_root = tmp_path / "ml"
    ml_root.mkdir()
    (ml_root / "requirements-runtime.lock").write_text("numpy==2.5.2\n", encoding="utf-8")
    (ml_root / "requirements-ocr.lock").write_text(
        "-r requirements-runtime.lock\neasyocr==1.7.2\npaddleocr==3.7.0\npaddlepaddle==3.3.1\n",
        encoding="utf-8",
    )
    for name in ("training", "dev"):
        (ml_root / f"requirements-{name}.lock").write_text("package==1\n", encoding="utf-8")

    with pytest.raises(ColabFoundationError, match=r"PaddleOCR requires numpy<2\.4"):
        install_lock_contract(tmp_path)


@pytest.mark.parametrize("numpy_requirement", ["", "numpy==not-a-version\n"])
def test_lock_contract_requires_numeric_numpy_for_paddleocr(
    tmp_path: Path, numpy_requirement: str
) -> None:
    ml_root = tmp_path / "ml"
    ml_root.mkdir()
    (ml_root / "requirements-runtime.lock").write_text(
        numpy_requirement or "package==1\n", encoding="utf-8"
    )
    (ml_root / "requirements-ocr.lock").write_text("paddleocr==3.7.0\n", encoding="utf-8")
    for name in ("training", "dev"):
        (ml_root / f"requirements-{name}.lock").write_text("package==1\n", encoding="utf-8")

    with pytest.raises(ColabFoundationError, match="numeric pinned numpy"):
        install_lock_contract(tmp_path)


def test_lock_contract_does_not_apply_paddle_constraint_without_paddleocr(tmp_path: Path) -> None:
    ml_root = tmp_path / "ml"
    ml_root.mkdir()
    for name in ("runtime", "ocr", "training", "dev"):
        (ml_root / f"requirements-{name}.lock").write_text("package==1\n", encoding="utf-8")

    assert len(install_lock_contract(tmp_path)["locks"]) == 4  # type: ignore[arg-type]


def test_preflight_records_clean_state_locks_paths_and_no_execution(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(colab, "repository_state", lambda _root: {"commit": COMMIT, "dirty": False})
    monkeypatch.setattr(
        colab,
        "runtime_inventory",
        lambda **_kwargs: {"python_version": "3.12.10", "secret": False},
    )
    monkeypatch.setattr(colab, "install_lock_contract", lambda _root: {"locks": []})
    paths = ColabPaths(drive_root=tmp_path / "drive", vm_root=tmp_path / "vm")
    report = colab_preflight_report(
        tmp_path,
        paths=paths,
        profile=ExecutionProfile.SMOKE,
        notebook="ml/notebooks/colab/fixture.ipynb",
        require_colab=True,
        environment={"COLAB_RELEASE_TAG": "release", "COLAB_BACKEND_VERSION": "backend"},
    )
    assert report["is_colab"] is True
    assert report["acquisition_executed"] is False
    assert report["full_training_executed"] is False


def test_preflight_rejects_profile_notebook_runtime_context_and_dirty_checkout(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    paths = ColabPaths(drive_root=tmp_path / "drive", vm_root=tmp_path / "vm")
    with pytest.raises(ColabFoundationError, match="smoke profile"):
        colab_preflight_report(
            tmp_path,
            paths=paths,
            profile=ExecutionProfile.UNIT,
            notebook="fixture.ipynb",
            require_colab=False,
        )
    with pytest.raises(ColabFoundationError, match="relative"):
        colab_preflight_report(
            tmp_path,
            paths=paths,
            profile=ExecutionProfile.SMOKE,
            notebook="/fixture.ipynb",
            require_colab=False,
        )
    with pytest.raises(ColabFoundationError, match="requires non-CI"):
        colab_preflight_report(
            tmp_path,
            paths=paths,
            profile=ExecutionProfile.SMOKE,
            notebook="fixture.ipynb",
            require_colab=True,
            environment={"CI": "true"},
        )
    monkeypatch.setattr(colab, "repository_state", lambda _root: {"commit": COMMIT, "dirty": True})
    with pytest.raises(ColabFoundationError, match="clean immutable"):
        colab_preflight_report(
            tmp_path,
            paths=paths,
            profile=ExecutionProfile.SMOKE,
            notebook="fixture.ipynb",
            require_colab=False,
        )
