from __future__ import annotations

import hashlib
import io
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from flask import Flask
from PIL import Image
from sqlalchemy import func, select

from momo_fdvs.extensions import db
from momo_fdvs.models import (
    AnalysisRun,
    FraudRuleSet,
    OCRConfirmation,
    OCRResult,
    Receipt,
    ReferenceImportBatch,
    ReferenceTransaction,
    Transaction,
    User,
)
from momo_fdvs.services.analysis_orchestrator import (
    ANALYSIS_STAGES,
    AnalysisFailure,
    AnalysisOrchestrationResult,
    run_analysis,
)
from momo_fdvs.storage.local import LocalPrivateStorage

pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="requires an isolated PostgreSQL test database",
)


def _png_bytes() -> bytes:
    stream = io.BytesIO()
    Image.new("RGB", (96, 160), color=(245, 247, 240)).save(stream, format="PNG")
    return stream.getvalue()


@dataclass(frozen=True)
class ControlledAnalysisCase:
    app: Flask
    transaction_id: uuid.UUID
    confirmation_id: uuid.UUID
    user_id: uuid.UUID
    storage: LocalPrivateStorage
    receipt_key: str

    def add_confirmation(self, *, amount: str) -> uuid.UUID:
        with self.app.app_context():
            existing = db.session.get(OCRConfirmation, self.confirmation_id)
            assert existing is not None
            confirmation = OCRConfirmation(
                ocr_result_id=existing.ocr_result_id,
                transaction_id=self.transaction_id,
                confirmed_fields={**existing.confirmed_fields, "amount": amount},
                corrections=[
                    {
                        "field": "amount",
                        "reason": "Controlled conflict fixture",
                    }
                ],
                confirmed_by=self.user_id,
                confirmed_at=datetime.now(UTC),
                schema_version="ocr-fields-v1",
            )
            db.session.add(confirmation)
            db.session.commit()
            return confirmation.id

    def run(
        self,
        *,
        key: str,
        confirmation_id: uuid.UUID | None = None,
        policy_path: Path | None = None,
    ) -> AnalysisOrchestrationResult:
        with self.app.app_context():
            transaction = db.session.get(Transaction, self.transaction_id)
            confirmation = db.session.get(OCRConfirmation, confirmation_id or self.confirmation_id)
            user = db.session.get(User, self.user_id)
            assert transaction is not None and confirmation is not None and user is not None
            return run_analysis(
                transaction=transaction,
                confirmation=confirmation,
                user=user,
                roles={"USER"},
                idempotency_key=key,
                storage=self.storage,
                policy_path=policy_path,
            )


def _controlled_case(
    app: Flask,
    tmp_path: Path,
    *,
    observed_amount: str,
) -> ControlledAnalysisCase:
    storage = LocalPrivateStorage(tmp_path / "analysis-storage")
    payload = _png_bytes()
    now = datetime.now(UTC)
    case_token = uuid.uuid4().hex
    reference_code = f"C{case_token[:11].upper()}"
    with app.app_context():
        user = User(
            email=f"analysis-{uuid.uuid4()}@example.test",
            password_hash="controlled-not-a-login-secret",
            full_name="Controlled Analysis User",
            status="ACTIVE",
            password_changed_at=now,
        )
        db.session.add(user)
        db.session.flush()
        transaction = Transaction(
            user_id=user.id,
            status="READY",
            provider_code="MTN_MOMO",
            display_reference_masked="CTRL...56",
        )
        db.session.add(transaction)
        db.session.flush()
        receipt_key = f"receipts/{user.id}/{transaction.id}/original/controlled.png"
        storage.put_bytes(receipt_key, payload, "image/png")
        receipt = Receipt(
            transaction_id=transaction.id,
            object_key=receipt_key,
            original_filename="controlled.png",
            media_type="image/png",
            size_bytes=len(payload),
            width_px=96,
            height_px=160,
            sha256=hashlib.sha256(payload).hexdigest(),
            perceptual_hash="abcdef0123456789",
            quality_warnings=[],
            storage_version="local-v1",
        )
        db.session.add(receipt)
        db.session.flush()
        ocr = OCRResult(
            receipt_id=receipt.id,
            engine_name="tesseract",
            engine_version="controlled",
            pipeline_version="ocr-pipeline-v1",
            selected_variant="original",
            raw_text="controlled test fixture",
            token_data=[],
            extracted_fields={
                "amount": {"value": observed_amount, "confidence": 0.95},
                "transaction_reference": {
                    "value": reference_code,
                    "confidence": 0.96,
                },
            },
            field_confidences={"amount": 0.95, "transaction_reference": 0.96},
            warnings=[],
            required_field_accuracy_hint=Decimal("0.95"),
        )
        db.session.add(ocr)
        db.session.flush()
        confirmation = OCRConfirmation(
            ocr_result_id=ocr.id,
            transaction_id=transaction.id,
            confirmed_fields={
                "provider_code": "MTN_MOMO",
                "transaction_reference": reference_code,
                "amount": observed_amount,
                "currency": "GHS",
                "sender_name": "Controlled Sender",
                "sender_phone": "+233240000002",
                "receiver_name": "Controlled Receiver",
                "receiver_phone": "+233240000001",
                "occurred_at": "2026-08-08T14:30:00Z",
                "status_text": "SUCCESSFUL",
            },
            corrections=[],
            confirmed_by=user.id,
            confirmed_at=now,
            schema_version="ocr-fields-v1",
        )
        rule_set = db.session.scalar(select(FraudRuleSet).where(FraudRuleSet.status == "ACTIVE"))
        if rule_set is None:
            rule_set = FraudRuleSet(
                version=f"analysis-policy-{case_token}",
                status="ACTIVE",
                risk_weights={},
                thresholds={},
                description="Controlled PR18 analysis policy anchor.",
                created_by=user.id,
                activated_by=user.id,
                activated_at=now,
                row_version=1,
            )
            db.session.add(rule_set)
        batch = ReferenceImportBatch(
            source_label=f"controlled-pr18-{case_token}",
            original_filename="controlled.csv",
            file_sha256=hashlib.sha256(case_token.encode()).hexdigest(),
            status="COMMITTED",
            total_rows=1,
            valid_rows=1,
            invalid_rows=0,
            uploaded_by=user.id,
        )
        db.session.add_all([confirmation, batch])
        db.session.flush()
        db.session.add(
            ReferenceTransaction(
                import_batch_id=batch.id,
                provider_code="MTN_MOMO",
                transaction_reference=reference_code,
                amount=Decimal("125.00"),
                currency="GHS",
                sender_name_normalised="CONTROLLED SENDER",
                sender_phone_e164="+233240000002",
                receiver_name_normalised="CONTROLLED RECEIVER",
                receiver_phone_e164="+233240000001",
                occurred_at=datetime(2026, 8, 8, 14, 30, tzinfo=UTC),
                transaction_status="SUCCESSFUL",
                raw_row={"controlled_fixture": True},
            )
        )
        db.session.commit()
        return ControlledAnalysisCase(
            app=app,
            transaction_id=transaction.id,
            confirmation_id=confirmation.id,
            user_id=user.id,
            storage=storage,
            receipt_key=receipt_key,
        )


