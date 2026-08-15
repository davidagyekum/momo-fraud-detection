from __future__ import annotations

import json
from pathlib import Path

import pytest

from momo_fdvs.contracts.evidence import (
    EVIDENCE_CONTRACT_VERSION,
    EvidenceContractError,
    EvidenceMode,
    EvidenceResult,
    EvidenceSignal,
    ImageLabel,
    RiskBand,
    SignalState,
    canonical_image_from_legacy,
    canonical_risk_from_legacy,
    legacy_risk_from_band,
)


def _available(*, score: float = 0.25, label: ImageLabel | None = None) -> EvidenceSignal:
    return EvidenceSignal(
        state=SignalState.AVAILABLE,
        score=score,
        label=label,
        reason_codes=("EVIDENCE_AVAILABLE",),
    )


def _unavailable(name: str) -> EvidenceSignal:
    return EvidenceSignal.unavailable(f"{name.upper()}_UNAVAILABLE")


def test_screenshot_only_keeps_transaction_score_null() -> None:
    result = EvidenceResult(
        mode=EvidenceMode.SCREENSHOT_ONLY,
        image=_available(label=ImageLabel.UNALTERED),
        ocr=_available(),
        semantic=_available(),
        transaction=_unavailable("transaction"),
        risk_band=RiskBand.LOW,
        risk_score=0.2,
        reason_codes=("SCREENSHOT_EVIDENCE_ONLY",),
    )

    payload = result.as_dict()
    assert payload["transaction"] == {
        "state": "unavailable",
        "score": None,
        "label": None,
        "reason_codes": ["TRANSACTION_UNAVAILABLE"],
    }
    assert payload["mode"] == "screenshot_only"


def test_transaction_only_keeps_image_ocr_and_semantic_unavailable() -> None:
    result = EvidenceResult(
        mode=EvidenceMode.TRANSACTION_ONLY,
        image=_unavailable("image"),
        ocr=_unavailable("ocr"),
        semantic=_unavailable("semantic"),
        transaction=_available(score=0.7),
        risk_band=RiskBand.HIGH,
        risk_score=0.7,
        reason_codes=("TRANSACTION_EVIDENCE_ONLY",),
    )

    payload = result.as_dict()
    assert payload["image"]["score"] is None  # type: ignore[index]
    assert payload["ocr"]["state"] == "unavailable"  # type: ignore[index]
    assert payload["semantic"]["state"] == "unavailable"  # type: ignore[index]


def test_unavailable_signals_reject_invented_zero_defaults() -> None:
    with pytest.raises(EvidenceContractError, match="must keep score and label null"):
        EvidenceSignal(state=SignalState.UNAVAILABLE, score=0.0)


def test_combined_mode_requires_both_evidence_families() -> None:
    with pytest.raises(EvidenceContractError, match="screenshot-derived"):
        EvidenceResult(
            mode=EvidenceMode.COMBINED,
            image=_unavailable("image"),
            ocr=_unavailable("ocr"),
            semantic=_unavailable("semantic"),
            transaction=_available(),
            risk_band=RiskBand.MEDIUM,
            risk_score=0.5,
            reason_codes=("COMBINED_EVIDENCE",),
        )


def test_conclusive_modes_require_actual_evidence_and_policy_score() -> None:
    with pytest.raises(EvidenceContractError, match="requires screenshot-derived"):
        EvidenceResult(
            mode=EvidenceMode.SCREENSHOT_ONLY,
            image=_unavailable("image"),
            ocr=_unavailable("ocr"),
            semantic=_unavailable("semantic"),
            transaction=_unavailable("transaction"),
            risk_band=RiskBand.LOW,
            risk_score=0.1,
            reason_codes=("INSUFFICIENT_EVIDENCE",),
        )
    with pytest.raises(EvidenceContractError, match="requires a policy score"):
        EvidenceResult(
            mode=EvidenceMode.TRANSACTION_ONLY,
            image=_unavailable("image"),
            ocr=_unavailable("ocr"),
            semantic=_unavailable("semantic"),
            transaction=_available(),
            risk_band=RiskBand.MEDIUM,
            risk_score=None,
            reason_codes=("TRANSACTION_EVIDENCE_ONLY",),
        )


