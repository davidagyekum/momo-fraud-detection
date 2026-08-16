from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from momo_fdvs.contracts.evidence import EvidenceMode, RiskBand
from momo_fdvs.services.risk_policy import (
    AnalysisPolicyInput,
    LoadedRiskPolicy,
    ModelPolicySignal,
    PolicyFailure,
    PolicyReason,
    evaluate_risk_policy,
    load_risk_policy,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = REPOSITORY_ROOT / "services/api/src/momo_fdvs/policies/risk_policy_demo_v1.json"


def test_risk_policy_is_declared_as_wheel_package_data() -> None:
    pyproject = tomllib.loads(
        (REPOSITORY_ROOT / "services/api/pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["tool"]["setuptools"]["package-data"]["momo_fdvs.policies"] == ["*.json"]


@pytest.fixture
def policy() -> LoadedRiskPolicy:
    return load_risk_policy(POLICY_PATH)


def _unavailable_input(
    *,
    verification_status: str = "UNVERIFIED",
    mismatches: tuple[str, ...] = (),
    complete: bool = True,
    deterministic_reasons: tuple[PolicyReason, ...] = (),
    corrected_fields: tuple[str, ...] = (),
) -> AnalysisPolicyInput:
    return AnalysisPolicyInput(
        mode=EvidenceMode.SCREENSHOT_ONLY,
        verification_status=verification_status,
        critical_verification_mismatches=mismatches,
        confirmed_critical_fields_complete=complete,
        corrected_low_confidence_fields=corrected_fields,
        deterministic_image_reasons=deterministic_reasons,
        image_model=ModelPolicySignal.unavailable("IMAGE", "IMAGE_MODEL_NOT_ACTIVE"),
        structured_model=ModelPolicySignal.unavailable(
            "STRUCTURED", "STRUCTURED_CONTEXT_UNAVAILABLE"
        ),
        semantic_reasons=(),
    )


def _available_structured(predicted_class: str, score: float) -> ModelPolicySignal:
    return ModelPolicySignal(
        kind="STRUCTURED",
        available=True,
        score=score,
        predicted_class=predicted_class,
        reason_codes=("STRUCTURED_MODEL_SUCCESS",),
        model_version="structured-controlled-v1",
        artifact_sha256="a" * 64,
        schema_hash="b" * 64,
    )


def _with_structured(
    source: AnalysisPolicyInput,
    predicted_class: str,
    score: float,
) -> AnalysisPolicyInput:
    return AnalysisPolicyInput(
        mode=source.mode,
        verification_status=source.verification_status,
        critical_verification_mismatches=source.critical_verification_mismatches,
        confirmed_critical_fields_complete=source.confirmed_critical_fields_complete,
        corrected_low_confidence_fields=source.corrected_low_confidence_fields,
        deterministic_image_reasons=source.deterministic_image_reasons,
        image_model=source.image_model,
        structured_model=_available_structured(predicted_class, score),
        semantic_reasons=source.semantic_reasons,
    )


def test_reference_amount_mismatch_is_categorical_high_without_invented_score(
    policy: LoadedRiskPolicy,
) -> None:
    result = evaluate_risk_policy(
        policy,
        _unavailable_input(
            verification_status="MISMATCH",
            mismatches=("amount",),
        ),
    )

    assert result.status == "PARTIAL"
    assert result.band is RiskBand.HIGH
    assert result.legacy_risk_class == "FRAUDULENT"
    assert result.score is None
    assert [reason.code for reason in result.reasons] == ["REFERENCE_AMOUNT_MISMATCH"]
    assert set(result.missing_signals) == {
        "IMAGE_MODEL_NOT_ACTIVE",
        "STRUCTURED_CONTEXT_UNAVAILABLE",
    }


def test_reference_match_without_conclusive_model_stays_inconclusive(
    policy: LoadedRiskPolicy,
) -> None:
    result = evaluate_risk_policy(
        policy,
        _unavailable_input(verification_status="VERIFIED"),
    )

    assert result.status == "PARTIAL"
    assert result.band is RiskBand.INCONCLUSIVE
    assert result.legacy_risk_class is None
    assert result.score is None
    assert "STORED_REFERENCE_MATCH_NOT_AUTHENTICITY" in result.limitations


def test_deterministic_warning_is_supporting_evidence_not_tamper_classification(
    policy: LoadedRiskPolicy,
) -> None:
    result = evaluate_risk_policy(
        policy,
        _unavailable_input(
            deterministic_reasons=(
                PolicyReason(
                    code="IMAGE_COMPRESSION_INCONSISTENCY",
                    title="Compression differs across regions",
                    severity="MEDIUM",
                ),
            )
        ),
    )

    assert result.band is RiskBand.INCONCLUSIVE
    assert result.legacy_risk_class is None
    assert "DETERMINISTIC_IMAGE_SUPPORTING_ONLY" in result.limitations
    assert "IMAGE_COMPRESSION_INCONSISTENCY" in {reason.code for reason in result.reasons}


@pytest.mark.parametrize(
    ("predicted_class", "score", "expected_band", "legacy_class"),
    [
        ("GENUINE", 0.08, RiskBand.LOW, "GENUINE"),
        ("SUSPICIOUS", 0.52, RiskBand.MEDIUM, "SUSPICIOUS"),
        ("FRAUDULENT", 0.91, RiskBand.HIGH, "FRAUDULENT"),
    ],
)
def test_exact_contract_structured_prediction_maps_without_averaging(
    policy: LoadedRiskPolicy,
    predicted_class: str,
    score: float,
    expected_band: RiskBand,
    legacy_class: str,
) -> None:
    value = _with_structured(
        _unavailable_input(verification_status="VERIFIED"),
        predicted_class,
        score,
    )

    result = evaluate_risk_policy(policy, value)

    assert result.band is expected_band
    assert result.legacy_risk_class == legacy_class
    assert result.score is None


def test_accepted_image_tamper_signal_above_threshold_can_trigger_high(
    policy: LoadedRiskPolicy,
) -> None:
    source = _unavailable_input()
    value = AnalysisPolicyInput(
        mode=source.mode,
        verification_status=source.verification_status,
        critical_verification_mismatches=(),
        confirmed_critical_fields_complete=True,
        corrected_low_confidence_fields=(),
        deterministic_image_reasons=(),
        image_model=ModelPolicySignal(
            kind="IMAGE",
            available=True,
            score=0.86,
            predicted_class="tampered",
            reason_codes=("IMAGE_MODEL_SUCCESS",),
            model_version="accepted-image-v1",
            artifact_sha256="c" * 64,
            schema_hash="d" * 64,
        ),
        structured_model=source.structured_model,
        semantic_reasons=(),
    )

    result = evaluate_risk_policy(policy, value)

    assert result.band is RiskBand.HIGH
    assert result.score is None
    assert [reason.code for reason in result.reasons] == ["IMAGE_MODEL_TAMPER_THRESHOLD_EXCEEDED"]


def test_structured_low_is_blocked_when_confirmed_critical_fields_are_incomplete(
    policy: LoadedRiskPolicy,
) -> None:
    value = _with_structured(
        _unavailable_input(verification_status="VERIFIED", complete=False),
        "GENUINE",
        0.05,
    )

    result = evaluate_risk_policy(policy, value)

    assert result.band is RiskBand.INCONCLUSIVE
    assert "CRITICAL_OCR_FIELDS_INCOMPLETE" in result.missing_signals


def test_corrected_low_confidence_field_is_limitation_not_fraud_reason(
    policy: LoadedRiskPolicy,
) -> None:
    result = evaluate_risk_policy(
        policy,
        _unavailable_input(corrected_fields=("amount",)),
    )

    assert result.band is RiskBand.INCONCLUSIVE
    assert "CORRECTED_LOW_CONFIDENCE_FIELDS" in result.limitations
    assert all("FRAUD" not in reason.code for reason in result.reasons)


def test_policy_expected_hash_mismatch_fails_without_path_leakage() -> None:
    with pytest.raises(PolicyFailure) as raised:
        load_risk_policy(POLICY_PATH, expected_sha256="0" * 64)

    assert raised.value.code == "RISK_POLICY_HASH_MISMATCH"
    assert str(POLICY_PATH) not in str(raised.value)


def test_policy_unknown_key_fails_closed_without_value_leakage(tmp_path: Path) -> None:
    policy_path = tmp_path / "private-policy-name.json"
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    payload["private_rule"] = "do-not-leak"
    policy_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(PolicyFailure) as raised:
        load_risk_policy(policy_path)

    assert raised.value.code == "RISK_POLICY_SCHEMA_INVALID"
    assert "private-policy-name" not in str(raised.value)
    assert "do-not-leak" not in str(raised.value)


def test_unavailable_model_rejects_invented_score_and_class() -> None:
    with pytest.raises(PolicyFailure) as raised:
        ModelPolicySignal(
            kind="IMAGE",
            available=False,
            score=0.0,
            predicted_class="unaltered",
            reason_codes=("IMAGE_MODEL_NOT_ACTIVE",),
        )
    assert raised.value.code == "RISK_POLICY_INPUT_INVALID"


def test_model_kind_rejects_class_from_other_taxonomy() -> None:
    with pytest.raises(PolicyFailure, match="image model class"):
        ModelPolicySignal(
            kind="IMAGE",
            available=True,
            score=0.8,
            predicted_class="FRAUDULENT",
            reason_codes=("IMAGE_MODEL_SUCCESS",),
            model_version="image-v1",
            artifact_sha256="e" * 64,
            schema_hash="f" * 64,
        )


def test_analysis_result_schema_allows_categorical_null_score(
    policy: LoadedRiskPolicy,
) -> None:
    schema = json.loads(
        (REPOSITORY_ROOT / "packages/evidence-contracts/analysis-result-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    result = evaluate_risk_policy(
        policy,
        _unavailable_input(
            verification_status="MISMATCH",
            mismatches=("transaction_reference",),
        ),
    ).as_dict()

    assert schema["properties"]["score"]["type"] == ["number", "null"]
    assert schema["properties"]["legacy_risk_class"]["type"] == [
        "string",
        "null",
    ]
    assert schema["$defs"]["verification"]["additionalProperties"] is False
    assert schema["$defs"]["imageEvidence"]["additionalProperties"] is False
    assert schema["$defs"]["modelStatus"]["additionalProperties"] is False
    assert schema["$defs"]["versions"]["additionalProperties"] is False
    assert result["score"] is None
    assert result["legacy_risk_class"] == "FRAUDULENT"
