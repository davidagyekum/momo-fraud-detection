"""Evidence-aware result contract and compatibility projections.

This module deliberately does not replace the existing public API or database enums. It is the
versioned internal contract that future orchestration can adopt while legacy projections remain
available during a separately migrated API/database/UI transition.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

EVIDENCE_CONTRACT_VERSION: Final = "evidence-result-v1"
_REASON_CODE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")


class EvidenceContractError(ValueError):
    """Raised when evidence violates the versioned availability contract."""


class EvidenceMode(StrEnum):
    """The evidence families supplied to one analysis."""

    SCREENSHOT_ONLY = "screenshot_only"
    TRANSACTION_ONLY = "transaction_only"
    COMBINED = "combined"
    INCONCLUSIVE = "inconclusive"


class SignalState(StrEnum):
    """Whether one evidence pipeline produced usable output."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ImageLabel(StrEnum):
    """Canonical manipulation label; it never asserts transaction authenticity."""

    UNALTERED = "unaltered"
    TAMPERED = "tampered"


class RiskBand(StrEnum):
    """Canonical policy band for the evidence supplied to an analysis."""

    LOW = "low_risk"
    MEDIUM = "medium_risk"
    HIGH = "high_risk"
    INCONCLUSIVE = "inconclusive"


def _validate_reason_codes(reason_codes: tuple[str, ...]) -> None:
    if not reason_codes:
        raise EvidenceContractError("at least one reason code is required")
    if len(set(reason_codes)) != len(reason_codes):
        raise EvidenceContractError("reason codes must be unique")
    if any(_REASON_CODE.fullmatch(code) is None for code in reason_codes):
        raise EvidenceContractError("reason codes must use canonical uppercase identifiers")


@dataclass(frozen=True)
class EvidenceSignal:
    """One nullable evidence-pipeline output."""

    state: SignalState
    score: float | None = None
    label: ImageLabel | None = None
    reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.state, SignalState):
            raise EvidenceContractError("signal state must be a SignalState")
        if self.label is not None and not isinstance(self.label, ImageLabel):
            raise EvidenceContractError("new image labels must be unaltered or tampered")
        if self.score is not None and (
            isinstance(self.score, bool)
            or not math.isfinite(self.score)
            or not 0 <= self.score <= 1
        ):
            raise EvidenceContractError("signal score must be null or a finite value in [0, 1]")
        if self.state is SignalState.UNAVAILABLE and (
            self.score is not None or self.label is not None
        ):
            raise EvidenceContractError("unavailable signals must keep score and label null")
        _validate_reason_codes(self.reason_codes)

    @classmethod
    def unavailable(cls, reason_code: str) -> EvidenceSignal:
        """Create an explicit unavailable signal without manufacturing a default value."""

        return cls(state=SignalState.UNAVAILABLE, reason_codes=(reason_code,))

    def as_dict(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "score": self.score,
            "label": self.label.value if self.label is not None else None,
            "reason_codes": list(self.reason_codes),
        }


_RESULT_SUMMARIES: Final = {
    RiskBand.LOW: (
        "No configured high-risk evidence was found in the supplied evidence. "
        "This is not provider verification."
    ),
    RiskBand.MEDIUM: (
        "Some configured risk indicators require caution and human review. "
        "This is not provider verification."
    ),
    RiskBand.HIGH: (
        "Configured high-risk evidence was detected and requires human review. "
        "This is not provider verification."
    ),
    RiskBand.INCONCLUSIVE: (
        "The supplied evidence was insufficient or unreadable. No authenticity conclusion was made."
    ),
}


