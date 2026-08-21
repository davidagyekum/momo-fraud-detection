"""Build and verify a deterministic, repository-safe academic submission ZIP."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
from typing import Any, cast, Mapping
import zipfile


MANIFEST_NAME = "FINAL_SUBMISSION_PACKAGE_MANIFEST.json"
SCHEMA_VERSION = "momo-fdvs-academic-submission-package-v1"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 250 * 1024 * 1024

EVIDENCE_MANIFEST_FIELDS = [
    "evidence_id",
    "requirement_id",
    "chapter_section",
    "title",
    "file_path",
    "type",
    "SHA",
    "environment",
    "contains_sensitive_data",
    "safe_for_submission",
    "notes",
]

DENIED_PREFIXES = (
    ".git",
    ".local",
    ".secrets",
    ".venv",
    ".worktrees",
    ".superpowers",
    ".playwright-cli",
    "uploads",
    "private_uploads",
    "private-storage",
    "datasets",
    "data/private",
    "data/raw",
    "data/staging",
    "data/quarantine",
    "data/acquisition-requests",
    "data/consent-records",
    "data/withdrawal-records",
    "ml/data/private",
    "ml/data/raw",
    "ml/data/staging",
    "ml/data/authorised",
    "ml/data/authorized",
    "artifacts",
    "model-artifacts",
    "checkpoints",
    "ml/checkpoints",
    "ml/models",
    "consent-records",
    "node_modules",
    ".expo",
    ".vite",
    "dist",
    "build",
    "web-build",
    "coverage",
    "playwright-report",
    "test-results",
    "output",
)

DENIED_SUFFIXES = {
    ".7z",
    ".gz",
    ".h5",
    ".hdf5",
    ".joblib",
    ".keras",
    ".key",
    ".onnx",
    ".p12",
    ".pem",
    ".pfx",
    ".pickle",
    ".pkl",
    ".pt",
    ".pth",
    ".rar",
    ".tar",
    ".tflite",
    ".zip",
}

LIMITATIONS = [
    "No hosted, staging, or production deployment is claimed.",
    "Hosted GitHub Actions acceptance is unverified because of the recorded billing lock.",
    "Final native Android and iOS device automation was not performed; the accepted mobile journey uses the Expo web export in Chromium.",
    "Verification uses stored or imported reference records and is not live MNO confirmation.",
    "The P12 image model failed acceptance at held-out macro F1 0.333333 and remains inactive/unavailable.",
    "No locked-test access or model training occurred during the final completion or submission freeze.",
]


class PackageSafetyError(RuntimeError):
    """Raised when a source path or repository state is unsafe to package."""


class PackageVerificationError(RuntimeError):
    """Raised when a generated package fails independent verification."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_submission_path(path: str, size_bytes: int) -> None:
    """Reject paths or file types that must never enter the submission ZIP."""
    if not path or "\x00" in path or "\\" in path:
        raise PackageSafetyError(f"Unsafe repository path: {path!r}")
    if size_bytes < 0 or size_bytes > MAX_FILE_BYTES:
        raise PackageSafetyError(f"Unsafe file size for {path!r}: {size_bytes}")

    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise PackageSafetyError(f"Unsafe repository path: {path!r}")
    if re.match(r"^[A-Za-z]:", path):
        raise PackageSafetyError(f"Windows drive path is not allowed: {path!r}")

    normalised = pure.as_posix()
    lowered = normalised.casefold()
    for prefix in DENIED_PREFIXES:
        denied = prefix.casefold()
        if lowered == denied or lowered.startswith(f"{denied}/"):
            raise PackageSafetyError(f"Denied repository path: {path!r}")

    if any(
        part.casefold().startswith(".env") and part.casefold() != ".env.example"
        for part in pure.parts
    ):
        raise PackageSafetyError(f"Environment file is not allowed: {path!r}")
    if pure.suffix.casefold() in DENIED_SUFFIXES:
        raise PackageSafetyError(f"Denied file extension: {path!r}")


