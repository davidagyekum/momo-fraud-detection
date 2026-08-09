#!/usr/bin/env python3
"""Reject insecure token persistence in the Expo mobile source tree."""

from __future__ import annotations

from pathlib import Path

from _common import REPO_ROOT

MOBILE_SOURCE = REPO_ROOT / "apps" / "mobile" / "src"
TOKEN_VAULT = MOBILE_SOURCE / "lib" / "token-vault.ts"
FORBIDDEN_STORAGE = ("AsyncStorage", "localStorage", "sessionStorage")


def main() -> int:
    violations: list[str] = []
    for path in MOBILE_SOURCE.rglob("*"):
        if path.suffix not in {".ts", ".tsx"} or "__tests__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for prohibited in FORBIDDEN_STORAGE:
            if prohibited in text:
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}: prohibited {prohibited}"
                )
        if "SecureStore." in text and path != TOKEN_VAULT:
            violations.append(
                f"{path.relative_to(REPO_ROOT)}: SecureStore access must be isolated in token-vault.ts"
            )

    vault_text = TOKEN_VAULT.read_text(encoding="utf-8")
    if "access_token" in vault_text.lower() or "accessToken" in vault_text:
        violations.append(
            "apps/mobile/src/lib/token-vault.ts: access tokens must remain memory-only"
        )
    if "refresh" not in vault_text.lower() or "SecureStore." not in vault_text:
        violations.append(
            "apps/mobile/src/lib/token-vault.ts: expected secure refresh-token storage is missing"
        )

    if violations:
        print("Mobile token-storage policy: FAIL")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Mobile token-storage policy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
