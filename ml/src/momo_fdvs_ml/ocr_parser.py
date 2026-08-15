"""Versioned Ghana MoMo OCR field parsing and deterministic semantic checks."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Final, Literal
from zoneinfo import ZoneInfo

OCR_PARSER_VERSION: Final = "ghana-momo-parser-v1"
OCR_FIELD_SCHEMA_VERSION: Final = "ghana-momo-ocr-fields-v1"
CRITICAL_FIELDS: Final = ("amount", "reference", "timestamp", "recipient")
FIELD_CONFIDENCE_THRESHOLD: Final = 0.65

_SPACE = re.compile(r"\s+")
_AMOUNT_TOKEN = r"(?:GHS|GHC|GH[₵¢]|₵)\s*([0-9][0-9, ]*(?:\.\d{1,2})?)(?![\d.])"  # noqa: S105
_REFERENCE_TOKEN = r"([A-Z0-9][A-Z0-9._/-]{4,49})"  # noqa: S105 - regex token, not a credential
_PHONE = re.compile(r"(?<!\d)(?:\+?233|0)?(?:2|5)\d(?:[\s-]?\d){7}(?!\d)")
_KNOWN_PROVIDERS: Final = {
    "MTN_MOMO": ("MTN", "MOBILEMONEY", "MOBILE MONEY", "MOMO"),
    "TELECEL_CASH": ("TELECEL", "VODAFONE CASH"),
    "AIRTELTIGO_MONEY": ("AIRTELTIGO", "AIRTEL TIGO", "AT MONEY"),
}


@dataclass(frozen=True)
class ParsedField:
    """One field with raw evidence, conservative normalization and warnings."""

    raw: str | None
    normalized: str | None
    confidence: float
    available: bool
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ParserResult:
    """Parser output suitable for a versioned OCR/parser bundle."""

    parser_version: str
    field_schema_version: str
    provider: ParsedField
    template_family: str
    fields: dict[str, ParsedField]
    semantic_reason_codes: tuple[str, ...]
    inconclusive: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "parser_version": self.parser_version,
            "field_schema_version": self.field_schema_version,
            "provider": self.provider.as_dict(),
            "template_family": self.template_family,
            "fields": {name: field.as_dict() for name, field in sorted(self.fields.items())},
            "semantic_reason_codes": list(self.semantic_reason_codes),
            "inconclusive": self.inconclusive,
        }


def _clean(value: str) -> str:
    return _SPACE.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def _confidence(base: float, engine_confidence: float | None) -> float:
    if engine_confidence is None:
        return round(base, 4)
    return round(max(0.0, min(1.0, 0.65 * base + 0.35 * engine_confidence)), 4)


def _unavailable(*warnings: str) -> ParsedField:
    return ParsedField(None, None, 0.0, False, tuple(warnings or ("FIELD_NOT_FOUND",)))


def _first(patterns: tuple[str, ...], text: str, *, flags: int = re.IGNORECASE) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return _clean(match.group(1))
    return None


def detect_provider(text: str, engine_confidence: float | None = None) -> ParsedField:
    """Return an explicit unknown provider when anchors are insufficient."""

    upper = _clean(text).upper()
    matches: dict[str, tuple[str, ...]] = {
        provider: tuple(anchor for anchor in anchors if anchor in upper)
        for provider, anchors in _KNOWN_PROVIDERS.items()
    }
    ordered = sorted(matches.items(), key=lambda item: (-len(item[1]), item[0]))
    if not ordered or not ordered[0][1]:
        return ParsedField(
            None,
            "UNKNOWN",
            _confidence(0.3, engine_confidence),
            True,
            ("TEMPLATE_UNKNOWN",),
        )
    provider, anchors = ordered[0]
    if len([candidate for candidate in ordered if candidate[1]]) > 1:
        return ParsedField(
            " / ".join(anchors),
            "UNKNOWN",
            _confidence(0.35, engine_confidence),
            True,
            ("PROVIDER_ANCHORS_CONFLICT", "TEMPLATE_UNKNOWN"),
        )
    return ParsedField(
        " / ".join(anchors),
        provider,
        _confidence(min(0.96, 0.7 + 0.08 * len(anchors)), engine_confidence),
        True,
    )


def _normalize_amount(raw: str) -> str | None:
    token = raw.replace(" ", "").replace(",", "")
    try:
        amount = Decimal(token)
    except (InvalidOperation, ValueError):
        return None
    if amount < 0 or amount > Decimal("999999999.99"):
        return None
    raw_exponent = amount.as_tuple().exponent
    if not isinstance(raw_exponent, int) or -raw_exponent > 2:
        return None
    return f"{amount.quantize(Decimal('0.01')):.2f}"


@dataclass(frozen=True)
class AmountCandidateSnapshot:
    labelled_raw_candidates: tuple[str, ...]
    labelled_valid_normalized: tuple[str, ...]
    labelled_distinct_normalized: tuple[str, ...]
    currency_raw_candidates: tuple[str, ...]
    currency_valid_normalized: tuple[str, ...]
    currency_distinct_normalized: tuple[str, ...]
    active_source: Literal["labelled", "currency_fallback"]
    active_valid_normalized: tuple[str, ...]
    active_distinct_normalized: tuple[str, ...]


def _ordered_distinct(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _amount_candidate_snapshot(text: str) -> AmountCandidateSnapshot:
    labelled_patterns = (
        rf"(?:amount|total|paid|payment|cash\s*in|cash\s*out|transferred|sent|received)"
        rf"[^\n]{{0,36}}?{_AMOUNT_TOKEN}",
        rf"{_AMOUNT_TOKEN}[^\n]{{0,24}}?(?:paid|sent|received|transferred)",
    )
    labelled_raw = tuple(
        _clean(match.group(1))
        for pattern in labelled_patterns
        for match in re.finditer(pattern, text, re.IGNORECASE)
    )
    currency_raw = tuple(
        _clean(match.group(1)) for match in re.finditer(_AMOUNT_TOKEN, text, re.IGNORECASE)
    )
    labelled_valid = tuple(
        normalized
        for raw in labelled_raw
        if (normalized := _normalize_amount(raw)) is not None
    )
    currency_valid = tuple(
        normalized
        for raw in currency_raw
        if (normalized := _normalize_amount(raw)) is not None
    )
    active_source: Literal["labelled", "currency_fallback"] = (
        "labelled" if labelled_raw else "currency_fallback"
    )
    active_valid = labelled_valid if labelled_raw else currency_valid
    return AmountCandidateSnapshot(
        labelled_raw,
        labelled_valid,
        _ordered_distinct(labelled_valid),
        currency_raw,
        currency_valid,
        _ordered_distinct(currency_valid),
        active_source,
        active_valid,
        _ordered_distinct(active_valid),
    )


def parse_amount(text: str, engine_confidence: float | None = None) -> ParsedField:
    """Prefer transaction-labelled GHS values and reject unresolved ambiguity."""

    snapshot = _amount_candidate_snapshot(text)
    active_raw = (
        snapshot.labelled_raw_candidates
        if snapshot.active_source == "labelled"
        else snapshot.currency_raw_candidates
    )
    valid = tuple(
        (raw, normalized)
        for raw in active_raw
        if (normalized := _normalize_amount(raw)) is not None
    )
    if not valid:
        return _unavailable("AMOUNT_NOT_FOUND")
    if len(snapshot.active_distinct_normalized) > 1:
        return ParsedField(
            " | ".join(raw for raw, _ in valid),
            None,
            _confidence(0.25, engine_confidence),
            False,
            ("AMOUNT_AMBIGUOUS",),
        )
    raw, value = valid[0]
    return ParsedField(
        raw,
        value,
        _confidence(0.92 if snapshot.active_source == "labelled" else 0.72, engine_confidence),
        True,
    )


def parse_reference(text: str, engine_confidence: float | None = None) -> ParsedField:
    raw = _first(
        (
            rf"(?:transaction\s*(?:id|reference|ref)|reference|ref\b|receipt\s*id)"
            rf"\s*(?:is\s*)?(?:[:#=-]\s*|\s+){_REFERENCE_TOKEN}",
        ),
        text,
    )
    if raw is None:
        return _unavailable("REFERENCE_NOT_FOUND")
    normalized = _SPACE.sub("", raw).upper()
    if re.fullmatch(r"[A-Z0-9][A-Z0-9._/-]{4,49}", normalized) is None:
        return ParsedField(raw, None, 0.2, False, ("REFERENCE_FORMAT_INVALID",))
    warnings: list[str] = []
    base = 0.92
    if re.search(r"(?=.*[0-9])(?=.*[OI])[A-Z0-9._/-]+", normalized):
        warnings.append("REFERENCE_OI_AMBIGUITY_PRESERVED")
        base = 0.58
    return ParsedField(raw, normalized, _confidence(base, engine_confidence), True, tuple(warnings))


def _normalize_phone(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 12 and digits.startswith("233"):
        return f"+{digits}"
    if len(digits) == 10 and digits.startswith("0"):
        return f"+233{digits[1:]}"
    if len(digits) == 9 and digits.startswith(("2", "5")):
        return f"+233{digits}"
    return None


def parse_recipient(text: str, engine_confidence: float | None = None) -> ParsedField:
    raw = _first(
        (
            r"(?:recipient|receiver|beneficiary)(?:\s*name)?\s*[:#=-]\s*([^\n]{2,100})",
            r"(?:payment\s+made|sent|transferred|cash\s*out)[^\n]{0,20}?\bto\s+([^\n]{2,100})",
            r"(?:payment\s+received|received|cash\s*in)[^\n]{0,20}?\bfrom\s+([^\n]{2,100})",
        ),
        text,
    )
    if raw is None:
        return _unavailable("RECIPIENT_NOT_FOUND")
    raw = re.split(
        r"\s+(?:on|at|ref(?:erence)?|transaction\s*id)\b",
        raw,
        maxsplit=1,
        flags=re.I,
    )[0]
    normalized = _clean(raw).strip(" .,:;-").upper()
    if not normalized or len(normalized) > 100:
        return ParsedField(raw, None, 0.2, False, ("RECIPIENT_FORMAT_INVALID",))
    return ParsedField(raw, normalized, _confidence(0.82, engine_confidence), True)


def parse_wallet(text: str, engine_confidence: float | None = None) -> ParsedField:
    labelled = _first(
        (
            r"(?:recipient|receiver|beneficiary|wallet|account)(?:\s*(?:number|phone|msisdn))?"
            r"\s*[:#=-]\s*([+0-9][0-9 ()-]{7,20})",
        ),
        text,
    )
    raw = labelled
    if raw is None:
        matches = _PHONE.findall(text)
        raw = _clean(matches[0]) if len(matches) == 1 else None
        if len(matches) > 1:
            return ParsedField(
                " | ".join(_clean(value) for value in matches),
                None,
                _confidence(0.25, engine_confidence),
                False,
                ("WALLET_AMBIGUOUS",),
            )
    if raw is None:
        return _unavailable("WALLET_NOT_FOUND")
    normalized = _normalize_phone(raw)
    if normalized is None:
        return ParsedField(raw, None, 0.2, False, ("WALLET_FORMAT_INVALID",))
    return ParsedField(
        raw,
        normalized,
        _confidence(0.9 if labelled else 0.68, engine_confidence),
        True,
    )


_TIMESTAMP_FORMATS: Final = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d/%m/%y %H:%M",
    "%d-%m-%y %H:%M",
)


def parse_timestamp(text: str, engine_confidence: float | None = None) -> ParsedField:
    raw = _first(
        (
            r"(?:date\s*/?\s*time|date|time|on|at)\s*[:#=-]?\s*"
            r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)",
            r"(?:date\s*/?\s*time|date|time|on|at)\s*[:#=-]?\s*"
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s+(?:at\s+)?\d{1,2}:\d{2}(?::\d{2})?)",
        ),
        text,
    )
    if raw is None:
        return _unavailable("TIMESTAMP_NOT_FOUND")
    candidate = raw.replace(" at ", " ").replace("T", " ").removesuffix("Z")
    warnings: list[str] = []
    slash_match = re.match(r"(\d{1,2})[/-](\d{1,2})[/-]", candidate)
    if slash_match and int(slash_match.group(1)) <= 12 and int(slash_match.group(2)) <= 12:
        warnings.append("DATE_ORDER_AMBIGUOUS_DAY_FIRST_USED")
    parsed: datetime | None = None
    for date_format in _TIMESTAMP_FORMATS:
        try:
            parsed = datetime.strptime(candidate, date_format)
            break
        except ValueError:
            continue
    if parsed is None:
        return ParsedField(raw, None, 0.2, False, ("TIMESTAMP_FORMAT_INVALID",))
    parsed = parsed.replace(tzinfo=ZoneInfo("Africa/Accra")).astimezone(UTC)
    base = 0.62 if warnings else 0.9
    return ParsedField(
        raw,
        parsed.isoformat().replace("+00:00", "Z"),
        _confidence(base, engine_confidence),
        True,
        tuple(warnings),
    )


def parse_status(text: str, engine_confidence: float | None = None) -> ParsedField:
    mapping = {
        "successful": "successful",
        "success": "successful",
        "completed": "successful",
        "failed": "failed",
        "reversed": "reversed",
        "reversal": "reversed",
        "pending": "pending",
    }
    matches = {
        mapping[match.group(1).casefold()]
        for match in re.finditer(
            r"\b(successful|success|completed|failed|reversed|reversal|pending)\b",
            text,
            re.I,
        )
    }
    if not matches:
        return ParsedField(
            None,
            "unknown",
            _confidence(0.35, engine_confidence),
            True,
            ("STATUS_UNKNOWN",),
        )
    if len(matches) > 1:
        return ParsedField(
            " / ".join(sorted(matches)),
            "unknown",
            _confidence(0.25, engine_confidence),
            True,
            ("STATUS_CONFLICT",),
        )
    status = next(iter(matches))
    return ParsedField(status, status, _confidence(0.9, engine_confidence), True)


def _semantic_reasons(
    *,
    text: str,
    provider: ParsedField,
    fields: dict[str, ParsedField],
    now: datetime,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if provider.normalized == "UNKNOWN":
        reasons.append("TEMPLATE_UNKNOWN")
    status = fields["status"]
    if status.normalized == "unknown":
        reasons.append("STATUS_UNKNOWN")
    timestamp = fields["timestamp"]
    if timestamp.normalized:
        parsed = datetime.fromisoformat(timestamp.normalized.replace("Z", "+00:00"))
        if parsed > now.astimezone(UTC) + timedelta(minutes=5):
            reasons.append("TIMESTAMP_IN_FUTURE")
    amounts = {
        value
        for value in (
            _normalize_amount(match.group(1))
            for match in re.finditer(_AMOUNT_TOKEN, text, re.IGNORECASE)
        )
        if value is not None
    }
    if len(amounts) > 1:
        reasons.append("MULTIPLE_DISTINCT_AMOUNTS")
    upper = text.upper()
    provider_mentions = [
        name for name, anchors in _KNOWN_PROVIDERS.items() if any(a in upper for a in anchors)
    ]
    if len(provider_mentions) > 1:
        reasons.append("PROVIDER_BODY_CONFLICT")
    return tuple(dict.fromkeys(reasons))


def parse_momo_text(
    text: str,
    *,
    engine_confidence: float | None = None,
    now: datetime | None = None,
) -> ParserResult:
    """Parse OCR text without silently correcting evidence or inventing missing values."""

    cleaned = unicodedata.normalize("NFKC", text)
    provider = detect_provider(cleaned, engine_confidence)
    fields = {
        "amount": parse_amount(cleaned, engine_confidence),
        "reference": parse_reference(cleaned, engine_confidence),
        "recipient": parse_recipient(cleaned, engine_confidence),
        "recipient_wallet": parse_wallet(cleaned, engine_confidence),
        "timestamp": parse_timestamp(cleaned, engine_confidence),
        "status": parse_status(cleaned, engine_confidence),
    }
    effective_now = now or datetime.now(UTC)
    if effective_now.tzinfo is None:
        raise ValueError("semantic test clock must be timezone-aware")
    reasons = _semantic_reasons(text=cleaned, provider=provider, fields=fields, now=effective_now)
    critical = [fields[name] for name in CRITICAL_FIELDS]
    inconclusive = any(
        not field.available
        or field.normalized is None
        or field.confidence < FIELD_CONFIDENCE_THRESHOLD
        for field in critical
    )
    provider_name = provider.normalized
    template = (
        f"{provider_name.lower()}_transaction"
        if provider_name is not None and provider_name != "UNKNOWN"
        else "unknown"
    )
    return ParserResult(
        OCR_PARSER_VERSION,
        OCR_FIELD_SCHEMA_VERSION,
        provider,
        template,
        fields,
        reasons,
        inconclusive,
    )


def redacted_log_summary(result: ParserResult) -> dict[str, object]:
    """Return only availability/confidence metadata; never raw OCR or field values."""

    return {
        "parser_version": result.parser_version,
        "template_family": result.template_family,
        "provider_available": result.provider.normalized not in {None, "UNKNOWN"},
        "field_availability": {
            name: field.available and field.normalized is not None
            for name, field in sorted(result.fields.items())
        },
        "field_confidence": {
            name: field.confidence for name, field in sorted(result.fields.items())
        },
        "reason_codes": list(result.semantic_reason_codes),
        "inconclusive": result.inconclusive,
    }