@dataclass(frozen=True)
class EvidenceResult:
    """Versioned aggregate contract that keeps evidence families independent."""

    mode: EvidenceMode
    image: EvidenceSignal
    ocr: EvidenceSignal
    semantic: EvidenceSignal
    transaction: EvidenceSignal
    risk_band: RiskBand
    risk_score: float | None
    reason_codes: tuple[str, ...]
    contract_version: str = EVIDENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_version != EVIDENCE_CONTRACT_VERSION:
            raise EvidenceContractError("unsupported evidence contract version")
        if not isinstance(self.mode, EvidenceMode) or not isinstance(self.risk_band, RiskBand):
            raise EvidenceContractError("mode and risk band must use canonical enums")
        if any(
            not isinstance(signal, EvidenceSignal)
            for signal in (self.image, self.ocr, self.semantic, self.transaction)
        ):
            raise EvidenceContractError("all pipeline outputs must use EvidenceSignal")
        if any(signal.label is not None for signal in (self.ocr, self.semantic, self.transaction)):
            raise EvidenceContractError("only image evidence can carry an image label")
        if self.risk_score is not None and (
            isinstance(self.risk_score, bool)
            or not math.isfinite(self.risk_score)
            or not 0 <= self.risk_score <= 1
        ):
            raise EvidenceContractError("risk score must be null or a finite value in [0, 1]")
        _validate_reason_codes(self.reason_codes)
        if self.mode is EvidenceMode.SCREENSHOT_ONLY:
            self._require_unavailable(self.transaction, "transaction")
            if all(
                signal.state is SignalState.UNAVAILABLE
                for signal in (self.image, self.ocr, self.semantic)
            ):
                raise EvidenceContractError(
                    "screenshot-only mode requires screenshot-derived evidence"
                )
        elif self.mode is EvidenceMode.TRANSACTION_ONLY:
            self._require_unavailable(self.image, "image")
            self._require_unavailable(self.ocr, "ocr")
            self._require_unavailable(self.semantic, "semantic")
            if self.transaction.state is SignalState.UNAVAILABLE:
                raise EvidenceContractError("transaction-only mode requires transaction evidence")
        elif self.mode is EvidenceMode.COMBINED:
            if self.transaction.state is SignalState.UNAVAILABLE:
                raise EvidenceContractError("combined mode requires transaction evidence")
            if all(
                signal.state is SignalState.UNAVAILABLE
                for signal in (self.image, self.ocr, self.semantic)
            ):
                raise EvidenceContractError("combined mode requires screenshot-derived evidence")
        if self.mode is EvidenceMode.INCONCLUSIVE:
            if self.risk_band is not RiskBand.INCONCLUSIVE or self.risk_score is not None:
                raise EvidenceContractError("inconclusive mode requires null score and band")
        elif self.risk_band is RiskBand.INCONCLUSIVE and self.risk_score is not None:
            raise EvidenceContractError("inconclusive risk band must keep risk score null")
        elif self.risk_score is None:
            raise EvidenceContractError("a conclusive risk band requires a policy score")

    @staticmethod
    def _require_unavailable(signal: EvidenceSignal, name: str) -> None:
        if signal.state is not SignalState.UNAVAILABLE:
            raise EvidenceContractError(f"{name} evidence must be unavailable in this mode")

    @property
    def summary(self) -> str:
        return _RESULT_SUMMARIES[self.risk_band]

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "mode": self.mode.value,
            "image": self.image.as_dict(),
            "ocr": self.ocr.as_dict(),
            "semantic": self.semantic.as_dict(),
            "transaction": self.transaction.as_dict(),
            "risk_band": self.risk_band.value,
            "risk_score": self.risk_score,
            "reason_codes": list(self.reason_codes),
            "summary": self.summary,
        }


_LEGACY_IMAGE_TO_CANONICAL: Final = {
    "ORIGINAL": ImageLabel.UNALTERED,
    "CONTROLLED_TAMPERED": ImageLabel.TAMPERED,
}
_LEGACY_RISK_TO_CANONICAL: Final = {
    "GENUINE": RiskBand.LOW,
    "SUSPICIOUS": RiskBand.MEDIUM,
    "FRAUDULENT": RiskBand.HIGH,
}
_CANONICAL_RISK_TO_LEGACY: Final = {
    RiskBand.LOW: "GENUINE",
    RiskBand.MEDIUM: "SUSPICIOUS",
    RiskBand.HIGH: "FRAUDULENT",
    RiskBand.INCONCLUSIVE: None,
}


def canonical_image_from_legacy(value: str) -> ImageLabel:
    """Project one already-stored image class into the canonical manipulation taxonomy."""

    try:
        return _LEGACY_IMAGE_TO_CANONICAL[value]
    except KeyError as exc:
        raise EvidenceContractError("unsupported legacy image class") from exc


def canonical_risk_from_legacy(value: str) -> RiskBand:
    """Project one already-stored risk class without changing persisted records."""

    try:
        return _LEGACY_RISK_TO_CANONICAL[value]
    except KeyError as exc:
        raise EvidenceContractError("unsupported legacy risk class") from exc


def legacy_risk_from_band(value: RiskBand) -> str | None:
    """Provide the temporary old-API projection; inconclusive has no fabricated legacy class."""

    if not isinstance(value, RiskBand):
        raise EvidenceContractError("risk band must use the canonical enum")
    return _CANONICAL_RISK_TO_LEGACY[value]
