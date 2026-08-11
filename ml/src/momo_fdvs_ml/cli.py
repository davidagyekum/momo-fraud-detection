"""Command-line interface for governed datasets and structured-model workflows."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from momo_fdvs_ml.acquisition import (
    AcquisitionError,
    acquisition_readiness_report,
    register_local_source,
)
from momo_fdvs_ml.colab import (
    ColabFoundationError,
    ColabPaths,
    colab_preflight_report,
    install_lock_contract,
    repository_state,
)
from momo_fdvs_ml.derivation import (
    DerivationError,
    derive_deduplicated_transactions,
)
from momo_fdvs_ml.execution import (
    FULL_TRAINING_ACKNOWLEDGEMENT,
    ExecutionGuardError,
    ExecutionProfile,
    require_training_execution,
)
from momo_fdvs_ml.governance import GovernanceError, governance_report
from momo_fdvs_ml.image_model import (
    ImageModelError,
    load_and_verify_image_artifact,
    train_and_package_image_model,
)
from momo_fdvs_ml.image_model import (
    runtime_fingerprint as image_runtime_fingerprint,
)
from momo_fdvs_ml.image_schema import ImageDatasetError, image_dataset_report
from momo_fdvs_ml.manifest import ManifestError, load_manifest, validate_manifest
from momo_fdvs_ml.notebooks import (
    NotebookPolicyError,
    require_clean_notebooks,
)
from momo_fdvs_ml.smoke import SmokeOutputs, run_smoke_flow
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

    validate_governance = subparsers.add_parser(
        "validate-governance",
        help="validate registry, schemas, fixtures, taxonomy and withdrawal controls",
    )
    validate_governance.add_argument("--root", type=Path, required=True)
    validate_governance.add_argument("--recorded-report", type=Path)

    acquisition_readiness = subparsers.add_parser(
        "acquisition-readiness",
        help="report source-specific governance blockers without opening source bytes",
    )
    acquisition_readiness.add_argument("--data-root", type=Path, required=True)
    acquisition_readiness.add_argument("--recorded-report", type=Path)

    register_dataset = subparsers.add_parser(
        "register-dataset",
        help="validate and register pre-authorized local bytes without network access",
    )
    register_dataset.add_argument("--data-root", type=Path, required=True)
    register_dataset.add_argument("--request", type=Path, required=True)
    register_dataset.add_argument("--allowed-source-root", type=Path, required=True)
    register_dataset.add_argument("--manifest-output", type=Path, required=True)
    register_dataset.add_argument("--profile-output", type=Path, required=True)

    derive_transactions = subparsers.add_parser(
        "derive-deduplicated-transactions",
        help="create a private first-occurrence exact-row derivative without splitting",
    )
    derive_transactions.add_argument("--request", type=Path, required=True)
    derive_transactions.add_argument("--allowed-source-root", type=Path, required=True)
    derive_transactions.add_argument("--allowed-output-root", type=Path, required=True)
    derive_transactions.add_argument("--output", type=Path, required=True)
    derive_transactions.add_argument("--manifest-output", type=Path, required=True)

    validate_notebooks = subparsers.add_parser(
        "validate-notebooks",
        help="validate standard Colab notebooks are clean, thin and restart-safe",
    )
    validate_notebooks.add_argument("--root", type=Path, required=True)
    validate_notebooks.add_argument("--recorded-report", type=Path)

    lock_report = subparsers.add_parser(
        "colab-lock-report", help="record exact shared Colab environment lock hashes"
    )
    lock_report.add_argument("--repository-root", type=Path, required=True)
    lock_report.add_argument("--recorded-report", type=Path)

    colab_preflight = subparsers.add_parser(
        "colab-preflight", help="validate clean runtime, checkout, locks and path layout"
    )
    colab_preflight.add_argument("--repository-root", type=Path, required=True)
    colab_preflight.add_argument("--notebook", required=True)
    colab_preflight.add_argument(
        "--profile", choices=[profile.value for profile in ExecutionProfile], required=True
    )
    colab_preflight.add_argument("--require-colab", action="store_true")

    smoke = subparsers.add_parser(
        "smoke-colab", help="run/resume the tiny non-promotable fictitious smoke flow"
    )
    smoke.add_argument("--repository-root", type=Path, required=True)
    smoke.add_argument("--vm-root", type=Path, required=True)
    smoke.add_argument("--drive-root", type=Path, required=True)
    smoke.add_argument("--notebook", required=True)
    smoke.add_argument("--run-id")
    smoke.add_argument(
        "--profile", choices=[profile.value for profile in ExecutionProfile], required=True
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
    train.add_argument(
        "--profile", choices=[profile.value for profile in ExecutionProfile], required=True
    )
    train.add_argument(
        "--acknowledge-full-training",
        metavar="TOKEN",
        help=f"required for FULL mode: {FULL_TRAINING_ACKNOWLEDGEMENT}",
    )

    verify_artifact = subparsers.add_parser(
        "verify-structured-artifact",
        help="hash and validate a trusted structured artifact without inference",
    )
    verify_artifact.add_argument("--artifact", type=Path, required=True)
    verify_artifact.add_argument("--sha256", required=True)
    verify_artifact.add_argument("--schema-hash", required=True)

    validate_image = subparsers.add_parser(
        "validate-image",
        help="validate P12 binary image data and preprocessing without model training",
    )
    validate_image.add_argument("--manifest", type=Path, required=True)
    validate_image.add_argument("--root", type=Path, required=True)
    validate_image.add_argument("--recorded-report", type=Path)

    train_image = subparsers.add_parser(
        "train-image",
        help="fit/evaluate/package P12; reportable execution is Google Colab only",
    )
    train_image.add_argument("--manifest", type=Path, required=True)
    train_image.add_argument("--root", type=Path, required=True)
    train_image.add_argument("--output-dir", type=Path, required=True)
    train_image.add_argument("--model-version", required=True)
    train_image.add_argument("--training-commit-sha", required=True)
    train_image.add_argument(
        "--profile", choices=[profile.value for profile in ExecutionProfile], required=True
    )
    train_image.add_argument(
        "--acknowledge-full-training",
        metavar="TOKEN",
        help=f"required for FULL mode: {FULL_TRAINING_ACKNOWLEDGEMENT}",
    )

    verify_image = subparsers.add_parser(
        "verify-image-artifact",
        help="hash, schema and shape-check one trusted Keras image artifact",
    )
    verify_image.add_argument("--artifact", type=Path, required=True)
    verify_image.add_argument("--sha256", required=True)
    verify_image.add_argument("--schema-hash", required=True)
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

        if args.command == "validate-governance":
            report = governance_report(args.root)
            if args.recorded_report is not None:
                recorded = json.loads(args.recorded_report.read_text(encoding="utf-8"))
                if recorded != report:
                    raise GovernanceError(
                        "recorded governance report does not match canonical data"
                    )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "acquisition-readiness":
            report = acquisition_readiness_report(args.data_root)
            if args.recorded_report is not None:
                recorded = json.loads(args.recorded_report.read_text(encoding="utf-8"))
                if recorded != report:
                    raise AcquisitionError(
                        "recorded acquisition readiness does not match canonical governance"
                    )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "register-dataset":
            registration_outputs = register_local_source(
                data_root=args.data_root,
                request_path=args.request,
                allowed_source_root=args.allowed_source_root,
                manifest_path=args.manifest_output,
                profile_path=args.profile_output,
            )
            print(
                json.dumps(
                    {
                        "dataset_id": registration_outputs.manifest["dataset_id"],
                        "status": registration_outputs.manifest["status"],
                        "manifest_path": str(registration_outputs.manifest_path),
                        "profile_path": str(registration_outputs.profile_path),
                        "source_sha256": registration_outputs.manifest["source_sha256"],
                        "network_acquisition_executed": False,
                        "promotable_for_training": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0 if registration_outputs.manifest["status"] == "registered" else 2

        if args.command == "derive-deduplicated-transactions":
            derivation_outputs = derive_deduplicated_transactions(
                request_path=args.request,
                allowed_source_root=args.allowed_source_root,
                allowed_output_root=args.allowed_output_root,
                output_path=args.output,
                manifest_path=args.manifest_output,
            )
            print(
                json.dumps(
                    {
                        "dataset_id": derivation_outputs.manifest["dataset_id"],
                        "derived_dataset_version": derivation_outputs.manifest[
                            "derived_dataset_version"
                        ],
                        "manifest_path": str(derivation_outputs.manifest_path),
                        "output_sha256": derivation_outputs.manifest["output_sha256"],
                        "output_row_count": derivation_outputs.manifest["output_row_count"],
                        "removed_duplicate_row_count": derivation_outputs.manifest[
                            "removed_duplicate_row_count"
                        ],
                        "source_bytes_modified": False,
                        "splits_created": False,
                        "training_executed": False,
                        "promotable_for_training": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "validate-notebooks":
            report = require_clean_notebooks(args.root)
            if args.recorded_report is not None:
                recorded = json.loads(args.recorded_report.read_text(encoding="utf-8"))
                if recorded != report:
                    raise NotebookPolicyError(
                        "recorded notebook report does not match canonical notebooks"
                    )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "colab-lock-report":
            report = install_lock_contract(args.repository_root)
            if args.recorded_report is not None:
                recorded = json.loads(args.recorded_report.read_text(encoding="utf-8"))
                if recorded != report:
                    raise ColabFoundationError(
                        "recorded Colab lock report does not match repository locks"
                    )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "colab-preflight":
            report = colab_preflight_report(
                args.repository_root,
                paths=ColabPaths.from_environment(),
                profile=ExecutionProfile(args.profile),
                notebook=args.notebook,
                require_colab=args.require_colab,
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "smoke-colab":
            if ExecutionProfile(args.profile) is not ExecutionProfile.SMOKE:
                raise ColabFoundationError("smoke-colab requires --profile smoke")
            smoke_outputs: SmokeOutputs = run_smoke_flow(
                repository_root=args.repository_root,
                vm_root=args.vm_root,
                drive_root=args.drive_root,
                git_state=repository_state(args.repository_root),
                notebook=args.notebook,
                run_id=args.run_id,
            )
            print(
                json.dumps(
                    {
                        "run_id": smoke_outputs.run_id,
                        "manifest_path": str(smoke_outputs.manifest_path),
                        "report_path": str(smoke_outputs.report_path),
                        "bundle_path": str(smoke_outputs.bundle_path),
                        "prediction_digest": smoke_outputs.prediction_digest,
                        "resumed": smoke_outputs.resumed,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

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
            require_training_execution(
                ExecutionProfile(args.profile),
                acknowledgement=args.acknowledge_full_training,
            )
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

        if args.command == "validate-image":
            report = image_dataset_report(args.manifest, root=args.root)
            if args.recorded_report is not None:
                recorded = json.loads(args.recorded_report.read_text(encoding="utf-8"))
                if recorded != report:
                    raise ImageDatasetError(
                        "recorded image dataset report does not match canonical data"
                    )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "train-image":
            require_training_execution(
                ExecutionProfile(args.profile),
                acknowledgement=args.acknowledge_full_training,
            )
            image_outputs = train_and_package_image_model(
                manifest_path=args.manifest,
                dataset_root=args.root,
                output_dir=args.output_dir,
                model_version=args.model_version,
                training_commit_sha=args.training_commit_sha,
            )
            summary = {
                "artifact_path": str(image_outputs.artifact_path),
                "artifact_sha256": image_outputs.artifact_sha256,
                "report_path": str(image_outputs.report_path),
                "model_card_path": str(image_outputs.model_card_path),
                "registry_payload_path": str(image_outputs.registry_payload_path),
                "confusion_matrix_path": str(image_outputs.confusion_matrix_path),
                "acceptance_passed": image_outputs.report["acceptance_passed"],
                "runtime": image_runtime_fingerprint(),
            }
            print(json.dumps(summary, indent=2, sort_keys=True))
            return 0 if image_outputs.report["acceptance_passed"] else 2

        if args.command == "verify-image-artifact":
            model = load_and_verify_image_artifact(
                args.artifact,
                expected_sha256=args.sha256,
                expected_schema_hash=args.schema_hash,
            )
            print(
                json.dumps(
                    {
                        "artifact_verified": True,
                        "input_shape": list(model.input_shape),
                        "output_shape": list(model.output_shape),
                        "preprocessing_schema_hash": args.schema_hash,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

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
    except (
        AcquisitionError,
        ColabFoundationError,
        DerivationError,
        ExecutionGuardError,
        GovernanceError,
        ImageDatasetError,
        ImageModelError,
        ManifestError,
        NotebookPolicyError,
        StructuredDatasetError,
        StructuredModelError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
