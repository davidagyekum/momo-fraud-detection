#!/usr/bin/env python3
"""Run the PR19 security acceptance gate without silently skipping scenarios."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from _common import REPO_ROOT, display_command

API_ROOT = REPO_ROOT / "services" / "api"


def run(label: str, command: list[str], cwd: Path = REPO_ROOT) -> bool:
    print(f"\n== {label} ==", flush=True)
    print(f"$ {display_command(command)}", flush=True)
    result = subprocess.run(command, cwd=cwd, check=False)
    print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}")
    return result.returncode == 0


def run_backend_security() -> bool:
    if not os.environ.get("TEST_DATABASE_URL"):
        print("Security verification: FAIL (TEST_DATABASE_URL is required)")
        return False
    with tempfile.TemporaryDirectory(prefix="momo-security-") as temporary:
        report = Path(temporary) / "pytest.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "tests/security",
            "tests/integration/test_casework_api.py",
            "tests/integration/test_operations_api.py",
            "tests/integration/test_receipt_upload.py",
            "tests/integration/test_transaction_history_api.py",
            "tests/unit/test_config.py",
            "tests/unit/test_logging.py",
            "--no-cov",
            "-q",
            f"--junitxml={report}",
        ]
        if not run("backend security scenarios", command, API_ROOT):
            return False
        root = ET.parse(report).getroot()
        skipped = sum(
            int(suite.get("skipped", "0")) for suite in root.iter("testsuite")
        )
        if skipped:
            print(
                f"Security verification: FAIL ({skipped} required scenario(s) skipped)"
            )
            return False
    return True


def main() -> int:
    success = run_backend_security()
    success &= run(
        "admin browser-security policy",
        [sys.executable, "scripts/check_admin_security_policy.py"],
    )
    success &= run(
        "mobile token-storage policy",
        [sys.executable, "scripts/check_mobile_token_storage.py"],
    )
    success &= run(
        "secret and prohibited-artifact scan",
        [sys.executable, "scripts/check_secrets.py"],
    )
    print(f"\nSecurity verification: {'PASS' if success else 'FAIL'}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
