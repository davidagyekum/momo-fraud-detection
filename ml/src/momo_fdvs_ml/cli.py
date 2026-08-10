"""Command-line interface for governed dataset generation and validation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from momo_fdvs_ml.manifest import ManifestError, load_manifest, validate_manifest
from momo_fdvs_ml.synthetic import (
    DEFAULT_SEED,
    generate_controlled_dataset,
    verify_recorded_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser(
        "generate", help="generate generic controlled research fixtures"
    )
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    generate.add_argument("--groups", type=int, default=6)

    validate = subparsers.add_parser(
        "validate", help="validate manifest, files, privacy and split isolation"
    )
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--root", type=Path, required=True)
    validate.add_argument(
        "--check-recorded-report",
        action="store_true",
        help="also compare dataset_report.json to canonical hashes",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "generate":
            generated = generate_controlled_dataset(
                args.output, seed=args.seed, group_count=args.groups
            )
            print(json.dumps(generated.validation.as_dict(), indent=2, sort_keys=True))
            return 0

        manifest = load_manifest(args.manifest)
        validation = validate_manifest(manifest, root=args.root)
        recorded_errors = (
            verify_recorded_report(args.root, manifest) if args.check_recorded_report else ()
        )
        payload = validation.as_dict()
        payload["recorded_report_errors"] = list(recorded_errors)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if validation.is_valid and not recorded_errors else 1
    except ManifestError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
