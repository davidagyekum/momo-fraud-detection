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
