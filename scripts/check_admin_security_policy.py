#!/usr/bin/env python3
"""Reject unsafe browser persistence and HTML injection in the admin portal."""

from __future__ import annotations

from pathlib import Path

from _common import REPO_ROOT

ADMIN_SOURCE = REPO_ROOT / "apps" / "admin" / "src"
FORBIDDEN_APIS = (
    "localStorage",
    "sessionStorage",
    "indexedDB",
    "dangerouslySetInnerHTML",
)


def find_violations(source_root: Path = ADMIN_SOURCE) -> list[str]:
    violations: list[str] = []
    for path in source_root.rglob("*"):
        if path.suffix not in {".ts", ".tsx"} or path.name.endswith(
            (".test.ts", ".test.tsx")
        ):
            continue
        source = path.read_text(encoding="utf-8")
        for prohibited in FORBIDDEN_APIS:
            if prohibited in source:
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}: prohibited {prohibited}"
                )
    return violations


def main() -> int:
    if not ADMIN_SOURCE.is_dir():
        print("Admin security policy: FAIL (admin source tree is missing)")
        return 1
    violations = find_violations()
    if violations:
        print("Admin security policy: FAIL")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Admin security policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
