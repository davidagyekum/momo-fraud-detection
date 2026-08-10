"""Restart-safe Google Colab runtime, manifest and checkpoint primitives."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import random
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Final, Protocol

import numpy as np

from momo_fdvs_ml.execution import ExecutionProfile, detect_execution_context

COLAB_FOUNDATION_VERSION: Final = "colab-foundation-v1"
RUN_MANIFEST_VERSION: Final = "colab-run-manifest-v1"
CHECKPOINT_LEDGER_VERSION: Final = "checkpoint-ledger-v1"
CHECKPOINT_VERSION: Final = "smoke-checkpoint-v1"
DEFAULT_DRIVE_ROOT: Final = Path("/content/drive/MyDrive/momo-fraud")
DEFAULT_VM_ROOT: Final = Path("/content/momo-work")
SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")
SHA1_PATTERN: Final = re.compile(r"^[0-9a-f]{40}$")
RUN_ID_PATTERN: Final = re.compile(
    r"^[0-9]{8}T[0-9]{6}Z_[a-z0-9][a-z0-9-]{1,31}_[a-f0-9]{8}_seed[0-9]+$"
)
SAFE_NAME_PATTERN: Final = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
RUN_STATUSES: Final = {"created", "running", "completed", "failed", "cancelled"}


class ColabFoundationError(RuntimeError):
    """Raised when a reproducibility, integrity or privacy invariant fails."""


def utc_now() -> datetime:
    """Return one timezone-aware UTC timestamp."""

    return datetime.now(UTC)


def isoformat_utc(value: datetime) -> str:
    """Serialize a timezone-aware datetime using the repository's UTC form."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ColabFoundationError("run timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a file without trusting its name or caller metadata."""

    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ColabFoundationError(f"unable to hash file {path.name}") from exc
    return digest.hexdigest()


def canonical_json_hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256_bytes(encoded)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Write and fsync a same-directory temporary file before atomic replacement."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except OSError as exc:
        raise ColabFoundationError(f"atomic write failed for {path.name}") from exc
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def atomic_write_json(path: Path, payload: Mapping[str, object]) -> str:
    """Atomically write canonical JSON and return its byte-level SHA-256."""

    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    atomic_write_bytes(path, encoded)
    return sha256_bytes(encoded)


def load_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ColabFoundationError(f"unable to load JSON object {path.name}") from exc
    if not isinstance(value, dict):
        raise ColabFoundationError(f"{path.name} must contain a JSON object")
    return value


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def _is_absolute_portable(value: str | Path) -> bool:
    text = str(value)
    return PurePosixPath(text).is_absolute() or PureWindowsPath(text).is_absolute()


def _native_colab_path(path: Path) -> Path:
    if os.name == "nt" and path.root and not path.drive:
        return Path(Path.cwd().anchor) / str(path).lstrip("/\\")
    return path


def _assert_distinct_nested_roots(drive_root: Path, vm_root: Path) -> None:
    drive = _resolved(drive_root)
    vm = _resolved(vm_root)
    if drive == vm or drive in vm.parents or vm in drive.parents:
        raise ColabFoundationError("Drive and VM roots must be distinct non-nested paths")


@dataclass(frozen=True)
class ColabPaths:
    """Generic durable-Drive and ephemeral-VM layout without personal path segments."""

    drive_root: Path
    vm_root: Path

    def __post_init__(self) -> None:
        if not self.drive_root.is_absolute() or not self.vm_root.is_absolute():
            raise ColabFoundationError("Colab Drive and VM roots must be absolute")
        if any(part == ".." for part in (*self.drive_root.parts, *self.vm_root.parts)):
            raise ColabFoundationError("Colab roots cannot contain parent traversal")
        _assert_distinct_nested_roots(self.drive_root, self.vm_root)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> ColabPaths:
        values = os.environ if environment is None else environment
        drive_root = _native_colab_path(
            Path(values.get("MOMO_FDVS_DRIVE_ROOT", str(DEFAULT_DRIVE_ROOT)))
        )
        vm_root = _native_colab_path(Path(values.get("MOMO_FDVS_VM_ROOT", str(DEFAULT_VM_ROOT))))
        return cls(drive_root=drive_root, vm_root=vm_root)

    def create(self) -> dict[str, Path]:
        layout = {
            "drive_datasets": self.drive_root / "datasets",
            "drive_checkpoints": self.drive_root / "checkpoints",
            "drive_runs": self.drive_root / "runs",
            "drive_registry": self.drive_root / "model_registry",
            "drive_governance": self.drive_root / "private-governance",
            "vm_repo": self.vm_root / "repo",
            "vm_data": self.vm_root / "data",
            "vm_cache": self.vm_root / "cache",
            "vm_outputs": self.vm_root / "outputs",
            "vm_checkpoints": self.vm_root / "checkpoints",
        }
        for path in layout.values():
            path.mkdir(parents=True, exist_ok=True)
        return layout


