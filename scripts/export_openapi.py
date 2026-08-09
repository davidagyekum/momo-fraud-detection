#!/usr/bin/env python3
"""Export the OpenAPI document generated from Flask-Smorest schemas."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from momo_fdvs import create_app
from momo_fdvs.extensions import api

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = REPO_ROOT / "packages" / "api-client" / "openapi.json"


def generated_contract() -> str:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://momo_fdvs:momo_fdvs_local_only@localhost:5432/momo_fdvs",
    )
    app = create_app("testing")
    with app.app_context():
        document = api.spec.to_dict()
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail when the committed snapshot differs"
    )
    args = parser.parse_args()
    generated = generated_contract()
    if args.check:
        if not SNAPSHOT.is_file():
            print(f"OpenAPI snapshot is missing: {SNAPSHOT}")
            return 1
        if SNAPSHOT.read_text(encoding="utf-8") != generated:
            print("OpenAPI snapshot is stale; run scripts/export_openapi.py")
            return 1
        print("OpenAPI contract matches the generated schemas")
        return 0
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(generated, encoding="utf-8", newline="\n")
    print(f"Wrote {SNAPSHOT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
