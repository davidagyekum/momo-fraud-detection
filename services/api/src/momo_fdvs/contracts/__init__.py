"""Versioned product contracts shared across evidence pipelines."""

from momo_fdvs.contracts.evidence import (
    EVIDENCE_CONTRACT_VERSION,
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

__all__ = [
    "EVIDENCE_CONTRACT_VERSION",
    "EvidenceMode",
    "EvidenceResult",
    "EvidenceSignal",
    "ImageLabel",
    "RiskBand",
    "SignalState",
    "canonical_image_from_legacy",
    "canonical_risk_from_legacy",
    "legacy_risk_from_band",
]
