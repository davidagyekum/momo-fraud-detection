"""Tests for repository secret-scanner code syntax handling."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

check_secrets = importlib.import_module("check_secrets")


def test_typescript_types_and_schema_identifiers_are_not_secrets(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(check_secrets, "REPO_ROOT", tmp_path)
    source = tmp_path / "schema.ts"
    source.write_text(
        "type Value = { must_change_password: boolean; };\n"
        "const password = z.string();\n"
        "const PasswordField = forwardRef<HTMLInputElement, Props>();\n"
        "const item = { new_password: password };\n",
        encoding="utf-8",
    )

    assert check_secrets.inspect_file(source) == []


def test_controlled_test_tokens_are_explicit_placeholders(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(check_secrets, "REPO_ROOT", tmp_path)
    source = tmp_path / "fixture.ts"
    source.write_text(
        'const ACCESS_TOKEN = "controlled-test-only-access-token";\n',
        encoding="utf-8",
    )

    assert check_secrets.inspect_file(source) == []


def test_typescript_hard_coded_token_remains_a_finding(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(check_secrets, "REPO_ROOT", tmp_path)
    source = tmp_path / "unsafe.ts"
    source.write_text(
        'const ACCESS_TOKEN = "live-token-value-abcdef1234567890";\n',
        encoding="utf-8",
    )

    findings = check_secrets.inspect_file(source)

    assert [finding.reason for finding in findings] == [
        "possible non-placeholder secret assigned to ACCESS_TOKEN"
    ]


def test_private_ml_dataset_paths_remain_prohibited(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(check_secrets, "REPO_ROOT", tmp_path)
    source = tmp_path / "ml" / "data" / "private" / "receipt.csv"
    source.parent.mkdir(parents=True)
    source.write_text("private research row\n", encoding="utf-8")

    findings = check_secrets.inspect_file(source)

    assert [finding.reason for finding in findings] == [
        "path is reserved for private research data"
    ]


def test_pii_filenames_are_rejected_but_fictitious_markers_are_allowed(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(check_secrets, "REPO_ROOT", tmp_path)
    unsafe_phone = tmp_path / "receipt-0241234567.png"
    unsafe_email = tmp_path / "receipt-owner@example.test.png"
    unsafe_name = tmp_path / "participant-kwame-mensah.pdf"
    safe_fixture = tmp_path / "participant-demo-fixture.pdf"
    for path in (unsafe_phone, unsafe_email, unsafe_name, safe_fixture):
        path.write_text("fixture", encoding="utf-8")

    assert [finding.reason for finding in check_secrets.inspect_file(unsafe_phone)] == [
        "possible phone number in filename"
    ]
    assert [finding.reason for finding in check_secrets.inspect_file(unsafe_email)] == [
        "possible email address in filename"
    ]
    assert [finding.reason for finding in check_secrets.inspect_file(unsafe_name)] == [
        "possible personal name in filename"
    ]
    assert check_secrets.inspect_file(safe_fixture) == []


def test_large_file_limit_is_enforced_without_committing_a_large_fixture(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(check_secrets, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(check_secrets, "MAX_REPOSITORY_FILE_BYTES", 16)
    oversized = tmp_path / "oversized.txt"
    oversized.write_text("x" * 17, encoding="utf-8")

    assert [finding.reason for finding in check_secrets.inspect_file(oversized)] == [
        "file is larger than 16 bytes"
    ]