def test_reason_codes_are_required_and_non_image_signals_cannot_have_image_labels() -> None:
    with pytest.raises(EvidenceContractError, match="at least one"):
        EvidenceSignal(state=SignalState.AVAILABLE, score=0.2)
    with pytest.raises(EvidenceContractError, match="only image evidence"):
        EvidenceResult(
            mode=EvidenceMode.TRANSACTION_ONLY,
            image=_unavailable("image"),
            ocr=_unavailable("ocr"),
            semantic=_unavailable("semantic"),
            transaction=_available(label=ImageLabel.TAMPERED),
            risk_band=RiskBand.HIGH,
            risk_score=0.8,
            reason_codes=("TRANSACTION_EVIDENCE_ONLY",),
        )


def test_inconclusive_mode_has_no_fabricated_score() -> None:
    unavailable = _unavailable("evidence")
    result = EvidenceResult(
        mode=EvidenceMode.INCONCLUSIVE,
        image=unavailable,
        ocr=unavailable,
        semantic=unavailable,
        transaction=unavailable,
        risk_band=RiskBand.INCONCLUSIVE,
        risk_score=None,
        reason_codes=("INSUFFICIENT_EVIDENCE",),
    )
    assert result.as_dict()["risk_score"] is None
    assert legacy_risk_from_band(RiskBand.INCONCLUSIVE) is None


def test_new_image_contract_rejects_genuine_and_fake_labels() -> None:
    for legacy_authenticity_label in ("genuine", "fake", "ORIGINAL"):
        with pytest.raises(EvidenceContractError, match="unaltered or tampered"):
            EvidenceSignal(  # type: ignore[arg-type]
                state=SignalState.AVAILABLE,
                score=0.1,
                label=legacy_authenticity_label,
            )


def test_legacy_taxonomy_projections_are_explicit_and_loss_aware() -> None:
    assert canonical_image_from_legacy("ORIGINAL") is ImageLabel.UNALTERED
    assert canonical_image_from_legacy("CONTROLLED_TAMPERED") is ImageLabel.TAMPERED
    assert canonical_risk_from_legacy("GENUINE") is RiskBand.LOW
    assert canonical_risk_from_legacy("SUSPICIOUS") is RiskBand.MEDIUM
    assert canonical_risk_from_legacy("FRAUDULENT") is RiskBand.HIGH
    assert legacy_risk_from_band(RiskBand.HIGH) == "FRAUDULENT"
    with pytest.raises(EvidenceContractError, match="unsupported legacy"):
        canonical_image_from_legacy("genuine")


def test_result_copy_avoids_certainty_language() -> None:
    prohibited = ("safe", "verified", "100%")
    for risk_band in RiskBand:
        mode = (
            EvidenceMode.INCONCLUSIVE
            if risk_band is RiskBand.INCONCLUSIVE
            else EvidenceMode.SCREENSHOT_ONLY
        )
        result = EvidenceResult(
            mode=mode,
            image=(
                _unavailable("evidence")
                if risk_band is RiskBand.INCONCLUSIVE
                else _available(label=ImageLabel.UNALTERED)
            ),
            ocr=_unavailable("evidence"),
            semantic=_unavailable("evidence"),
            transaction=_unavailable("evidence"),
            risk_band=risk_band,
            risk_score=None if risk_band is RiskBand.INCONCLUSIVE else 0.5,
            reason_codes=("COPY_POLICY_TEST",),
        )
        lowered = result.summary.lower()
        assert all(term not in lowered for term in prohibited)


def test_portable_schema_matches_runtime_enums() -> None:
    repository_root = Path(__file__).resolve().parents[4]
    schema = json.loads(
        (repository_root / "packages/evidence-contracts/evidence-result-v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    properties = schema["properties"]
    signal_properties = schema["$defs"]["signal"]["properties"]
    assert properties["contract_version"]["const"] == EVIDENCE_CONTRACT_VERSION
    assert properties["mode"]["enum"] == [member.value for member in EvidenceMode]
    assert properties["risk_band"]["enum"] == [member.value for member in RiskBand]
    assert signal_properties["state"]["enum"] == [member.value for member in SignalState]
    assert signal_properties["label"]["oneOf"][0]["enum"] == [member.value for member in ImageLabel]