def make_run_id(task: str, commit: str, seed: int, *, started_at: datetime) -> str:
    """Build a stable, readable run ID from recorded non-secret inputs."""

    normalized_task = re.sub(r"[^a-z0-9-]+", "-", task.lower()).strip("-")
    if not normalized_task or len(normalized_task) > 32:
        raise ColabFoundationError("run task must normalize to 2-32 safe characters")
    if SHA1_PATTERN.fullmatch(commit) is None:
        raise ColabFoundationError("run commit must be a 40-character lowercase Git SHA")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ColabFoundationError("run seed must be a non-negative integer")
    timestamp = started_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{timestamp}_{normalized_task}_{commit[:8]}_seed{seed}"
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ColabFoundationError("generated run ID is invalid")
    return run_id


def seed_runtime(seed: int) -> None:
    """Seed Python and NumPy; framework-specific runs must add their framework seed."""

    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ColabFoundationError("runtime seed must be a non-negative integer")
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def _total_memory_bytes() -> int | None:
    sysconf = getattr(os, "sysconf", None)
    if not callable(sysconf):
        return None
    try:
        pages = sysconf("SC_PHYS_PAGES")
        page_size = sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        return None
    if not isinstance(pages, int) or not isinstance(page_size, int):
        return None
    return pages * page_size


def runtime_inventory(
    *,
    environment: Mapping[str, str] | None = None,
    packages: Sequence[str] = ("numpy", "pandas", "scikit-learn", "Pillow", "tensorflow"),
) -> dict[str, object]:
    """Record an allowlisted runtime inventory without copying environment secrets."""

    values = os.environ if environment is None else environment
    versions: dict[str, str | None] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    accelerator = "tpu" if values.get("COLAB_TPU_ADDR") else "unknown"
    visible_devices = values.get("CUDA_VISIBLE_DEVICES", "")
    if accelerator == "unknown" and visible_devices not in {"", "-1"}:
        accelerator = "gpu"
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": os.cpu_count(),
        "ram_bytes": _total_memory_bytes(),
        "accelerator": accelerator,
        "colab_release_tag": values.get("COLAB_RELEASE_TAG"),
        "colab_backend_version": values.get("COLAB_BACKEND_VERSION"),
        "package_versions": versions,
    }


def repository_state(repository_root: Path) -> dict[str, object]:
    """Record immutable Git state without logging remote URLs or credentials."""

    git_executable = shutil.which("git")
    if git_executable is None:
        raise ColabFoundationError("Git is unavailable for repository inspection")

    def run(*arguments: str) -> str:
        try:
            result = subprocess.run(  # noqa: S603 - fixed Git executable and fixed arguments
                [git_executable, "-C", str(repository_root), *arguments],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ColabFoundationError("unable to inspect repository state") from exc
        return result.stdout.strip()

    commit = run("rev-parse", "HEAD")
    if SHA1_PATTERN.fullmatch(commit) is None:
        raise ColabFoundationError("repository HEAD is not a full lowercase Git SHA")
    dirty_lines = run("status", "--porcelain=v1").splitlines()
    return {"commit": commit, "dirty": bool(dirty_lines)}


def prepare_repository_checkout(
    repository_url: str,
    commit: str,
    destination: Path,
    *,
    command_runner: Callable[[Sequence[str]], None] | None = None,
) -> None:
    """Clone/update and detach at an immutable commit using argument-safe commands."""

    if not repository_url.startswith("https://github.com/") or "@" in repository_url:
        raise ColabFoundationError("repository URL must be a credential-free GitHub HTTPS URL")
    if SHA1_PATTERN.fullmatch(commit) is None:
        raise ColabFoundationError("checkout commit must be a full lowercase Git SHA")
    git_executable = shutil.which("git")
    if git_executable is None:
        raise ColabFoundationError("Git is unavailable for repository checkout")
    runner = command_runner
    if runner is None:

        def default_runner(arguments: Sequence[str]) -> None:
            try:
                subprocess.run(list(arguments), check=True, timeout=300)  # noqa: S603
            except (OSError, subprocess.SubprocessError) as exc:
                raise ColabFoundationError("repository checkout command failed") from exc

        runner = default_runner
    if (destination / ".git").is_dir():
        runner((git_executable, "-C", str(destination), "fetch", "--prune", "origin"))
    elif destination.exists() and any(destination.iterdir()):
        raise ColabFoundationError("checkout destination exists and is not an empty repository")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        runner((git_executable, "clone", "--no-checkout", repository_url, str(destination)))
    runner((git_executable, "-C", str(destination), "checkout", "--detach", commit))


class SecretGetter(Protocol):
    def __call__(self, name: str) -> str | None: ...


class SecretBundle:
    """In-memory secret values with an intentionally redacted representation."""

    __slots__ = ("_values",)

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = dict(values)

    def __repr__(self) -> str:
        return f"SecretBundle(names={sorted(self._values)!r}, values=<redacted>)"

    def get(self, name: str) -> str:
        try:
            return self._values[name]
        except KeyError as exc:
            raise ColabFoundationError(f"secret {name} was not loaded") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._values))


