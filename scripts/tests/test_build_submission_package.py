from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import build_submission_package as package


class SubmissionPathPolicyTests(unittest.TestCase):
    def test_allows_repository_safe_paths(self) -> None:
        package.validate_submission_path("README.md", 100)
        package.validate_submission_path(".env.example", 100)
        package.validate_submission_path("docs/evidence/mobile/safe.png", 100)
        package.validate_submission_path("ml/data/controlled/fixture.png", 100)

    def test_rejects_traversal_absolute_and_windows_paths(self) -> None:
        for path in ("../secret.txt", "/absolute.txt", "C:/secret.txt", "a\\b.txt"):
            with self.subTest(path=path), self.assertRaises(package.PackageSafetyError):
                package.validate_submission_path(path, 1)

    def test_rejects_private_secret_generated_and_model_paths(self) -> None:
        paths = (
            ".env",
            ".env.local",
            "private-storage/receipt.png",
            "data/private/receipt.csv",
            "ml/data/authorised/source.csv",
            "node_modules/library/index.js",
            "output/report.txt",
            ".playwright-cli/state.json",
            "models/image.keras",
            "archive/freeze.zip",
            "keys/demo.pem",
        )
        for path in paths:
            with self.subTest(path=path), self.assertRaises(package.PackageSafetyError):
                package.validate_submission_path(path, 1)

    def test_rejects_an_oversized_file(self) -> None:
        with self.assertRaises(package.PackageSafetyError):
            package.validate_submission_path(
                "docs/report.md", package.MAX_FILE_BYTES + 1
            )


class DeterministicPackageTests(unittest.TestCase):
    def test_build_is_deterministic_and_verifies(self) -> None:
        entries = {
            "README.md": b"# Safe repository\n",
            ".env.example": b"DEMO_VALUE=CHANGE_ME\n",
            "docs/evidence/safe.md": b"safe evidence\n",
            "docs/evidence/EVIDENCE_MANIFEST.csv": (
                b"evidence_id,requirement_id,chapter_section,title,file_path,type,SHA,environment,"
                b"contains_sensitive_data,safe_for_submission,notes\n"
                b"SAFE-001,FR-SAFE-001,4.1,Safe evidence,docs/evidence/safe.md,report,"
                + (b"c" * 40)
                + b",Local synthetic fixture,false,true,No private data.\n"
            ),
        }
        metadata = {
            "repository": "example/momo-fdvs",
            "branch": "codex/freeze",
            "commit": "a" * 40,
            "commit_time_utc": "2026-08-21T00:00:00+00:00",
        }
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.zip"
            second = Path(directory) / "second.zip"
            package.write_deterministic_package(first, entries, metadata)
            package.write_deterministic_package(second, entries, metadata)

            self.assertEqual(
                hashlib.sha256(first.read_bytes()).digest(),
                hashlib.sha256(second.read_bytes()).digest(),
            )
            result = package.verify_package(first, expected_commit="a" * 40)
            self.assertEqual(result["file_count"], 4)
            self.assertEqual(result["commit"], "a" * 40)

            with zipfile.ZipFile(first) as archive:
                self.assertEqual(
                    archive.namelist(),
                    [
                        package.MANIFEST_NAME,
                        ".env.example",
                        "README.md",
                        "docs/evidence/EVIDENCE_MANIFEST.csv",
                        "docs/evidence/safe.md",
                    ],
                )
                self.assertTrue(
                    all(
                        info.date_time == package.ZIP_TIMESTAMP
                        for info in archive.infolist()
                    )
                )
                manifest = json.loads(archive.read(package.MANIFEST_NAME))
                self.assertEqual(manifest["files"][0]["path"], ".env.example")

    def test_verification_detects_changed_file_bytes(self) -> None:
        entries = {
            "README.md": b"safe\n",
            "docs/evidence/safe.md": b"safe evidence\n",
            "docs/evidence/EVIDENCE_MANIFEST.csv": (
                b"evidence_id,requirement_id,chapter_section,title,file_path,type,SHA,environment,"
                b"contains_sensitive_data,safe_for_submission,notes\n"
                b"SAFE-001,FR-SAFE-001,4.1,Safe evidence,docs/evidence/safe.md,report,"
                + (b"c" * 40)
                + b",Local synthetic fixture,false,true,No private data.\n"
            ),
        }
        metadata = {
            "repository": "example/momo-fdvs",
            "branch": "codex/freeze",
            "commit": "b" * 40,
            "commit_time_utc": "2026-08-21T00:00:00+00:00",
        }
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "original.zip"
            tampered = Path(directory) / "tampered.zip"
            package.write_deterministic_package(original, entries, metadata)
            with (
                zipfile.ZipFile(original) as source,
                zipfile.ZipFile(tampered, "w") as target,
            ):
                for info in source.infolist():
                    data = source.read(info.filename)
                    if info.filename == "README.md":
                        data = b"changed\n"
                    target.writestr(info, data)

            with self.assertRaises(package.PackageVerificationError):
                package.verify_package(tampered)


