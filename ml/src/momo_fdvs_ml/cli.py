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
from momo_fdvs_ml.ghana_pipeline import (
    OWNER_CONSENT_ACKNOWLEDGEMENT,
    GhanaPrivateError,
    advance_review,
    apply_withdrawals,
    attest_online_candidate_permission,
    freeze_group_splits,
    index_imazing_messages,
    ingest_private_screenshots,
    initialize_owner_consent,
    quarantine_online_candidate,
    review_online_candidate,
)
from momo_fdvs_ml.governance import (
    GovernanceError,
    governance_report,
    load_withdrawal_ledger,
)
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
from momo_fdvs_ml.transaction_etl import (
    TransactionBuildSpec,
    build_transaction_parquet_dataset,
)
from momo_fdvs_ml.transaction_model import (
    TransactionModelError,
    load_and_verify_transaction_artifact,
    load_training_config,
    train_and_package_transaction_core,
)
from momo_fdvs_ml.transaction_model import (
    runtime_fingerprint as transaction_runtime_fingerprint,
)
from momo_fdvs_ml.transaction_pipeline import TransactionPipelineError


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

    ghana_intake = subparsers.add_parser(
        "ghana-private-intake",
        help="create de-identified private working images and a restricted review index",
    )
    ghana_intake.add_argument("--request", type=Path, required=True)
    ghana_intake.add_argument("--raw-root", type=Path, required=True)
    ghana_intake.add_argument("--working-root", type=Path, required=True)
    ghana_intake.add_argument("--private-index", type=Path, required=True)
    ghana_intake.add_argument("--safe-report", type=Path, required=True)
    ghana_intake.add_argument("--repository-root", type=Path, required=True)
    ghana_intake.add_argument("--withdrawal-ledger", type=Path)

    ghana_consent = subparsers.add_parser(
        "ghana-init-owner-consent",
        help="record restricted self-owner internal-use consent outside the repository",
    )
    ghana_consent.add_argument("--governance-root", type=Path, required=True)
    ghana_consent.add_argument("--repository-root", type=Path, required=True)
    ghana_consent.add_argument("--withdrawal-operator-id", required=True)
    ghana_consent.add_argument(
        "--acknowledgement",
        metavar="TOKEN",
        help=f"required exact token: {OWNER_CONSENT_ACKNOWLEDGEMENT}",
        required=True,
    )

    ghana_messages = subparsers.add_parser(
        "ghana-index-imazing",
        help="create a private de-identified candidate transcript index from an owner export",
    )
    ghana_messages.add_argument("--source-csv", type=Path, required=True)
    ghana_messages.add_argument("--private-index", type=Path, required=True)
    ghana_messages.add_argument("--safe-report", type=Path, required=True)
    ghana_messages.add_argument("--repository-root", type=Path, required=True)
    ghana_messages.add_argument("--participant-id-hash", required=True)
    ghana_messages.add_argument("--permission-reference", required=True)
    ghana_messages.add_argument("--text-column")
    ghana_messages.add_argument("--sender-column")

    ghana_online = subparsers.add_parser(
        "ghana-quarantine-online-candidate",
        help="quarantine one manually acquired web image pending rights and content review",
    )
    ghana_online.add_argument("--source", type=Path, required=True)
    ghana_online.add_argument(
        "--source-page-url",
        help=(
            "exact HTTPS source page; omit only to retain a non-training missing-source quarantine"
        ),
    )
    ghana_online.add_argument("--quarantine-root", type=Path, required=True)
    ghana_online.add_argument("--private-index", type=Path, required=True)
    ghana_online.add_argument("--safe-report", type=Path, required=True)
    ghana_online.add_argument("--repository-root", type=Path, required=True)
    ghana_online.add_argument("--reviewer-id", required=True)

    ghana_review = subparsers.add_parser(
        "ghana-review-transition", help="apply one auditable private review state transition"
    )
    ghana_review.add_argument("--private-index", type=Path, required=True)
    ghana_review.add_argument("--image-id", required=True)
    ghana_review.add_argument("--expected-state", required=True)
    ghana_review.add_argument("--next-state", required=True)
    ghana_review.add_argument("--reviewer-id", required=True)
    ghana_review.add_argument("--reason-code", required=True)

    ghana_online_review = subparsers.add_parser(
        "ghana-review-online-candidate",
        help="record private content triage without granting rights or training eligibility",
    )
    ghana_online_review.add_argument("--private-index", type=Path, required=True)
    ghana_online_review.add_argument("--safe-report", type=Path, required=True)
    ghana_online_review.add_argument("--candidate-id", required=True)
    ghana_online_review.add_argument("--content-class", required=True)
    ghana_online_review.add_argument("--direct-identifier-state", required=True)
    ghana_online_review.add_argument("--reviewer-id", required=True)

    ghana_online_permission = subparsers.add_parser(
        "ghana-attest-online-permission",
        help="record project-owner permission while preserving de-identification/training gates",
    )
    ghana_online_permission.add_argument("--private-index", type=Path, required=True)
    ghana_online_permission.add_argument("--safe-report", type=Path, required=True)
    ghana_online_permission.add_argument("--candidate-id", required=True)
    ghana_online_permission.add_argument("--permission-reference", required=True)
    ghana_online_permission.add_argument(
        "--permission-scope", choices=("internal_model_development",), required=True
    )
    ghana_online_permission.add_argument("--reviewer-id", required=True)

    ghana_split = subparsers.add_parser(
        "ghana-freeze-splits", help="freeze approved private records by participant/source group"
    )
    ghana_split.add_argument("--private-index", type=Path, required=True)
    ghana_split.add_argument("--private-manifest", type=Path, required=True)
    ghana_split.add_argument("--safe-report", type=Path, required=True)
    ghana_split.add_argument("--seed", type=int, default=20260813)

    ghana_withdraw = subparsers.add_parser(
        "ghana-apply-withdrawals",
        help="quarantine withdrawn participant derivatives and record a private receipt",
    )
    ghana_withdraw.add_argument("--private-index", type=Path, required=True)
    ghana_withdraw.add_argument("--withdrawal-ledger", type=Path, required=True)
    ghana_withdraw.add_argument("--working-root", type=Path, required=True)
    ghana_withdraw.add_argument("--quarantine-root", type=Path, required=True)
    ghana_withdraw.add_argument("--receipt", type=Path, required=True)

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

    build_transactions = subparsers.add_parser(
        "build-transaction-features",
        help="build frozen private transaction Parquet shards without model training",
    )
    build_transactions.add_argument(
        "--dataset-id", choices=["paysim", "momtsim-v1", "momtsim-v2"], required=True
    )
    build_transactions.add_argument("--source", type=Path, required=True)
    build_transactions.add_argument("--source-sha256", required=True)
    build_transactions.add_argument("--expected-rows", type=int, required=True)
    build_transactions.add_argument("--expected-positives", type=int, required=True)
    build_transactions.add_argument("--output", type=Path, required=True)
    build_transactions.add_argument("--entrypoint")
    build_transactions.add_argument("--minimum-partition-positives", type=int, default=100)
    build_transactions.add_argument("--shard-size", type=int, default=100_000)

    train_transaction = subparsers.add_parser(
        "train-transaction-core",
        help="fit/calibrate/export PR15 from PR14 bundles in acknowledged Google Colab FULL mode",
    )
    train_transaction.add_argument("--dataset-root", type=Path, required=True)
    train_transaction.add_argument("--output-dir", type=Path, required=True)
    train_transaction.add_argument("--model-version", required=True)
    train_transaction.add_argument("--training-commit-sha", required=True)
    train_transaction.add_argument("--notebook", required=True)
    train_transaction.add_argument("--dependency-lock-sha256", required=True)
    train_transaction.add_argument("--config", type=Path)
    train_transaction.add_argument(
        "--external-dataset-root",
        type=Path,
        action="append",
        default=[],
        help="repeat for compatible non-final cross-source tuning evaluation",
    )
    train_transaction.add_argument(
        "--profile", choices=[profile.value for profile in ExecutionProfile], required=True
    )
    train_transaction.add_argument(
        "--acknowledge-full-training",
        metavar="TOKEN",
        help=f"required for FULL mode: {FULL_TRAINING_ACKNOWLEDGEMENT}",
    )

    verify_transaction = subparsers.add_parser(
        "verify-transaction-artifact",
        help="hash and contract-check one trusted PR15 transaction bundle",
    )
    verify_transaction.add_argument("--artifact", type=Path, required=True)
    verify_transaction.add_argument("--sha256", required=True)

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

        if args.command == "ghana-private-intake":
            withdrawn = (
                load_withdrawal_ledger(args.withdrawal_ledger)
                if args.withdrawal_ledger is not None
                else frozenset()
            )
            intake_outputs = ingest_private_screenshots(
                request_path=args.request,
                raw_root=args.raw_root,
                working_root=args.working_root,
                index_path=args.private_index,
                report_path=args.safe_report,
                repository_root=args.repository_root,
                withdrawn_participants=withdrawn,
            )
            print(
                json.dumps(
                    {
                        "record_count": intake_outputs.record_count,
                        "quarantined_count": intake_outputs.quarantined_count,
                        "private_index_path": str(intake_outputs.index_path),
                        "safe_report_path": str(intake_outputs.report_path),
                        "raw_images_copied": False,
                        "training_executed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "ghana-init-owner-consent":
            consent_outputs = initialize_owner_consent(
                governance_root=args.governance_root,
                repository_root=args.repository_root,
                acknowledgement=args.acknowledgement,
                withdrawal_operator_id=args.withdrawal_operator_id,
            )
            print(
                json.dumps(
                    {
                        "record_path": str(consent_outputs.record_path),
                        "participant_id_hash": consent_outputs.participant_id_hash,
                        "permission_reference": consent_outputs.permission_reference,
                        "consent_scope": "internal_only",
                        "public_release_consent": False,
                        "training_eligible": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "ghana-index-imazing":
            message_outputs = index_imazing_messages(
                source_csv=args.source_csv,
                index_path=args.private_index,
                report_path=args.safe_report,
                repository_root=args.repository_root,
                participant_id_hash=args.participant_id_hash,
                permission_reference=args.permission_reference,
                text_column=args.text_column,
                sender_column=args.sender_column,
            )
            print(
                json.dumps(
                    {
                        "message_count": message_outputs.record_count,
                        "private_index_path": str(message_outputs.index_path),
                        "safe_report_path": str(message_outputs.report_path),
                        "training_eligible": False,
                        "training_executed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "ghana-quarantine-online-candidate":
            candidate_outputs = quarantine_online_candidate(
                source_path=args.source,
                source_page_url=args.source_page_url,
                quarantine_root=args.quarantine_root,
                index_path=args.private_index,
                report_path=args.safe_report,
                repository_root=args.repository_root,
                reviewer_id=args.reviewer_id,
            )
            print(
                json.dumps(
                    {
                        "candidate_id": candidate_outputs.candidate_id,
                        "status": candidate_outputs.status,
                        "private_index_path": str(candidate_outputs.index_path),
                        "safe_report_path": str(candidate_outputs.report_path),
                        "training_eligible": False,
                        "automated_scraping_executed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "ghana-review-transition":
            advance_review(
                index_path=args.private_index,
                image_id=args.image_id,
                expected_state=args.expected_state,
                next_state=args.next_state,
                reviewer_id=args.reviewer_id,
                reason_code=args.reason_code,
            )
            print(json.dumps({"review_transition_applied": True}, indent=2, sort_keys=True))
            return 0

        if args.command == "ghana-review-online-candidate":
            review_online_candidate(
                index_path=args.private_index,
                report_path=args.safe_report,
                candidate_id=args.candidate_id,
                content_class=args.content_class,
                direct_identifier_state=args.direct_identifier_state,
                reviewer_id=args.reviewer_id,
            )
            print(
                json.dumps(
                    {
                        "content_review_recorded": True,
                        "rights_approved": False,
                        "training_eligible": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "ghana-attest-online-permission":
            attest_online_candidate_permission(
                index_path=args.private_index,
                report_path=args.safe_report,
                candidate_id=args.candidate_id,
                permission_reference=args.permission_reference,
                reviewer_id=args.reviewer_id,
                permission_scope=args.permission_scope,
            )
            print(
                json.dumps(
                    {
                        "permission_attestation_recorded": True,
                        "permission_scope": args.permission_scope,
                        "training_eligible": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "ghana-freeze-splits":
            split_outputs = freeze_group_splits(
                index_path=args.private_index,
                manifest_path=args.private_manifest,
                report_path=args.safe_report,
                seed=args.seed,
            )
            print(
                json.dumps(
                    {
                        "manifest_sha256": split_outputs.manifest_sha256,
                        "private_manifest_path": str(split_outputs.manifest_path),
                        "safe_report_path": str(split_outputs.report_path),
                        "locked_test": True,
                        "training_executed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "ghana-apply-withdrawals":
            affected = apply_withdrawals(
                index_path=args.private_index,
                withdrawn_participants=load_withdrawal_ledger(args.withdrawal_ledger),
                working_root=args.working_root,
                quarantine_root=args.quarantine_root,
                receipt_path=args.receipt,
            )
            print(
                json.dumps(
                    {
                        "affected_record_count": affected,
                        "split_rebuild_required": affected > 0,
                        "dependent_artifacts_invalidated": affected > 0,
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

        if args.command == "build-transaction-features":
            report = build_transaction_parquet_dataset(
                source_path=args.source,
                output_path=args.output,
                spec=TransactionBuildSpec(
                    dataset_id=args.dataset_id,
                    source_sha256=args.source_sha256,
                    expected_row_count=args.expected_rows,
                    expected_positive_count=args.expected_positives,
                    minimum_partition_positives=args.minimum_partition_positives,
                    shard_size=args.shard_size,
                    entrypoint=args.entrypoint,
                ),
            )
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0

        if args.command == "train-transaction-core":
            require_training_execution(
                ExecutionProfile(args.profile),
                acknowledgement=args.acknowledge_full_training,
            )
            transaction_outputs = train_and_package_transaction_core(
                dataset_root=args.dataset_root,
                output_dir=args.output_dir,
                model_version=args.model_version,
                training_commit_sha=args.training_commit_sha,
                notebook=args.notebook,
                dependency_lock_sha256=args.dependency_lock_sha256,
                config=load_training_config(args.config),
                external_dataset_roots=tuple(args.external_dataset_root),
            )
            print(
                json.dumps(
                    {
                        "artifact_path": str(transaction_outputs.artifact_path),
                        "artifact_sha256": transaction_outputs.artifact_sha256,
                        "report_path": str(transaction_outputs.report_path),
                        "model_card_path": str(transaction_outputs.model_card_path),
                        "registry_payload_path": str(transaction_outputs.registry_payload_path),
                        "run_manifest_path": str(transaction_outputs.run_manifest_path),
                        "dataset_id": transaction_outputs.report["dataset_id"],
                        "selected_family": transaction_outputs.report["selection"]["family"],
                        "locked_test_accessed_for_decisions": False,
                        "final_evaluation_executed": False,
                        "not_real_world_probability": True,
                        "runtime": transaction_runtime_fingerprint(),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "verify-transaction-artifact":
            transaction_bundle = load_and_verify_transaction_artifact(
                args.artifact, expected_sha256=args.sha256
            )
            print(
                json.dumps(
                    {
                        "artifact_verified": True,
                        "model_name": transaction_bundle["model_name"],
                        "model_version": transaction_bundle["model_version"],
                        "dataset_id": transaction_bundle["dataset_id"],
                        "feature_contract_version": transaction_bundle["feature_contract_version"],
                        "locked_test_accessed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
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
        GhanaPrivateError,
        GovernanceError,
        ImageDatasetError,
        ImageModelError,
        ManifestError,
        NotebookPolicyError,
        StructuredDatasetError,
        StructuredModelError,
        TransactionModelError,
        TransactionPipelineError,
    ) as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