def load_colab_secrets(names: Sequence[str], *, getter: SecretGetter | None = None) -> SecretBundle:
    """Load named Colab Secrets without printing or serializing their values."""

    if len(names) != len(set(names)) or not all(
        SAFE_NAME_PATTERN.fullmatch(name.lower()) for name in names
    ):
        raise ColabFoundationError("secret names must be unique and use safe characters")
    if getter is None:
        try:
            from google.colab import userdata  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ColabFoundationError("Google Colab secret storage is unavailable") from exc
        getter = userdata.get
    values: dict[str, str] = {}
    for name in names:
        value = getter(name)
        if not isinstance(value, str) or not value:
            raise ColabFoundationError(f"required Colab secret {name} is unavailable")
        values[name] = value
    return SecretBundle(values)


def _expect_iso_datetime(value: object, field: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not value:
        raise ColabFoundationError(f"{field} must be an ISO-8601 datetime")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ColabFoundationError(f"{field} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ColabFoundationError(f"{field} must include a timezone")


def _expect_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or SHA256_PATTERN.fullmatch(value) is None:
        raise ColabFoundationError(f"{field} must be a lowercase SHA-256")
    return value


def validate_run_manifest(manifest: Mapping[str, object]) -> None:
    """Validate the complete restart-safe manifest required for reproducible citation."""

    required = {
        "schema_version",
        "foundation_version",
        "run_id",
        "profile",
        "status",
        "started_at",
        "completed_at",
        "git",
        "notebook",
        "runtime_inventory",
        "seed",
        "dependency_lock",
        "dataset_manifest_sha256",
        "split_manifest_sha256",
        "config_sha256",
        "feature_schema_versions",
        "artifacts",
        "checkpoints",
        "sessions",
        "limitations",
        "acquisition_executed",
        "full_training_executed",
        "promotable",
    }
    if set(manifest) != required:
        raise ColabFoundationError("run manifest fields do not match the canonical contract")
    if manifest["schema_version"] != RUN_MANIFEST_VERSION:
        raise ColabFoundationError("unsupported Colab run manifest version")
    if manifest["foundation_version"] != COLAB_FOUNDATION_VERSION:
        raise ColabFoundationError("unsupported Colab foundation version")
    run_id = manifest["run_id"]
    if not isinstance(run_id, str) or RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ColabFoundationError("run_id is invalid")
    if manifest["profile"] not in {profile.value for profile in ExecutionProfile}:
        raise ColabFoundationError("run profile is invalid")
    if manifest["status"] not in RUN_STATUSES:
        raise ColabFoundationError("run status is invalid")
    _expect_iso_datetime(manifest["started_at"], "started_at")
    _expect_iso_datetime(manifest["completed_at"], "completed_at", nullable=True)
    git = manifest["git"]
    if not isinstance(git, dict) or set(git) != {"commit", "dirty"}:
        raise ColabFoundationError("run Git state is invalid")
    if SHA1_PATTERN.fullmatch(str(git["commit"])) is None or git["dirty"] is not False:
        raise ColabFoundationError("reportable runs require an immutable clean Git commit")
    notebook = manifest["notebook"]
    if (
        not isinstance(notebook, str)
        or not notebook.endswith(".ipynb")
        or _is_absolute_portable(notebook)
    ):
        raise ColabFoundationError("run notebook must be a relative .ipynb path")
    if not isinstance(manifest["runtime_inventory"], dict):
        raise ColabFoundationError("runtime_inventory must be an object")
    if (
        isinstance(manifest["seed"], bool)
        or not isinstance(manifest["seed"], int)
        or manifest["seed"] < 0
    ):
        raise ColabFoundationError("run seed must be a non-negative integer")
    lock = manifest["dependency_lock"]
    if not isinstance(lock, dict) or set(lock) != {"path", "sha256"}:
        raise ColabFoundationError("dependency_lock must contain path and sha256")
    if not isinstance(lock["path"], str) or Path(lock["path"]).is_absolute():
        raise ColabFoundationError("dependency lock path must be relative")
    _expect_sha256(lock["sha256"], "dependency lock sha256")
    for field in ("dataset_manifest_sha256", "split_manifest_sha256", "config_sha256"):
        _expect_sha256(manifest[field], field)
    schemas = manifest["feature_schema_versions"]
    if (
        not isinstance(schemas, list)
        or not schemas
        or not all(isinstance(item, str) and item for item in schemas)
    ):
        raise ColabFoundationError("feature_schema_versions must be a non-empty string list")
    artifacts = manifest["artifacts"]
    checkpoints = manifest["checkpoints"]
    sessions = manifest["sessions"]
    if not isinstance(artifacts, list):
        raise ColabFoundationError("artifacts must be a list")
    if not isinstance(checkpoints, list):
        raise ColabFoundationError("checkpoints must be a list")
    if not isinstance(sessions, list):
        raise ColabFoundationError("sessions must be a list")
    for item in artifacts:
        if not isinstance(item, dict) or set(item) != {"name", "path", "sha256", "bytes"}:
            raise ColabFoundationError("artifact entries are invalid")
        _expect_sha256(item["sha256"], "artifact sha256")
    for item in checkpoints:
        if not isinstance(item, dict) or set(item) != {"checkpoint_id", "sha256", "bytes"}:
            raise ColabFoundationError("checkpoint entries are invalid")
        _expect_sha256(item["sha256"], "checkpoint sha256")
    for item in sessions:
        if not isinstance(item, dict) or set(item) != {
            "session_index",
            "started_at",
            "completed_at",
            "resumed_from_checkpoint_sha256",
            "outcome",
        }:
            raise ColabFoundationError("session history entries are invalid")
        _expect_iso_datetime(item["started_at"], "session started_at")
        _expect_iso_datetime(item["completed_at"], "session completed_at", nullable=True)
        resumed_hash = item["resumed_from_checkpoint_sha256"]
        if resumed_hash is not None:
            _expect_sha256(resumed_hash, "resumed checkpoint sha256")
        if item["outcome"] not in {"active", "completed", "interrupted"}:
            raise ColabFoundationError("session outcome is invalid")
    limitations = manifest["limitations"]
    if (
        not isinstance(limitations, list)
        or not limitations
        or not all(isinstance(item, str) and item for item in limitations)
    ):
        raise ColabFoundationError("run limitations must be a non-empty string list")
    if manifest["profile"] == ExecutionProfile.SMOKE.value and (
        manifest["acquisition_executed"] is not False
        or manifest["full_training_executed"] is not False
        or manifest["promotable"] is not False
    ):
        raise ColabFoundationError(
            "smoke runs cannot acquire, fully train or produce promotable output"
        )
    if manifest["status"] == "completed" and manifest["completed_at"] is None:
        raise ColabFoundationError("completed runs require completed_at")


def new_run_manifest(
    *,
    run_id: str,
    profile: ExecutionProfile,
    git_state: Mapping[str, object],
    notebook: str,
    inventory: Mapping[str, object],
    seed: int,
    dependency_lock_path: str,
    dependency_lock_sha256: str,
    dataset_manifest_sha256: str,
    split_manifest_sha256: str,
    config_sha256: str,
    feature_schema_versions: Sequence[str],
    started_at: datetime,
) -> dict[str, object]:
    """Create a non-promotable manifest before any smoke component executes."""

    manifest: dict[str, object] = {
        "schema_version": RUN_MANIFEST_VERSION,
        "foundation_version": COLAB_FOUNDATION_VERSION,
        "run_id": run_id,
        "profile": profile.value,
        "status": "created",
        "started_at": isoformat_utc(started_at),
        "completed_at": None,
        "git": dict(git_state),
        "notebook": notebook,
        "runtime_inventory": dict(inventory),
        "seed": seed,
        "dependency_lock": {
            "path": dependency_lock_path,
            "sha256": dependency_lock_sha256,
        },
        "dataset_manifest_sha256": dataset_manifest_sha256,
        "split_manifest_sha256": split_manifest_sha256,
        "config_sha256": config_sha256,
        "feature_schema_versions": list(feature_schema_versions),
        "artifacts": [],
        "checkpoints": [],
        "sessions": [],
        "limitations": [
            "Fictitious tiny smoke fixtures only; no production prevalence or accuracy claim.",
            "Smoke artifacts are non-promotable and cannot replace reportable Colab FULL evidence.",
        ],
        "acquisition_executed": False,
        "full_training_executed": False,
        "promotable": False,
    }
    validate_run_manifest(manifest)
    return manifest


def start_session(
    manifest: dict[str, object], *, started_at: datetime, resumed_from_sha256: str | None
) -> None:
    validate_run_manifest(manifest)
    if manifest["status"] in {"completed", "cancelled"}:
        raise ColabFoundationError("terminal run cannot start another session")
    sessions = manifest["sessions"]
    assert isinstance(sessions, list)
    if sessions and isinstance(sessions[-1], dict) and sessions[-1]["completed_at"] is None:
        raise ColabFoundationError("previous run session is still open")
    if resumed_from_sha256 is not None:
        _expect_sha256(resumed_from_sha256, "resumed checkpoint sha256")
    sessions.append(
        {
            "session_index": len(sessions) + 1,
            "started_at": isoformat_utc(started_at),
            "completed_at": None,
            "resumed_from_checkpoint_sha256": resumed_from_sha256,
            "outcome": "active",
        }
    )
    manifest["status"] = "running"
    validate_run_manifest(manifest)


def complete_session(manifest: dict[str, object], *, completed_at: datetime) -> None:
    sessions = manifest.get("sessions")
    if not isinstance(sessions, list) or not sessions or not isinstance(sessions[-1], dict):
        raise ColabFoundationError("run has no open session")
    if sessions[-1].get("completed_at") is not None:
        raise ColabFoundationError("latest run session is already complete")
    sessions[-1]["completed_at"] = isoformat_utc(completed_at)
    sessions[-1]["outcome"] = "completed"
    validate_run_manifest(manifest)


def mark_interrupted_session(manifest: dict[str, object], *, detected_at: datetime) -> None:
    """Close an open session after a lost runtime without pretending it completed."""

    sessions = manifest.get("sessions")
    if not isinstance(sessions, list) or not sessions or not isinstance(sessions[-1], dict):
        raise ColabFoundationError("run has no session to mark interrupted")
    if sessions[-1].get("outcome") != "active" or sessions[-1].get("completed_at") is not None:
        raise ColabFoundationError("latest run session is not active")
    sessions[-1]["completed_at"] = isoformat_utc(detected_at)
    sessions[-1]["outcome"] = "interrupted"
    manifest["status"] = "failed"
    validate_run_manifest(manifest)


def complete_run(manifest: dict[str, object], *, completed_at: datetime) -> None:
    complete_session(manifest, completed_at=completed_at)
    manifest["status"] = "completed"
    manifest["completed_at"] = isoformat_utc(completed_at)
    validate_run_manifest(manifest)


def artifact_record(name: str, path: Path, *, relative_to: Path) -> dict[str, object]:
    if SAFE_NAME_PATTERN.fullmatch(name) is None:
        raise ColabFoundationError("artifact name is invalid")
    resolved = _resolved(path)
    root = _resolved(relative_to)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ColabFoundationError("artifact path escapes the run root") from exc
    return {
        "name": name,
        "path": relative.as_posix(),
        "sha256": sha256_file(resolved),
        "bytes": resolved.stat().st_size,
    }


def _checkpoint_envelope(
    *, run_id: str, checkpoint_id: str, state: Mapping[str, object], created_at: datetime
) -> dict[str, object]:
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ColabFoundationError("checkpoint run ID is invalid")
    if SAFE_NAME_PATTERN.fullmatch(checkpoint_id) is None:
        raise ColabFoundationError("checkpoint ID is invalid")
    return {
        "schema_version": CHECKPOINT_VERSION,
        "run_id": run_id,
        "checkpoint_id": checkpoint_id,
        "created_at": isoformat_utc(created_at),
        "state": dict(state),
    }


def _ledger_path(root: Path) -> Path:
    return root / "checkpoint-ledger.json"


def load_checkpoint_ledger(root: Path, *, run_id: str) -> dict[str, object]:
    path = _ledger_path(root)
    if not path.is_file():
        return {"schema_version": CHECKPOINT_LEDGER_VERSION, "run_id": run_id, "entries": []}
    ledger = load_json_object(path)
    if (
        ledger.get("schema_version") != CHECKPOINT_LEDGER_VERSION
        or ledger.get("run_id") != run_id
        or not isinstance(ledger.get("entries"), list)
    ):
        raise ColabFoundationError("checkpoint ledger identity is invalid")
    seen: set[str] = set()
    entries = ledger["entries"]
    assert isinstance(entries, list)
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "checkpoint_id",
            "filename",
            "sha256",
            "bytes",
            "created_at",
        }:
            raise ColabFoundationError("checkpoint ledger entry is invalid")
        checkpoint_id = entry["checkpoint_id"]
        if not isinstance(checkpoint_id, str) or checkpoint_id in seen:
            raise ColabFoundationError("checkpoint IDs must be unique")
        seen.add(checkpoint_id)
        _expect_sha256(entry["sha256"], "checkpoint sha256")
        _expect_iso_datetime(entry["created_at"], "checkpoint created_at")
    return ledger


def write_checkpoint(
    root: Path,
    *,
    run_id: str,
    checkpoint_id: str,
    state: Mapping[str, object],
    created_at: datetime,
    mirror_root: Path | None = None,
) -> dict[str, object]:
    """Atomically write, hash and optionally mirror one immutable checkpoint."""

    envelope = _checkpoint_envelope(
        run_id=run_id, checkpoint_id=checkpoint_id, state=state, created_at=created_at
    )
    checkpoint_path = root / f"{checkpoint_id}.json"
    if checkpoint_path.exists():
        raise ColabFoundationError("checkpoint IDs are immutable and cannot be overwritten")
    digest = atomic_write_json(checkpoint_path, envelope)
    entry: dict[str, object] = {
        "checkpoint_id": checkpoint_id,
        "filename": checkpoint_path.name,
        "sha256": digest,
        "bytes": checkpoint_path.stat().st_size,
        "created_at": isoformat_utc(created_at),
    }
    ledger = load_checkpoint_ledger(root, run_id=run_id)
    entries = ledger["entries"]
    assert isinstance(entries, list)
    entries.append(entry)
    atomic_write_json(_ledger_path(root), ledger)
    if mirror_root is not None:
        mirror_root.mkdir(parents=True, exist_ok=True)
        mirror_path = mirror_root / checkpoint_path.name
        atomic_write_bytes(mirror_path, checkpoint_path.read_bytes())
        if sha256_file(mirror_path) != digest:
            raise ColabFoundationError("mirrored checkpoint hash mismatch")
        atomic_write_json(_ledger_path(mirror_root), ledger)
    return entry


def load_checkpoint(
    root: Path,
    *,
    run_id: str,
    checkpoint_id: str,
    mirror_root: Path | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    """Hash-verify and load a checkpoint, restoring from its durable mirror if needed."""

    ledger_root = root if _ledger_path(root).is_file() else mirror_root
    if ledger_root is None:
        raise ColabFoundationError("checkpoint ledger is unavailable")
    ledger = load_checkpoint_ledger(ledger_root, run_id=run_id)
    entries = ledger["entries"]
    assert isinstance(entries, list)
    entry = next(
        (
            item
            for item in entries
            if isinstance(item, dict) and item.get("checkpoint_id") == checkpoint_id
        ),
        None,
    )
    if entry is None:
        raise ColabFoundationError("requested checkpoint is absent from the ledger")
    filename = entry["filename"]
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise ColabFoundationError("checkpoint filename is unsafe")
    checkpoint_path = root / filename
    if not checkpoint_path.is_file():
        if mirror_root is None:
            raise ColabFoundationError("checkpoint file is unavailable")
        mirror_path = mirror_root / filename
        if sha256_file(mirror_path) != entry["sha256"]:
            raise ColabFoundationError("durable checkpoint failed hash verification")
        atomic_write_bytes(checkpoint_path, mirror_path.read_bytes())
        atomic_write_json(_ledger_path(root), ledger)
    if sha256_file(checkpoint_path) != entry["sha256"]:
        raise ColabFoundationError("checkpoint failed hash verification")
    envelope = load_json_object(checkpoint_path)
    if (
        envelope.get("schema_version") != CHECKPOINT_VERSION
        or envelope.get("run_id") != run_id
        or envelope.get("checkpoint_id") != checkpoint_id
        or not isinstance(envelope.get("state"), dict)
    ):
        raise ColabFoundationError("checkpoint envelope identity is invalid")
    state = envelope["state"]
    assert isinstance(state, dict)
    return dict(state), dict(entry)


def sync_verified_file(source: Path, destination: Path, *, expected_sha256: str) -> None:
    """Atomically synchronize a verified result to durable storage."""

    _expect_sha256(expected_sha256, "synchronization sha256")
    if sha256_file(source) != expected_sha256:
        raise ColabFoundationError("source file failed synchronization hash verification")
    atomic_write_bytes(destination, source.read_bytes())
    if sha256_file(destination) != expected_sha256:
        raise ColabFoundationError("destination file failed synchronization hash verification")


def install_lock_contract(repository_root: Path) -> dict[str, object]:
    """Record the exact repository lock files shared by standard Colab notebooks."""

    relative_paths = (
        "ml/requirements-runtime.lock",
        "ml/requirements-training.lock",
        "ml/requirements-dev.lock",
    )
    locks: list[dict[str, object]] = []
    for relative_path in relative_paths:
        path = repository_root / relative_path
        lines = [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if not lines or any(not (line.startswith("-r ") or "==" in line) for line in lines):
            raise ColabFoundationError(f"{relative_path} contains an unpinned requirement")
        locks.append(
            {
                "path": relative_path,
                "sha256": sha256_file(path),
                "requirement_count": len(lines),
            }
        )
    return {
        "schema_version": "colab-lock-contract-v1",
        "python": ">=3.12,<3.13",
        "install_order": list(relative_paths),
        "locks": locks,
    }


def colab_preflight_report(
    repository_root: Path,
    *,
    paths: ColabPaths,
    profile: ExecutionProfile,
    notebook: str,
    require_colab: bool,
    environment: Mapping[str, str] | None = None,
) -> dict[str, object]:
    """Fail before smoke work if the runtime, checkout or paths are not reproducible."""

    if profile is not ExecutionProfile.SMOKE:
        raise ColabFoundationError("PR12 preflight requires the smoke profile")
    if not notebook.endswith(".ipynb") or _is_absolute_portable(notebook):
        raise ColabFoundationError("preflight notebook must be a relative .ipynb path")
    context = detect_execution_context(environment)
    if require_colab and (not context.is_colab or context.is_ci):
        raise ColabFoundationError("owner-operated preflight requires non-CI Google Colab")
    git_state = repository_state(repository_root)
    if git_state["dirty"] is not False:
        raise ColabFoundationError("Colab preflight requires a clean immutable checkout")
    inventory = runtime_inventory(environment=environment)
    python_version = inventory["python_version"]
    if not isinstance(python_version, str) or not python_version.startswith("3.12."):
        raise ColabFoundationError("Colab preflight requires Python 3.12")
    layout = paths.create()
    return {
        "schema_version": "colab-preflight-report-v1",
        "foundation_version": COLAB_FOUNDATION_VERSION,
        "profile": profile.value,
        "notebook": notebook,
        "git": git_state,
        "runtime_inventory": inventory,
        "lock_contract": install_lock_contract(repository_root),
        "paths": {name: str(path) for name, path in sorted(layout.items())},
        "is_colab": context.is_colab,
        "is_ci": context.is_ci,
        "acquisition_executed": False,
        "full_training_executed": False,
    }
