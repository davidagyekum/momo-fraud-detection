"""High-precision fraud assessment over OCR text from MoMo screenshots.

The module deliberately separates three concerns:

* OCR text availability/quality;
* deterministic scam-language signals; and
* the final screenshot risk policy, which may also use stored-reference status.

A policy score is not a probability. Raw OCR text, matched snippets, phone numbers,
links and secrets are never returned from the public projections.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Final, Literal, cast

TEXT_FRAUD_SCHEMA_VERSION: Final = "momo-text-fraud-assessment-v1"
LEGACY_TEXT_FRAUD_RULESET_VERSION: Final = "ghana-momo-obvious-scam-rules-v1"
TEXT_FRAUD_RULESET_VERSION: Final = "ghana-momo-obvious-scam-rules-v2"
_SUPPORTED_RULESET_VERSIONS: Final = {
    LEGACY_TEXT_FRAUD_RULESET_VERSION,
    TEXT_FRAUD_RULESET_VERSION,
}

Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
RiskClass = Literal["GENUINE", "SUSPICIOUS", "FRAUDULENT"]
AssessmentStatus = Literal["SUCCESS", "UNAVAILABLE"]
EvidenceQuality = Literal["HIGH", "MEDIUM", "LOW", "UNAVAILABLE"]

_SPACE = re.compile(r"\s+")
_GHANA_PHONE = re.compile(r"(?<!\d)(?:\+?233[\s().-]?|0)(?:2|5)\d(?:[\s().-]?\d){7}(?!\d)")
_INTERNATIONAL_PHONE = re.compile(r"(?<![\d.])\+\d(?:[\s().-]?\d){7,14}(?!\d)")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s]+", re.IGNORECASE)
_SHORT_LINK = re.compile(
    r"(?<![\w@])(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|ow\.ly|is\.gd|cutt\.ly|"
    r"rb\.gy|buff\.ly)/[a-z0-9_-]+\b",
    re.IGNORECASE,
)
_CLAUSE_BOUNDARY = re.compile(
    r"\s*(?:[.!?;:]+(?=\s|$)|,(?=\s)|"
    r"\b(?:but|however|yet|although|nevertheless|instead)\b)\s*",
    re.IGNORECASE,
)
_SAFE_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,79}")

# A second, OCR-tolerant form is used only for matching. It is never persisted.
_LEET_TRANSLATION = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
        "|": "i",
    }
)

_SECRET = re.compile(
    r"\b(?:p\s*i\s*n|o\s*t\s*p|one\s*time\s*password|security\s*code|"
    r"verification\s*code|activation\s*code|secret\s*code)\b",
    re.IGNORECASE,
)
_SECRET_DISCLOSURE_VERB = re.compile(
    r"\b(?:send|share|provide|reply|tell|forward|reveal|give)\b",
    re.IGNORECASE,
)
_ADVISORY = re.compile(
    r"\b(?:never|do\s+not|don['\u2019]?t|must\s+not|will\s+never|should\s+not)\s+"
    r"(?:ask\s+(?:you\s+)?(?:for|to\s+share)|share|send|provide|reveal|give)\b",
    re.IGNORECASE,
)

_WRONG_TRANSFER = re.compile(
    r"\b(?:wrong(?:ly)?\s+(?:sent|transfer(?:red)?)|"
    r"sent\s+(?:it|money|funds)?\s*(?:to\s+you\s*)?by\s+mistake|"
    r"mistaken(?:ly)?\s+(?:sent|transfer(?:red)?)|wrong\s+transaction|erroneous\s+transfer|"
    r"reverse\s+(?:the\s+)?(?:money|payment|transaction|transfer)|"
    r"reversal|refund)\b",
    re.IGNORECASE,
)
_MISTAKEN_TRANSFER_CLAIM = re.compile(
    r"\b(?:wrong(?:ly)?\s+(?:sent|transfer(?:red)?)|"
    r"sent\s+(?:it|money|funds)?\s*(?:to\s+you\s*)?by\s+mistake|"
    r"mistaken(?:ly)?\s+(?:sent|transfer(?:red)?)|wrong\s+transaction|"
    r"erroneous\s+transfer)\b",
    re.IGNORECASE,
)
_MONEY_RETURN_ACTION = re.compile(
    r"\b(?:send\s+(?:it|the\s+money|money|funds)?\s*back|"
    r"return\s+(?:it|the\s+money|money|funds)|"
    r"refund\s+(?:it|the\s+money|money|funds|"
    r"(?:ghs|ghc|gh[₵¢]|₵)\s*\d[\d,.]*)|"
    r"transfer\s+(?:it|the\s+money|money|funds)?\s*(?:to|back))\b",
    re.IGNORECASE,
)
_COMPLETED_REVERSAL = re.compile(
    r"\b(?:reversal|reverse(?:d)?|refund(?:ed)?)\b.{0,24}"
    r"\b(?:successful|completed|processed|done)\b",
    re.IGNORECASE,
)

_ACCOUNT_CONTEXT = re.compile(
    r"\b(?:momo|mobile\s*money|wallet|account|number|line|funds?)\b", re.IGNORECASE
)
_ACCOUNT_THREAT = re.compile(
    r"\b(?:block(?:ed)?|suspend(?:ed)?|frozen?|lock(?:ed)?|deactivat(?:e|ed|ion)|"
    r"restrict(?:ed)?|close(?:d)?|disable(?:d)?)\b",
    re.IGNORECASE,
)
_ACTION = re.compile(
    r"\b(?:call|contact|whatsapp|message|click|verify|update|reactivate|unlock|"
    r"send|pay|transfer|provide|submit|reply|confirm|login|log\s*in|claim)\b",
    re.IGNORECASE,
)
_ACCOUNT_EXTERNAL_ACTION = re.compile(
    r"\b(?:pay|send|transfer|provide|submit|reply|login|log\s*in|click)\b",
    re.IGNORECASE,
)

_PAY = re.compile(r"\b(?:pay|send|transfer|deposit)\b", re.IGNORECASE)
_FEE = re.compile(
    r"\b(?:fee|charge|processing\s*fee|activation\s*fee|clearance\s*fee|tax|deposit)\b",
    re.IGNORECASE,
)
_RELEASE = re.compile(
    r"\b(?:unlock|release|reverse|reactivate|restore|claim|receive|clear|unblock)\b",
    re.IGNORECASE,
)

_LINK_ACTION = re.compile(
    r"\b(?:verify|login|log\s*in|update|claim|reactivate|unlock|restore|confirm|reset)\b",
    re.IGNORECASE,
)
_LINK_CONTEXT = re.compile(
    r"\b(?:momo|mobile\s*money|wallet|account|payment|transaction)\b",
    re.IGNORECASE,
)

_CONTACT = re.compile(r"\b(?:call|contact|whatsapp|message|text|dial)\b", re.IGNORECASE)
_CONTACT_CONTEXT = re.compile(
    r"\b(?:momo|mobile\s*money|provider|customer\s*care|support|wallet|account|"
    r"transaction|transfer|refund|reversal|payment)\b",
    re.IGNORECASE,
)

_PRIZE = re.compile(
    r"\b(?:congratulations|winner|won|prize|reward|bonus|promotion|promo|cash\s*award|gift)\b",
    re.IGNORECASE,
)
_PRIZE_ACTION = re.compile(
    r"\b(?:claim|call|contact|click|visit|pay|send|reply|register|redeem)\b", re.IGNORECASE
)

_URGENCY = re.compile(
    r"\b(?:urgent|immediately|now|final\s+notice|last\s+warning|today\s+only|"
    r"within\s+\d+\s+(?:minute|minutes|hour|hours)|before\s+it\s+expires)\b",
    re.IGNORECASE,
)

_PROVIDER_CLAIM = re.compile(
    r"\b(?:mtn|telecel|vodafone|airteltigo|airtel\s*tigo|at\s*money|mobile\s*money|momo)\b",
    re.IGNORECASE,
)

_REASON_DETAILS: Final[dict[str, tuple[str, str, Severity]]] = {
    "PIN_OR_OTP_REQUEST": (
        "Secret code requested",
        (
            "The text asks the user to disclose a MoMo PIN, OTP or security code. "
            "Legitimate support should not request these secrets."
        ),
        "CRITICAL",
    ),
    "WRONG_TRANSFER_REFUND_LURE": (
        "Wrong-transfer or refund lure",
        (
            "The text claims money was sent by mistake or asks for a reversal/refund "
            "through an unverified route."
        ),
        "CRITICAL",
    ),
    "ACCOUNT_BLOCK_THREAT_WITH_ACTION": (
        "Account threat with demanded action",
        (
            "The text threatens that an account or wallet is blocked and directs the "
            "user to call, click, pay or submit details."
        ),
        "HIGH",
    ),
    "PAY_TO_UNLOCK_OR_RELEASE": (
        "Payment demanded to unlock funds",
        (
            "The text demands a fee, transfer or deposit to unlock, release, reverse "
            "or reactivate funds."
        ),
        "CRITICAL",
    ),
    "SUSPICIOUS_LINK_ACCOUNT_ACTION": (
        "Suspicious account-action link",
        (
            "The text includes a link and asks the user to verify, log in, update, "
            "claim or reactivate a MoMo account."
        ),
        "HIGH",
    ),
    "UNVERIFIED_CONTACT_REDIRECT": (
        "Redirected to an unverified contact",
        "The text redirects a transaction or account issue to a normal phone or WhatsApp number.",
        "HIGH",
    ),
    "PRIZE_OR_BONUS_LURE": (
        "Prize or bonus lure",
        (
            "The text announces a prize, reward or bonus and asks the user to claim "
            "it through another action."
        ),
        "HIGH",
    ),
    "URGENCY_PRESSURE": (
        "Urgency or pressure language",
        "The text pressures the user to act immediately or before a short deadline.",
        "MEDIUM",
    ),
    "UNOFFICIAL_SENDER_CONTEXT": (
        "Unofficial sender context",
        (
            "A message claiming to represent a provider came from a normal phone-number "
            "sender. This is supporting evidence only."
        ),
        "LOW",
    ),
}

_SEVERITY_ORDER: Final[dict[Severity, int]] = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

_PERSISTED_LIMITATIONS: Final = {
    "ABSENCE_OF_RULE_MATCH_IS_NOT_PROOF_OF_GENUINENESS",
    "OCR_CONFIDENCE_LOW",
    "OCR_TEXT_EMPTY",
    "OCR_TEXT_SHORT",
}


@dataclass(frozen=True)
class TextFraudContext:
    """Optional non-secret metadata that may corroborate OCR text."""

    sender_kind: str | None = None
    claimed_provider: str | None = None
    capture_channel: str | None = None


@dataclass(frozen=True)
class FraudReason:
    code: str
    title: str
    summary: str
    severity: Severity

    def as_public_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class TextFraudAssessment:
    schema_version: str
    ruleset_version: str
    status: AssessmentStatus
    risk_class: RiskClass | None
    risk_score: int | None
    reason_code: str
    reasons: tuple[FraudReason, ...]
    evidence_quality: EvidenceQuality
    limitations: tuple[str, ...]
    score_is_probability: bool = False

    @property
    def reason_codes(self) -> tuple[str, ...]:
        return tuple(reason.code for reason in self.reasons)

    def as_public_dict(self) -> dict[str, object]:
        """Return an allowlisted projection containing no OCR text or matched values."""

        return {
            "schema_version": self.schema_version,
            "ruleset_version": self.ruleset_version,
            "status": self.status,
            "class": self.risk_class,
            "score": self.risk_score,
            "score_is_probability": self.score_is_probability,
            "reason_code": self.reason_code,
            "reason_codes": sorted(self.reason_codes),
            "reasons": [reason.as_public_dict() for reason in self.reasons],
            "evidence_quality": self.evidence_quality,
            "limitations": list(self.limitations),
            "summary": _assessment_summary(self),
            "disclaimer": (
                "This is a rule-based risk assessment of the supplied screenshot text, not "
                "live confirmation from a mobile-network operator or a legal determination."
            ),
        }


def _normalize_text(raw_text: str) -> tuple[str, str]:
    canonical = unicodedata.normalize("NFKC", raw_text)
    canonical = "".join(
        character for character in canonical if unicodedata.category(character) != "Cf"
    )
    canonical = canonical.replace("\N{RIGHT SINGLE QUOTATION MARK}", "'").replace("`", "'")
    # OCR engines expose visual lines. Keep them as sentence boundaries so an
    # official advisory on one line cannot suppress a separate secret request.
    canonical = canonical.replace("\r\n", "\n").replace("\r", "\n")
    canonical = re.sub(r"\n+", " . ", canonical)
    canonical = _SPACE.sub(" ", canonical).strip().casefold()
    tolerant = canonical.translate(_LEET_TRANSLATION)
    tolerant = _SPACE.sub(" ", tolerant)
    return canonical, tolerant


def _bounded_clauses(text: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in _CLAUSE_BOUNDARY.split(text) if value.strip())


def _clause_windows(canonical: str, tolerant: str) -> tuple[tuple[str, str], ...]:
    clauses: list[tuple[str, str]] = []
    start = 0
    for boundary in _CLAUSE_BOUNDARY.finditer(tolerant):
        canonical_clause = canonical[start : boundary.start()].strip()
        tolerant_clause = tolerant[start : boundary.start()].strip()
        if canonical_clause and tolerant_clause:
            clauses.append((canonical_clause, tolerant_clause))
        start = boundary.end()
    canonical_clause = canonical[start:].strip()
    tolerant_clause = tolerant[start:].strip()
    if canonical_clause and tolerant_clause:
        clauses.append((canonical_clause, tolerant_clause))

    windows: list[tuple[str, str]] = []
    for index, (canonical_clause, tolerant_clause) in enumerate(clauses):
        windows.append((canonical_clause, tolerant_clause))
        if index + 1 < len(clauses):
            windows.append(
                (
                    f"{canonical_clause} . {clauses[index + 1][0]}",
                    f"{tolerant_clause} . {clauses[index + 1][1]}",
                )
            )
    return tuple(windows)


def _contains_secret_request(tolerant: str) -> bool:
    """Return true when at least one bounded clause requests a secret.

    Negation is evaluated per sentence/visual line. This avoids both common false
    positives ("never share your PIN") and a bypass where a malicious message puts
    an advisory sentence before a separate request.
    """

    for clause in _bounded_clauses(tolerant):
        if (
            _SECRET.search(clause)
            and _SECRET_DISCLOSURE_VERB.search(clause)
            and not _ADVISORY.search(clause)
        ):
            return True
    return False


def _has_phone(text: str) -> bool:
    return _GHANA_PHONE.search(text) is not None or _INTERNATIONAL_PHONE.search(text) is not None


def _has_explicit_link(text: str) -> bool:
    return _URL.search(text) is not None


def _has_account_action_link(canonical: str, tolerant: str) -> bool:
    return bool(
        (_has_explicit_link(canonical) or _SHORT_LINK.search(canonical))
        and _LINK_ACTION.search(tolerant)
        and _LINK_CONTEXT.search(tolerant)
    )


def _reason(code: str) -> FraudReason:
    title, summary, severity = _REASON_DETAILS[code]
    return FraudReason(code, title, summary, severity)


def _add_reason(codes: set[str], code: str) -> None:
    if code not in _REASON_DETAILS:
        raise ValueError("unknown fraud reason code")
    codes.add(code)


def _detect_reasons(
    canonical: str,
    tolerant: str,
    *,
    context: TextFraudContext,
) -> tuple[FraudReason, ...]:
    codes: set[str] = set()
    windows = _clause_windows(canonical, tolerant)

    if _contains_secret_request(tolerant):
        _add_reason(codes, "PIN_OR_OTP_REQUEST")

    wrong_transfer_lure = any(
        (
            _WRONG_TRANSFER.search(tolerant_window)
            and (
                _MONEY_RETURN_ACTION.search(canonical_window)
                or _MONEY_RETURN_ACTION.search(tolerant_window)
            )
            and not _COMPLETED_REVERSAL.search(tolerant_window)
        )
        or (
            _MISTAKEN_TRANSFER_CLAIM.search(tolerant_window)
            and _CONTACT.search(tolerant_window)
            and (_has_phone(canonical_window) or _has_explicit_link(canonical_window))
        )
        for canonical_window, tolerant_window in windows
    )
    if wrong_transfer_lure:
        _add_reason(codes, "WRONG_TRANSFER_REFUND_LURE")

    account_threat = any(
        _ACCOUNT_CONTEXT.search(tolerant_window)
        and _ACCOUNT_THREAT.search(tolerant_window)
        and (
            _ACCOUNT_EXTERNAL_ACTION.search(tolerant_window)
            or (_CONTACT.search(tolerant_window) and _has_phone(canonical_window))
            or _has_account_action_link(canonical_window, tolerant_window)
        )
        for canonical_window, tolerant_window in windows
    )
    if account_threat:
        _add_reason(codes, "ACCOUNT_BLOCK_THREAT_WITH_ACTION")

    if any(
        _PAY.search(tolerant_window)
        and _FEE.search(tolerant_window)
        and _RELEASE.search(tolerant_window)
        for _, tolerant_window in windows
    ):
        _add_reason(codes, "PAY_TO_UNLOCK_OR_RELEASE")

    if any(
        _has_account_action_link(canonical_window, tolerant_window)
        for canonical_window, tolerant_window in windows
    ):
        _add_reason(codes, "SUSPICIOUS_LINK_ACCOUNT_ACTION")

    if any(
        _has_phone(canonical_window)
        and _CONTACT.search(tolerant_window)
        and _CONTACT_CONTEXT.search(tolerant_window)
        for canonical_window, tolerant_window in windows
    ):
        _add_reason(codes, "UNVERIFIED_CONTACT_REDIRECT")

    if any(
        _PRIZE.search(tolerant_window) and _PRIZE_ACTION.search(tolerant_window)
        for _, tolerant_window in windows
    ):
        _add_reason(codes, "PRIZE_OR_BONUS_LURE")

    if any(
        _URGENCY.search(tolerant_window) and _ACTION.search(tolerant_window)
        for _, tolerant_window in windows
    ):
        _add_reason(codes, "URGENCY_PRESSURE")

    if (
        context.sender_kind == "phone_number"
        and context.claimed_provider
        and _PROVIDER_CLAIM.search(tolerant)
    ):
        _add_reason(codes, "UNOFFICIAL_SENDER_CONTEXT")

    return tuple(
        sorted(
            (_reason(code) for code in codes),
            key=lambda item: (-_SEVERITY_ORDER[item.severity], item.code),
        )
    )


def _quality(ocr_confidence: float | None, character_count: int) -> EvidenceQuality:
    if character_count == 0:
        return "UNAVAILABLE"
    confidence = 0.0 if ocr_confidence is None else max(0.0, min(1.0, ocr_confidence))
    if confidence >= 0.75 and character_count >= 20:
        return "HIGH"
    if confidence >= 0.4 and character_count >= 12:
        return "MEDIUM"
    return "LOW"


def _classify_v1(
    reasons: tuple[FraudReason, ...],
    *,
    evidence_quality: EvidenceQuality,
) -> tuple[RiskClass | None, int | None, str]:
    counts = {severity: 0 for severity in _SEVERITY_ORDER}
    for reason in reasons:
        counts[reason.severity] += 1

    if counts["CRITICAL"] >= 1:
        score = min(100, 94 + 2 * (counts["CRITICAL"] - 1) + counts["HIGH"])
        return "FRAUDULENT", score, "OBVIOUS_SCAM_TEXT_DETECTED"
    if counts["HIGH"] >= 2:
        return "FRAUDULENT", min(95, 86 + 3 * (counts["HIGH"] - 2)), "CORROBORATED_SCAM_TEXT"
    if counts["HIGH"] >= 1 and counts["MEDIUM"] >= 1:
        return "FRAUDULENT", 82, "CORROBORATED_SCAM_TEXT"
    if counts["HIGH"] >= 1:
        return "SUSPICIOUS", 70 if evidence_quality != "LOW" else 62, "HIGH_RISK_TEXT_SIGNAL"
    if counts["MEDIUM"] >= 2:
        return "SUSPICIOUS", 58, "MULTIPLE_SUSPICIOUS_TEXT_SIGNALS"
    if counts["MEDIUM"] == 1:
        return "SUSPICIOUS", 42, "SUSPICIOUS_TEXT_SIGNAL"
    return None, None, "NO_DECISIVE_TEXT_FRAUD_SIGNAL"


def _classify_v2(
    reasons: tuple[FraudReason, ...],
    *,
    evidence_quality: EvidenceQuality,
) -> tuple[RiskClass | None, int | None, str]:
    counts = {severity: 0 for severity in _SEVERITY_ORDER}
    for reason in reasons:
        counts[reason.severity] += 1

    if counts["CRITICAL"] >= 1:
        score = min(100, 94 + 2 * (counts["CRITICAL"] - 1) + counts["HIGH"])
        return "FRAUDULENT", score, "OBVIOUS_SCAM_TEXT_DETECTED"
    if counts["HIGH"] >= 2:
        return "FRAUDULENT", min(95, 86 + 3 * (counts["HIGH"] - 2)), "CORROBORATED_SCAM_TEXT"
    if counts["HIGH"] >= 1:
        return "SUSPICIOUS", 70 if evidence_quality != "LOW" else 62, "HIGH_RISK_TEXT_SIGNAL"
    if counts["MEDIUM"] >= 2:
        return "SUSPICIOUS", 58, "MULTIPLE_SUSPICIOUS_TEXT_SIGNALS"
    if counts["MEDIUM"] == 1:
        return "SUSPICIOUS", 42, "SUSPICIOUS_TEXT_SIGNAL"
    return None, None, "NO_DECISIVE_TEXT_FRAUD_SIGNAL"


def _classify_for_ruleset(
    ruleset_version: str,
    reasons: tuple[FraudReason, ...],
    *,
    evidence_quality: EvidenceQuality,
) -> tuple[RiskClass | None, int | None, str]:
    if ruleset_version == LEGACY_TEXT_FRAUD_RULESET_VERSION:
        return _classify_v1(reasons, evidence_quality=evidence_quality)
    return _classify_v2(reasons, evidence_quality=evidence_quality)


def _assessment_summary(result: TextFraudAssessment) -> str:
    if result.status == "UNAVAILABLE":
        return "The screenshot text could not be assessed."
    if result.risk_class == "FRAUDULENT":
        return (
            "The screenshot contains strong scam-language indicators and should be "
            "treated as high risk."
        )
    if result.risk_class == "SUSPICIOUS":
        return "The screenshot contains suspicious language that requires caution and verification."
    return (
        "No decisive scam-language rule was triggered; this does not prove that the "
        "transaction is genuine."
    )


def confidence_from_ocr_tokens(
    token_data: object,
    *,
    fallback: float | None = None,
) -> float:
    """Aggregate OCR token confidences accepting either 0..1 or 0..100 scales."""

    values: list[float] = []
    if isinstance(token_data, list):
        for token in token_data:
            if not isinstance(token, dict):
                continue
            raw = token.get("confidence")
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                continue
            value = float(raw)
            if value < 0:
                continue
            if value > 1:
                value /= 100.0
            values.append(max(0.0, min(1.0, value)))
    if values:
        return round(sum(values) / len(values), 4)
    return round(max(0.0, min(1.0, fallback or 0.0)), 4)


def assess_ocr_text(
    raw_text: str,
    *,
    ocr_confidence: float | None = None,
    context: TextFraudContext | None = None,
) -> TextFraudAssessment:
    """Assess OCR text for high-precision scam-language indicators.

    The function never returns the input text or matched spans. A critical rule may remain
    actionable even when OCR confidence is low because the combination itself is strong;
    the low-quality limitation remains explicit in the result.
    """

    canonical, tolerant = _normalize_text(raw_text)
    evidence_quality = _quality(ocr_confidence, len(canonical))
    if not canonical:
        return TextFraudAssessment(
            TEXT_FRAUD_SCHEMA_VERSION,
            TEXT_FRAUD_RULESET_VERSION,
            "UNAVAILABLE",
            None,
            None,
            "OCR_TEXT_UNAVAILABLE",
            (),
            "UNAVAILABLE",
            ("OCR_TEXT_EMPTY",),
        )

    reasons = _detect_reasons(canonical, tolerant, context=context or TextFraudContext())
    risk_class, score, reason_code = _classify_v2(reasons, evidence_quality=evidence_quality)
    limitations: list[str] = []
    if evidence_quality == "LOW":
        limitations.append("OCR_CONFIDENCE_LOW")
    if len(canonical) < 20:
        limitations.append("OCR_TEXT_SHORT")
    if risk_class is None:
        limitations.append("ABSENCE_OF_RULE_MATCH_IS_NOT_PROOF_OF_GENUINENESS")

    return TextFraudAssessment(
        TEXT_FRAUD_SCHEMA_VERSION,
        TEXT_FRAUD_RULESET_VERSION,
        "SUCCESS",
        risk_class,
        score,
        reason_code,
        reasons,
        evidence_quality,
        tuple(sorted(set(limitations))),
    )


def unavailable_text_assessment(
    reason_code: str = "OCR_TEXT_UNAVAILABLE",
    limitation: str = "OCR_TEXT_EMPTY",
) -> TextFraudAssessment:
    """Build a safe unavailable result for legacy or missing persisted evidence."""

    return TextFraudAssessment(
        TEXT_FRAUD_SCHEMA_VERSION,
        TEXT_FRAUD_RULESET_VERSION,
        "UNAVAILABLE",
        None,
        None,
        reason_code,
        (),
        "UNAVAILABLE",
        (limitation,),
    )


def stored_text_assessment(value: object) -> TextFraudAssessment:
    """Validate persisted evidence and reconstruct only fixed public reason text."""

    legacy = unavailable_text_assessment(
        "OCR_TEXT_ASSESSMENT_NOT_PERSISTED",
        "LEGACY_OCR_RESULT_WITHOUT_TEXT_ASSESSMENT",
    )
    if not isinstance(value, dict):
        return legacy
    status = value.get("status")
    risk_class = value.get("class")
    score = value.get("score")
    reason_code = value.get("reason_code")
    reason_codes = value.get("reason_codes")
    evidence_quality = value.get("evidence_quality")
    limitations = value.get("limitations")
    if (
        value.get("schema_version") != TEXT_FRAUD_SCHEMA_VERSION
        or value.get("ruleset_version") not in _SUPPORTED_RULESET_VERSIONS
        or value.get("score_is_probability") is not False
        or status not in {"SUCCESS", "UNAVAILABLE"}
        or risk_class not in {None, "SUSPICIOUS", "FRAUDULENT"}
        or (score is not None and (isinstance(score, bool) or not isinstance(score, int)))
        or (isinstance(score, int) and not 0 <= score <= 100)
        or not isinstance(reason_code, str)
        or _SAFE_CODE.fullmatch(reason_code) is None
        or not isinstance(reason_codes, list)
        or not isinstance(value.get("reasons"), list)
        or not isinstance(limitations, list)
        or evidence_quality not in {"HIGH", "MEDIUM", "LOW", "UNAVAILABLE"}
        or any(not isinstance(code, str) or code not in _REASON_DETAILS for code in reason_codes)
        or len(set(reason_codes)) != len(reason_codes)
        or any(not isinstance(limitation, str) for limitation in limitations)
        or not set(limitations).issubset(_PERSISTED_LIMITATIONS)
    ):
        return legacy
    reasons = tuple(
        sorted(
            (_reason(code) for code in reason_codes),
            key=lambda item: (-_SEVERITY_ORDER[item.severity], item.code),
        )
    )
    if status == "UNAVAILABLE":
        if (
            risk_class is not None
            or score is not None
            or reason_codes
            or evidence_quality != "UNAVAILABLE"
            or reason_code != "OCR_TEXT_UNAVAILABLE"
        ):
            return legacy
    else:
        expected_class, expected_score, expected_reason_code = _classify_for_ruleset(
            cast(str, value["ruleset_version"]),
            reasons,
            evidence_quality=cast(EvidenceQuality, evidence_quality),
        )
        if (risk_class, score, reason_code) != (
            expected_class,
            expected_score,
            expected_reason_code,
        ):
            return legacy
    return TextFraudAssessment(
        TEXT_FRAUD_SCHEMA_VERSION,
        cast(str, value["ruleset_version"]),
        cast(AssessmentStatus, status),
        cast(RiskClass | None, risk_class),
        score,
        reason_code,
        reasons,
        cast(EvidenceQuality, evidence_quality),
        tuple(cast(list[str], limitations)),
    )


def stored_text_assessment_projection(value: object) -> dict[str, object]:
    """Allowlist persisted assessment without recomputing historical OCR evidence."""

    return stored_text_assessment(value).as_public_dict()


__all__ = [
    "LEGACY_TEXT_FRAUD_RULESET_VERSION",
    "TEXT_FRAUD_RULESET_VERSION",
    "TEXT_FRAUD_SCHEMA_VERSION",
    "FraudReason",
    "TextFraudAssessment",
    "TextFraudContext",
    "assess_ocr_text",
    "confidence_from_ocr_tokens",
    "stored_text_assessment",
    "stored_text_assessment_projection",
    "unavailable_text_assessment",
]
