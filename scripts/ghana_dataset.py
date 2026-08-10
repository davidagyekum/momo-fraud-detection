#!/usr/bin/env python3
"""Operate the private Ghana MoMo fraud-message dataset workspace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_ROOT = REPO_ROOT / "ml"
if str(ML_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ML_ROOT / "src"))

from momo_fdvs_ml.ghana_dataset import (  # noqa: E402
    GhanaDatasetError,
    build_canonical_manifest,
    init_workspace,
    redact_image,
    validate_dataset,
    write_report,
)


DEFAULT_ROOT = ML_ROOT / "data" / "authorized" / "ghana_momo_fraud"


def _root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="private local Ghana corpus workspace (default: ml/data/authorized/ghana_momo_fraud)",
    )


def _box(value: str) -> tuple[int, int, int, int]:
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be x1,y1,x2,y2")
    try:
        values = tuple(int(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("box coordinates must be integers") from exc
    return values  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init", help="create the ignored workspace and CSV templates"
    )
    _root_argument(init_parser)

    validate_parser = subparsers.add_parser(
        "validate", help="validate redacted images and metadata"
    )
    _root_argument(validate_parser)
    validate_parser.add_argument("--minimum-ready", type=int, default=0)
    validate_parser.add_argument("--require-ready", action="store_true")
    validate_parser.add_argument("--report", type=Path)

    manifest_parser = subparsers.add_parser(
        "build-manifest", help="build the repository-compatible private manifest"
    )
    _root_argument(manifest_parser)
    manifest_parser.add_argument("--output", type=Path)

    redact_parser = subparsers.add_parser(
        "redact", help="apply explicit human-reviewed masks and strip EXIF"
    )
    redact_parser.add_argument("--input", type=Path, required=True)
    redact_parser.add_argument("--output", type=Path, required=True)
    redact_parser.add_argument("--box", type=_box, action="append", required=True)

    args = parser.parse_args()
    try:
        if args.command == "init":
            directories = init_workspace(args.root)
            print(
                json.dumps(
                    {
                        "status": "READY",
                        "root": str(args.root),
                        "directories": [str(item) for item in directories],
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "validate":
            report = validate_dataset(
                args.root,
                minimum_ready=args.minimum_ready,
                require_ready=args.require_ready,
            )
            report_path = args.report or args.root / "audits" / "qa_report.json"
            write_report(report, report_path)
            print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
            return 0 if report.status == "PASS" else 2
        if args.command == "build-manifest":
            output = args.output or args.root / "metadata" / "manifest.csv"
            path = build_canonical_manifest(args.root, output)
            print(json.dumps({"status": "PASS", "manifest": str(path)}, indent=2))
            return 0
        if args.command == "redact":
            redact_image(args.input, args.output, args.box)
            print(json.dumps({"status": "PASS", "output": str(args.output)}, indent=2))
            return 0
    except GhanaDatasetError as exc:
        print(
            json.dumps({"status": "ERROR", "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