@pytest.fixture
def mismatch_case(app: Flask, tmp_path: Path) -> ControlledAnalysisCase:
    return _controlled_case(app, tmp_path, observed_amount="999.00")


@pytest.fixture
def verified_case(app: Flask, tmp_path: Path) -> ControlledAnalysisCase:
    return _controlled_case(app, tmp_path, observed_amount="125.00")


def test_mismatch_completes_high_risk_and_persists_all_stages(
    mismatch_case: ControlledAnalysisCase,
) -> None:
    result = mismatch_case.run(key="analysis-mismatch-key")

    assert result.run.status == "COMPLETED"
    assert result.run.risk_class == "FRAUDULENT"
    assert result.run.risk_score is None
    assert [stage.stage for stage in result.stages] == list(ANALYSIS_STAGES)
    assert result.verification.status == "MISMATCH"


def test_verified_reference_without_models_is_partial_inconclusive(
    verified_case: ControlledAnalysisCase,
) -> None:
    result = verified_case.run(key="analysis-verified-key")

    assert result.run.status == "PARTIAL"
    assert result.run.risk_class is None
    assert result.run.component_scores["policy"]["band"] == "inconclusive"
    assert result.verification.status == "VERIFIED"


def test_same_key_and_fingerprint_replays_immutable_run(
    mismatch_case: ControlledAnalysisCase,
) -> None:
    first = mismatch_case.run(key="analysis-replay-key")
    second = mismatch_case.run(key="analysis-replay-key")

    assert second.replayed is True
    assert second.run.id == first.run.id
    assert len(second.stages) == len(first.stages) == len(ANALYSIS_STAGES)


def test_same_key_with_changed_confirmation_returns_conflict(
    mismatch_case: ControlledAnalysisCase,
) -> None:
    mismatch_case.run(key="analysis-conflict-key")
    second_confirmation_id = mismatch_case.add_confirmation(amount="998.00")

    with pytest.raises(AnalysisFailure) as raised:
        mismatch_case.run(
            key="analysis-conflict-key",
            confirmation_id=second_confirmation_id,
        )

    assert raised.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert raised.value.status == 409


def test_image_failure_retains_verification_and_safe_error(
    verified_case: ControlledAnalysisCase,
) -> None:
    verified_case.storage.delete(verified_case.receipt_key)

    result = verified_case.run(key="analysis-image-failure-key")

    assert result.verification.status == "VERIFIED"
    image_stage = next(stage for stage in result.stages if stage.stage == "DETERMINISTIC_IMAGE")
    assert image_stage.status == "FAILED"
    assert image_stage.error_code == "IMAGE_STORAGE_UNAVAILABLE"
    assert str(verified_case.storage.root) not in str(result.run.component_scores)


def test_structured_stage_skips_without_exact_context(
    verified_case: ControlledAnalysisCase,
) -> None:
    result = verified_case.run(key="analysis-structured-skip-key")

    stage = next(stage for stage in result.stages if stage.stage == "STRUCTURED_MODEL")
    assert stage.status == "SKIPPED"
    assert stage.error_code == "STRUCTURED_CONTEXT_UNAVAILABLE"


def test_invalid_policy_rolls_back_without_final_risk(
    verified_case: ControlledAnalysisCase,
    tmp_path: Path,
) -> None:
    invalid_policy = tmp_path / "invalid-policy.json"
    invalid_policy.write_text("{}", encoding="utf-8")

    with pytest.raises(AnalysisFailure) as raised:
        verified_case.run(
            key="analysis-invalid-policy-key",
            policy_path=invalid_policy,
        )

    assert raised.value.code == "RISK_POLICY_SCHEMA_INVALID"
    with verified_case.app.app_context():
        run_count = db.session.scalar(
            select(func.count(AnalysisRun.id)).where(
                AnalysisRun.transaction_id == verified_case.transaction_id
            )
        )
        assert run_count == 0
