"""Deterministic database factories spanning every later feature domain."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from momo_fdvs.models import (
    AnalysisRun,
    AuditLog,
    FraudCase,
    FraudRule,
    FraudRuleSet,
    ModelVersion,
    Notification,
    OCRConfirmation,
    OCRResult,
    Receipt,
    ReferenceImportBatch,
    ReferenceTransaction,
    Role,
    Transaction,
    User,
    VerificationResult,
)


def create_complete_graph(session: Session) -> dict[str, object]:
    now = datetime.now(UTC)
    user = User(
        email=f"user-{uuid.uuid4()}@example.test",
        password_hash="fixture-only-not-a-real-password",
        full_name="Controlled Fixture User",
        status="ACTIVE",
        password_changed_at=now,
    )
    session.add(user)
    if session.get(Role, "USER") is None:
        session.add(Role(code="USER", description="User"))
    session.flush()
    transaction = Transaction(user_id=user.id, status="UPLOADED")
    session.add(transaction)
    session.flush()
    receipt = Receipt(
        transaction_id=transaction.id,
        object_key=f"receipts/{user.id}/{transaction.id}/original/{uuid.uuid4()}.png",
        original_filename="controlled.png",
        media_type="image/png",
        size_bytes=10,
        width_px=320,
        height_px=320,
        sha256="1" * 64,
        perceptual_hash="abcdef0123456789",
        quality_warnings=[],
        storage_version="local-v1",
    )
    session.add(receipt)
    session.flush()
    ocr = OCRResult(
        receipt_id=receipt.id,
        engine_name="tesseract",
        engine_version="fixture",
        pipeline_version="fixture-v1",
        selected_variant="original",
        raw_text="controlled",
        token_data=[],
        extracted_fields={},
        field_confidences={},
        warnings=[],
    )
    session.add(ocr)
    session.flush()
    confirmation = OCRConfirmation(
        ocr_result_id=ocr.id,
        transaction_id=transaction.id,
        confirmed_fields={},
        corrections=[],
        confirmed_by=user.id,
        confirmed_at=now,
        schema_version="fixture-v1",
    )
    rule_set = FraudRuleSet(
        version=f"fixture-{uuid.uuid4()}",
        status="DRAFT",
        risk_weights={},
        thresholds={},
        description="fixture",
        created_by=user.id,
        row_version=1,
    )
    model = ModelVersion(
        model_type="STRUCTURED",
        name="fixture",
        version=str(uuid.uuid4()),
        status="DRAFT",
        artifact_uri="private://unavailable",
        artifact_sha256="2" * 64,
        input_schema_hash="3" * 64,
        preprocessing_version="fixture",
        framework_versions={},
        metrics={"status": "not_trained"},
    )
    session.add_all([confirmation, rule_set, model])
    session.flush()
    session.add(
        FraudRule(
            rule_set_id=rule_set.id,
            code="FIXTURE",
            description="fixture",
            severity="LOW",
            condition={},
            score_contribution=Decimal("0"),
            reason_template="fixture",
            enabled=True,
        )
    )
    run = AnalysisRun(
        transaction_id=transaction.id,
        ocr_confirmation_id=confirmation.id,
        status="QUEUED",
        rule_set_id=rule_set.id,
        structured_model_id=model.id,
        request_fingerprint="4" * 64,
        queued_at=now,
        component_scores={},
        top_reasons=[],
        configuration_snapshot={},
    )
    session.add(run)
    session.flush()
    batch = ReferenceImportBatch(
        source_label=f"fixture-{uuid.uuid4()}",
        original_filename="fixture.csv",
        file_sha256="5" * 64,
        status="COMMITTED",
        total_rows=1,
        valid_rows=1,
        invalid_rows=0,
        uploaded_by=user.id,
    )
    session.add(batch)
    session.flush()
    reference = ReferenceTransaction(
        import_batch_id=batch.id,
        provider_code="FIXTURE",
        transaction_reference=str(uuid.uuid4()),
        amount=Decimal("1.00"),
        currency="GHS",
        raw_row={"synthetic_only": True},
    )
    case = FraudCase(
        transaction_id=transaction.id,
        source="USER_REPORT",
        reporter_id=user.id,
        category="fixture",
        status="OPEN",
        opened_at=now,
    )
    notification = Notification(
        user_id=user.id,
        type="FIXTURE",
        title="Fixture",
        message="Fixture",
        delivery_status={},
    )
    audit = AuditLog(
        actor_id=user.id,
        actor_role_snapshot=["USER"],
        action="fixture.created",
        target_type="transaction",
        target_id=transaction.id,
        outcome="SUCCESS",
        request_id=uuid.uuid4(),
        metadata_json={},
    )
    session.add_all([reference, case, notification, audit])
    session.flush()
    verification = VerificationResult(
        analysis_run_id=run.id,
        reference_transaction_id=reference.id,
        status="VERIFIED",
        verifier_version="fixture",
        candidate_method="exact",
        field_comparisons={},
        matched_field_count=1,
        mismatched_field_count=0,
        warnings=[],
    )
    session.add(verification)
    session.flush()
    return locals()
