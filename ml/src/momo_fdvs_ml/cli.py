"""Command-line interface for governed datasets and structured-model workflows."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from momo_fdvs_ml.manifest import ManifestError, load_manifest, validate_manifest
from momo_fdvs_ml.structured_dataset import (
    STRUCTURED_DATASET_SEED,
    StructuredDatasetError,
    load_structured_dataset,
    structured_dataset_report,
    write_structured_dataset,
)
from momo_fdvs_ml.structured_model import (
    StructuredModelError,
    load_and_verify_artifact,
    runtime_fingerprint,
    train_and_package,
)
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

    structured_data = subparsers.add_parser(
        "generate-structured",
        help="derive controlled structured evidence rows from governed P10 groups",
    )
    structured_data.add_argument("--source-manifest", type=Path, required=True)
    structured_data.add_argument("--output", type=Path, required=True)
    structured_data.add_argument("--seed", type=int, default=STRUCTURED_DATASET_SEED)

    validate_structured = subparsers.add_parser(
        "validate-structured",
        help="validate governed structured rows, split isolation and recorded hashes",
    )
    validate_structured.add_argument("--dataset", type=Path, required=True)
    validate_structured.add_argument("--source-manifest", type=Path, required=True)
    validate_structured.add_argument("--recorded-report", type=Path)

    train = subparsers.add_parser(
        "train-structured",
        help="fit/evaluate/package P11; reportable execution is Google Colab only",
    )
    train.add_argument("--dataset", type=Path, required=True)
    train.add_argument("--source-manifest", type=Path, required=True)
    train.add_argument("--output-dir", type=Path, required=True)
    train.add_argument("--model-version", required=True)
    train.add_argument("--training-commit-sha", required=True)

    verify_artifact = subparsers.add_parser(
        "verify-structured-artifact",
        help="hash and validate a trusted structured artifact without inference",
    )
    verify_artifact.add_argument("--artifact", type=Path, required=True)
    verify_artifact.add_argument("--sha256", required=True)
    verify_artifact.add_argument("--schema-hash", required=True)
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

        if args.command == "validate":
            manifest = load_manifest(args.manifest)
            validation = validate_manifest(manifest, root=args.root)
            recorded_errors = (
                verify_recorded_report(args.root, manifest) if args.check_recorded_report else ()
            )
            payload = validation.as_dict()
            payload["recorded_report_errors"] = list(recorded_errors)
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if validation.is_valid and not recorded_errors else 1

        if args.command == "generate-structured":
            dataset = write_structured_dataset(
                source_manifest_path=args.source_manifest,
                output_path=args.output,
                seed=args.seed,
            )
            report = structured_dataset_report(dataset)
            report_path = args.output.with_name("structured_dataset_report.json")
            report_path.write_text(
                json.dumps(report, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "validate-structured":
            dataset = load_structured_dataset(
                path=args.dataset, source_manifest_path=args.source_manifest
            )
            report = structured_dataset_report(dataset)
            if args.recorded_report is not None:
                recorded = json.loads(args.recorded_report.read_text(encoding="utf-8"))
                if recorded != report:
                    raise StructuredDatasetError(
                        "recorded structured dataset report does not match canonical data"
                    )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "train-structured":
            dataset = load_structured_dataset(
                path=args.dataset, source_manifest_path=args.source_manifest
            )
            outputs = train_and_package(
                dataset=dataset,
                output_dir=args.output_dir,
                model_version=args.model_version,
                training_commit_sha=args.training_commit_sha,
            )
            summary = {
                "artifact_path": str(outputs.artifact_path),
                "artifact_sha256": outputs.artifact_sha256,
                "report_path": str(outputs.report_path),
                "model_card_path": str(outputs.model_card_path),
                "registry_payload_path": str(outputs.registry_payload_path),
                "confusion_matrix_path": str(outputs.confusion_matrix_path),
                "acceptance_passed": outputs.report["acceptance_passed"],
                "runtime": runtime_fingerprint(),
            }
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if outputs.report["acceptance_passed"] else 2

        bundle = load_and_verify_artifact(
            args.artifact,
            expected_sha256=args.sha256,
            expected_schema_hash=args.schema_hash,
        )
        print(
            json.dumps(
                {
                    "artifact_verified": True,
                    "model_name": bundle["model_name"],
                    "model_version": bundle["model_version"],
                    "feature_schema_hash": bundle["feature_schema_hash"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (ManifestError, StructuredDatasetError, StructuredModelError) as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
