#!/usr/bin/env python3
"""Verify the running four-service local PR19 release."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from _common import REPO_ROOT, display_command

EXPECTED_SERVICES = {"db", "api", "admin", "mobile"}
EXPECTED_MIGRATION = "20260816_0005"


def capture(
    command: list[str], cwd: Path = REPO_ROOT
) -> subprocess.CompletedProcess[str]:
    print(f"$ {display_command(command)}", flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def probe(url: str) -> tuple[int, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return (
                response.status,
                response.headers.get_content_type(),
                response.read().decode("utf-8", errors="replace"),
            )
    except (OSError, urllib.error.URLError) as error:
        raise RuntimeError(f"release probe failed for {url}: {error}") from error


def main() -> int:
    compose = shutil.which("docker-compose")
    if compose is None:
        print("Release verification: FAIL (docker-compose is unavailable)")
        return 1
    project = os.getenv("MOMO_RELEASE_PROJECT", "momo-fdvs")
    prefix = [compose, "-p", project]

    config = capture([*prefix, "config", "--quiet"])
    if config.returncode != 0:
        print(config.stderr)
        print("Release verification: FAIL (Compose configuration is invalid)")
        return 1
    running = capture([*prefix, "ps", "--status", "running", "--services"])
    services = {line.strip() for line in running.stdout.splitlines() if line.strip()}
    if running.returncode != 0 or services != EXPECTED_SERVICES:
        print(running.stdout, running.stderr)
        print(f"Release verification: FAIL (running services: {sorted(services)})")
        return 1

    migration = capture(
        [
            *prefix,
            "exec",
            "-T",
            "api",
            "flask",
            "--app",
            "momo_fdvs.wsgi:app",
            "db",
            "current",
        ]
    )
    if migration.returncode != 0 or EXPECTED_MIGRATION not in migration.stdout:
        print(migration.stdout, migration.stderr)
        print("Release verification: FAIL (database is not at migration head)")
        return 1

    api_url = os.getenv("MOMO_RELEASE_API_URL", "http://127.0.0.1:8000")
    admin_url = os.getenv("MOMO_RELEASE_ADMIN_URL", "http://127.0.0.1:5173")
    mobile_url = os.getenv("MOMO_RELEASE_MOBILE_URL", "http://127.0.0.1:8081")
    health_status, _, _ = probe(f"{api_url}/api/v1/health")
    ready_status, _, ready_body = probe(f"{api_url}/api/v1/ready")
    readiness = json.loads(ready_body)["data"]
    admin_status, admin_type, _ = probe(f"{admin_url}/login")
    mobile_status, mobile_type, _ = probe(f"{mobile_url}/login")
    valid = (
        health_status == 200
        and ready_status == 200
        and readiness["ready"] is True
        and readiness["components"]["database"]["status"] == "ready"
        and readiness["components"]["storage"]["status"] == "ready"
        and readiness["components"]["tesseract"]["status"] == "ready"
        and admin_status == 200
        and admin_type == "text/html"
        and mobile_status == 200
        and mobile_type == "text/html"
    )
    if not valid:
        print("Release verification: FAIL (one or more readiness assertions failed)")
        return 1
    print(
        "Release verification: PASS "
        f"(services={','.join(sorted(services))}; migration={EXPECTED_MIGRATION}; "
        f"full_analysis_available={readiness['full_analysis_available']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