def _manifest_for_entries(
    entries: Mapping[str, bytes], metadata: Mapping[str, str]
) -> dict[str, Any]:
    commit = metadata.get("commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise PackageSafetyError(
            "Package metadata requires a lowercase 40-character Git commit."
        )

    files: list[dict[str, Any]] = []
    total_size = 0
    for path in sorted(entries):
        data = entries[path]
        validate_submission_path(path, len(data))
        total_size += len(data)
        files.append(
            {"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)}
        )
    if total_size > MAX_TOTAL_BYTES:
        raise PackageSafetyError(f"Package content exceeds {MAX_TOTAL_BYTES} bytes.")

    return {
        "schema_version": SCHEMA_VERSION,
        "package_name": "MoMo-FDVS academic submission candidate",
        "source": {
            "repository": metadata.get("repository", "unknown"),
            "branch": metadata.get("branch", "unknown"),
            "commit": commit,
            "commit_time_utc": metadata.get("commit_time_utc", "unknown"),
        },
        "construction": {
            "source_kind": "exact-git-tree",
            "manifest_excludes_self": True,
            "zip_timestamp_utc": "1980-01-01T00:00:00Z",
            "file_order": "UTF-8 path order",
            "derived_artifact_committed": False,
        },
        "limitations": LIMITATIONS,
        "file_count_excluding_manifest": len(files),
        "total_size_bytes_excluding_manifest": total_size,
        "files": files,
    }


def _zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def write_deterministic_package(
    output_path: Path,
    entries: Mapping[str, bytes],
    metadata: Mapping[str, str],
) -> dict[str, Any]:
    """Write package contents with stable metadata, ordering, and compression."""
    manifest = _manifest_for_entries(entries, metadata)
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        archive.writestr(_zip_info(MANIFEST_NAME), manifest_bytes, compresslevel=9)
        for path in sorted(entries):
            archive.writestr(_zip_info(path), entries[path], compresslevel=9)
    return manifest


def _validate_evidence_rows(
    rows: list[dict[str, str]], available_paths: set[str]
) -> dict[str, int]:
    evidence_ids: set[str] = set()
    referenced_paths: set[str] = set()
    for index, row in enumerate(rows, start=2):
        evidence_id = (row.get("evidence_id") or "").strip()
        if not evidence_id or evidence_id in evidence_ids:
            raise PackageVerificationError(
                f"Missing or duplicate evidence_id at CSV line {index}: {evidence_id!r}"
            )
        evidence_ids.add(evidence_id)

        for field in ("contains_sensitive_data", "safe_for_submission"):
            if (row.get(field) or "").strip().casefold() not in {"true", "false"}:
                raise PackageVerificationError(
                    f"Invalid Boolean {field!r} at CSV line {index}"
                )
        if (
            row["contains_sensitive_data"].casefold() == "true"
            and row["safe_for_submission"].casefold() == "true"
        ):
            raise PackageVerificationError(
                f"Sensitive evidence cannot be submission-safe at CSV line {index}"
            )

        file_path = (row.get("file_path") or "").strip()
        validate_submission_path(file_path, 0)
        if file_path not in available_paths:
            raise PackageVerificationError(f"Evidence file does not exist: {file_path}")
        referenced_paths.add(file_path)
    return {
        "row_count": len(rows),
        "unique_evidence_ids": len(evidence_ids),
        "unique_evidence_paths": len(referenced_paths),
    }


def validate_evidence_manifest(
    repository_root: Path, manifest_path: Path
) -> dict[str, int]:
    """Validate the working-tree evidence manifest and referenced files."""
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EVIDENCE_MANIFEST_FIELDS:
            raise PackageVerificationError(
                "Evidence manifest header does not match the required schema."
            )
        rows = list(reader)
        if any(None in row for row in rows):
            raise PackageVerificationError(
                "Evidence manifest contains a row with extra columns."
            )
    evidence_root = repository_root / "docs" / "evidence"
    available = {
        path.relative_to(repository_root).as_posix()
        for path in evidence_root.rglob("*")
        if path.is_file() and path.resolve() != manifest_path.resolve()
    }
    referenced = {row["file_path"].strip() for row in rows}
    if available != referenced:
        missing = sorted(available - referenced)
        extra = sorted(referenced - available)
        raise PackageVerificationError(
            f"Evidence manifest/file inventory mismatch; unindexed={missing}, missing={extra}"
        )
    return _validate_evidence_rows(rows, available)


def validate_packaged_evidence_manifest(entries: Mapping[str, bytes]) -> dict[str, int]:
    path = "docs/evidence/EVIDENCE_MANIFEST.csv"
    if path not in entries:
        raise PackageSafetyError(
            f"Required evidence manifest is absent from Git tree: {path}"
        )
    with io.StringIO(entries[path].decode("utf-8-sig"), newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EVIDENCE_MANIFEST_FIELDS:
            raise PackageVerificationError(
                "Packaged evidence manifest header does not match the required schema."
            )
        rows = list(reader)
        if any(None in row for row in rows):
            raise PackageVerificationError(
                "Packaged evidence manifest contains extra columns."
            )
    available = {
        entry
        for entry in entries
        if entry.startswith("docs/evidence/") and entry != path
    }
    referenced = {row["file_path"].strip() for row in rows}
    if available != referenced:
        missing = sorted(available - referenced)
        extra = sorted(referenced - available)
        raise PackageVerificationError(
            f"Packaged evidence inventory mismatch; unindexed={missing}, missing={extra}"
        )
    return _validate_evidence_rows(rows, available)


def verify_package(
    package_path: Path, expected_commit: str | None = None
) -> dict[str, Any]:
    """Independently verify paths, manifest membership, sizes, and hashes."""
    try:
        with zipfile.ZipFile(package_path) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise PackageVerificationError("ZIP contains duplicate member names.")
            if names.count(MANIFEST_NAME) != 1:
                raise PackageVerificationError(
                    "ZIP must contain exactly one final submission manifest."
                )
            if any(info.is_dir() for info in infos):
                raise PackageVerificationError(
                    "ZIP contains unexpected directory entries."
                )
            if any(info.date_time != ZIP_TIMESTAMP for info in infos):
                raise PackageVerificationError(
                    "ZIP contains a non-deterministic timestamp."
                )

            try:
                manifest = json.loads(archive.read(MANIFEST_NAME))
            except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise PackageVerificationError(
                    "Package manifest is missing or invalid JSON."
                ) from exc
            if manifest.get("schema_version") != SCHEMA_VERSION:
                raise PackageVerificationError("Unexpected package manifest schema.")
            commit = manifest.get("source", {}).get("commit")
            if not re.fullmatch(r"[0-9a-f]{40}", str(commit)):
                raise PackageVerificationError(
                    "Manifest contains an invalid Git commit."
                )
            if expected_commit and commit != expected_commit:
                raise PackageVerificationError(
                    f"Package commit {commit} does not match expected {expected_commit}."
                )

            records = manifest.get("files")
            if not isinstance(records, list):
                raise PackageVerificationError("Manifest files must be a list.")
            expected_names: list[str] = []
            total_size = 0
            for record in records:
                if not isinstance(record, dict):
                    raise PackageVerificationError(
                        "Manifest file record is not an object."
                    )
                path = record.get("path")
                size = record.get("size_bytes")
                digest = record.get("sha256")
                if (
                    not isinstance(path, str)
                    or not isinstance(size, int)
                    or not isinstance(digest, str)
                ):
                    raise PackageVerificationError(
                        "Manifest file record has invalid field types."
                    )
                validate_submission_path(path, size)
                if not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise PackageVerificationError(f"Invalid SHA-256 for {path}")
                try:
                    data = archive.read(path)
                except KeyError as exc:
                    raise PackageVerificationError(
                        f"Manifest-listed file is missing: {path}"
                    ) from exc
                if len(data) != size or sha256_bytes(data) != digest:
                    raise PackageVerificationError(
                        f"Size or digest mismatch for {path}"
                    )
                expected_names.append(path)
                total_size += size

            if expected_names != sorted(expected_names) or len(expected_names) != len(
                set(expected_names)
            ):
                raise PackageVerificationError(
                    "Manifest file paths are not sorted and unique."
                )
            if set(names) != {MANIFEST_NAME, *expected_names}:
                raise PackageVerificationError(
                    "ZIP membership does not exactly match the manifest."
                )
            if manifest.get("file_count_excluding_manifest") != len(expected_names):
                raise PackageVerificationError("Manifest file count is incorrect.")
            if manifest.get("total_size_bytes_excluding_manifest") != total_size:
                raise PackageVerificationError(
                    "Manifest total byte count is incorrect."
                )

            packaged_entries = {path: archive.read(path) for path in expected_names}
            evidence = validate_packaged_evidence_manifest(packaged_entries)
    except zipfile.BadZipFile as exc:
        raise PackageVerificationError(
            "Submission artifact is not a valid ZIP file."
        ) from exc

    return {
        "package": str(package_path),
        "commit": commit,
        "file_count": len(expected_names),
        "total_size_bytes": total_size,
        "evidence_rows": evidence["row_count"],
        "sha256": sha256_bytes(package_path.read_bytes()),
    }


def _run_git(root: Path, *args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=text,
    )
    if result.returncode != 0:
        stderr = (
            result.stderr.strip()
            if text
            else result.stderr.decode("utf-8", errors="replace").strip()
        )
        raise PackageSafetyError(f"Git command failed: git {' '.join(args)}: {stderr}")
    return cast(str | bytes, result.stdout)


def _repository_name(root: Path) -> str:
    remote = str(_run_git(root, "config", "--get", "remote.origin.url")).strip()
    match = re.search(r"(?:github\.com[:/])([^/]+/[^/]+?)(?:\.git)?$", remote)
    if match:
        return match.group(1)
    return root.name


def read_exact_git_tree(root: Path, commit: str) -> dict[str, bytes]:
    archive_bytes = _run_git(root, "archive", "--format=tar", commit, text=False)
    assert isinstance(archive_bytes, bytes)
    entries: dict[str, bytes] = {}
    total_size = 0
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise PackageSafetyError(
                    f"Git tree contains an unsupported non-file entry: {member.name}"
                )
            extracted = archive.extractfile(member)
            if extracted is None:
                raise PackageSafetyError(
                    f"Unable to read Git tree entry: {member.name}"
                )
            data = extracted.read()
            validate_submission_path(member.name, len(data))
            total_size += len(data)
            if total_size > MAX_TOTAL_BYTES:
                raise PackageSafetyError(
                    f"Git tree exceeds {MAX_TOTAL_BYTES} safe package bytes."
                )
            entries[member.name] = data
    validate_packaged_evidence_manifest(entries)
    return entries


def build_from_git(
    root: Path, output_path: Path, commit: str = "HEAD", require_pushed: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    head = str(_run_git(root, "rev-parse", "HEAD")).strip()
    resolved = str(_run_git(root, "rev-parse", commit)).strip()
    if resolved != head:
        raise PackageSafetyError(
            "Submission packages must be built from the current exact HEAD."
        )
    status = str(
        _run_git(root, "status", "--porcelain", "--untracked-files=all")
    ).strip()
    if status:
        raise PackageSafetyError(
            "Submission package build requires a clean working tree."
        )
    if require_pushed:
        upstream = str(_run_git(root, "rev-parse", "@{upstream}")).strip()
        if upstream != head:
            raise PackageSafetyError(
                f"Local HEAD {head} does not match upstream {upstream}."
            )

    metadata = {
        "repository": _repository_name(root),
        "branch": str(_run_git(root, "branch", "--show-current")).strip(),
        "commit": head,
        "commit_time_utc": str(
            _run_git(root, "show", "-s", "--format=%cI", head)
        ).strip(),
    }
    entries = read_exact_git_tree(root, head)
    write_deterministic_package(output_path, entries, metadata)
    result = verify_package(output_path, expected_commit=head)
    checksum_path = output_path.with_name(f"{output_path.name}.sha256")
    checksum_path.write_text(
        f"{result['sha256']}  {output_path.name}\n", encoding="ascii"
    )
    result["checksum_file"] = str(checksum_path)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build", help="Build from a clean, pushed exact Git HEAD."
    )
    build.add_argument("--repository-root", type=Path, default=Path.cwd())
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--commit", default="HEAD")
    build.add_argument(
        "--allow-unpushed",
        action="store_true",
        help="Testing only; skip upstream equality check.",
    )

    verify = subparsers.add_parser("verify", help="Verify an existing submission ZIP.")
    verify.add_argument("package", type=Path)
    verify.add_argument("--expected-commit")

    evidence = subparsers.add_parser(
        "validate-evidence", help="Validate the working-tree evidence CSV."
    )
    evidence.add_argument("--repository-root", type=Path, default=Path.cwd())
    evidence.add_argument(
        "--manifest", type=Path, default=Path("docs/evidence/EVIDENCE_MANIFEST.csv")
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            result = build_from_git(
                args.repository_root,
                args.output,
                commit=args.commit,
                require_pushed=not args.allow_unpushed,
            )
        elif args.command == "verify":
            result = verify_package(args.package, expected_commit=args.expected_commit)
        else:
            root = args.repository_root.resolve()
            manifest = (
                args.manifest if args.manifest.is_absolute() else root / args.manifest
            )
            result = validate_evidence_manifest(root, manifest)
    except (PackageSafetyError, PackageVerificationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