class EvidenceManifestTests(unittest.TestCase):
    def test_validates_evidence_manifest_shape_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / "docs" / "evidence" / "safe.md"
            evidence.parent.mkdir(parents=True)
            evidence.write_text("safe evidence\n", encoding="utf-8")
            manifest = root / "docs" / "evidence" / "EVIDENCE_MANIFEST.csv"
            with manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=package.EVIDENCE_MANIFEST_FIELDS
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "evidence_id": "SAFE-001",
                        "requirement_id": "FR-SAFE-001",
                        "chapter_section": "4.1",
                        "title": "Safe evidence",
                        "file_path": "docs/evidence/safe.md",
                        "type": "report",
                        "SHA": "c" * 40,
                        "environment": "Local synthetic fixture",
                        "contains_sensitive_data": "false",
                        "safe_for_submission": "true",
                        "notes": "No private data.",
                    }
                )

            result = package.validate_evidence_manifest(root, manifest)
            self.assertEqual(result["row_count"], 1)

    def test_rejects_duplicate_ids_and_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.csv"
            with manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=package.EVIDENCE_MANIFEST_FIELDS
                )
                writer.writeheader()
                row = {
                    "evidence_id": "DUPLICATE",
                    "requirement_id": "FR-SAFE-001",
                    "chapter_section": "4.1",
                    "title": "Missing evidence",
                    "file_path": "docs/evidence/missing.md",
                    "type": "report",
                    "SHA": "d" * 40,
                    "environment": "Local",
                    "contains_sensitive_data": "false",
                    "safe_for_submission": "true",
                    "notes": "Missing on purpose.",
                }
                writer.writerow(row)
                writer.writerow(row)

            with self.assertRaises(package.PackageVerificationError):
                package.validate_evidence_manifest(root, manifest)

    def test_rejects_an_unindexed_evidence_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_root = root / "docs" / "evidence"
            evidence_root.mkdir(parents=True)
            (evidence_root / "indexed.md").write_text("indexed\n", encoding="utf-8")
            (evidence_root / "forgotten.md").write_text("forgotten\n", encoding="utf-8")
            manifest = evidence_root / "EVIDENCE_MANIFEST.csv"
            with manifest.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=package.EVIDENCE_MANIFEST_FIELDS
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "evidence_id": "INDEXED",
                        "requirement_id": "FR-SAFE-001",
                        "chapter_section": "4.1",
                        "title": "Indexed evidence",
                        "file_path": "docs/evidence/indexed.md",
                        "type": "report",
                        "SHA": "e" * 40,
                        "environment": "Local",
                        "contains_sensitive_data": "false",
                        "safe_for_submission": "true",
                        "notes": "One file is intentionally omitted.",
                    }
                )

            with self.assertRaises(package.PackageVerificationError):
                package.validate_evidence_manifest(root, manifest)


if __name__ == "__main__":
    unittest.main()
