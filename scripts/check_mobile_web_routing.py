#!/usr/bin/env python3
"""Verify the Expo web build uses one hydration-safe SPA shell."""

from __future__ import annotations

import json

from _common import REPO_ROOT


APP_CONFIG = REPO_ROOT / "apps" / "mobile" / "app.json"
NGINX_CONFIG = REPO_ROOT / "apps" / "mobile" / "nginx.conf"


def main() -> int:
    app_config = json.loads(APP_CONFIG.read_text(encoding="utf-8"))
    output_mode = app_config.get("expo", {}).get("web", {}).get("output")
    nginx_config = NGINX_CONFIG.read_text(encoding="utf-8")
    failures: list[str] = []
    if output_mode != "single":
        failures.append("Expo web.output must be 'single'")
    if "try_files $uri $uri.html $uri/ /index.html;" not in nginx_config:
        failures.append("nginx must fall back to the single Expo index shell")
    if "location ~ ^/" in nginx_config:
        failures.append("nginx must not substitute prerendered dynamic-route templates")
    if failures:
        print("Mobile web-routing policy: FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Mobile web-routing policy: PASS (single hydration-safe SPA shell)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
