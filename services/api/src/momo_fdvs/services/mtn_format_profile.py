"""Hash-bound matching against the privacy-safe MTN message-format profile."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from importlib import resources
from typing import Final, Literal, cast

PROFILE_SCHEMA_VERSION: Final = "mtn-genuine-format-profile-v1"
PROFILE_BUILDER_VERSION: Final = "mtn-format-profiler-v1"
MTN_FORMAT_PROFILE_SHA256: Final = (
    "dd2671cfaa44ab59a79ed5828dff6ef7f1fc6d17355110b67695fd7a378347d8"
)
_PROFILE_FILENAME: Final = "mtn_genuine_format_profile_v1.json"

MessageFamily = Literal[
    "CASH_IN",
    "CASH_OUT",
    "PAYMENT_MADE",
    "PAYMENT_RECEIVED",
    "PAYMENT_FOR",
    "YOUR_PAYMENT",
    "AIRTIME",
    "REVERSAL",
    "BALANCE_OR_STATEMENT",
    "MARKETING",
    "SECURITY_OR_OTP",
    "OTHER",
]

_PROFILE_FAMILIES: Final = frozenset(
    {
        "CASH_IN",
        "CASH_OUT",
        "PAYMENT_MADE",
        "PAYMENT_RECEIVED",
        "PAYMENT_FOR",
        "YOUR_PAYMENT",
        "AIRTIME",
        "REVERSAL",
    }
)
_ALLOWED_FEATURES: Final = frozenset(
    {
        "cash_in",
        "cash_in_received_for",
        "cash_out",
        "cash_out_made_for",
        "payment_made_for",
        "payment_received_for",
        "payment_for",
        "your_payment_of",
        "airtime",
        "reversal",
        "from_marker",
        "to_marker",
        "current_balance",
        "available_balance",
        "new_balance",
        "reference_label",
        "ref_label",
        "transaction_id",
        "financial_transaction_id",
        "external_transaction_id",
        "fee_charged",
        "transaction_fee",
        "fee_was",
        "tax_charged",
        "cash_in_free_disclaimer",
        "cash_out_fee_disclaimer",
        "momo_app_link",
        "mtn_mobilemoney",
        "successful",
        "money_count_0",
        "money_count_1",
        "money_count_2",
        "money_count_3_plus",
        "fee_precision_none",
        "fee_precision_0",
        "fee_precision_1",
        "fee_precision_2",
        "fee_precision_3_plus",
    }
)
_ALLOWED_ANOMALY_CODES: Final = frozenset(
    {
        "bare_id_label",
        "nonstandard_gh_marker",
        "dot_joined_balance",
        "three_plus_decimal_fee",
        "current_balance_misspelled",
        "available_balance_misspelled",
    }
)
_ALLOWED_ORDER_CODES: Final = frozenset(
    {
        "cash_in",
        "cash_out",
        "payment",
        "money",
        "from",
        "to",
        "current_balance",
        "available_balance",
        "new_balance",
        "reference",
        "transaction_id",
        "financial_transaction_id",
        "external_transaction_id",
        "fee",
        "tax",
    }
)
_SHA256: Final = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE_ID: Final = re.compile(r"^[0-9a-f]{20}$")
_MONEY: Final = re.compile(r"(?i)(?:GHS|GHC|GH[₵¢]|₵)\s*\d[\d,]*(?:\.\d+)?")
_SECRET: Final = re.compile(
    r"(?i)\b(?:OTP|one[- ]time\s+password|security\s+code|verification\s+code|"
    r"activation\s+code|login\s+code|password|PIN)\b"
)
_MARKETING: Final = re.compile(
    r"(?i)\b(?:upgrade|promo|promotion|offer|bonus|reward|zero\s+fee|zero\s+charg|"
    r"download\s+momo|momoapp|y['"
    "\u2019"
    r"]?ello\s+valued\s+customer)\b"
)
_BALANCE: Final = re.compile(r"(?i)\bbalance\b")

_FEATURE_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "cash_in_received_for": re.compile(r"\bcash\s+in\s+received\s+for\b", re.I),
    "cash_in": re.compile(r"\bcash\s+in\b", re.I),
    "cash_out_made_for": re.compile(r"\bcash\s+out\s+made\s+for\b", re.I),
    "cash_out": re.compile(r"\bcash\s+out\b", re.I),
    "payment_made_for": re.compile(r"\bpayment\s+made\s+for\b", re.I),
    "payment_received_for": re.compile(r"\bpayment\s+received\s+for\b", re.I),
    "payment_for": re.compile(r"\bpayment\s+for\b", re.I),
    "your_payment_of": re.compile(r"\byour\s+payment\s+of\b", re.I),
    "airtime": re.compile(r"\b(?:airtime|recharge)\b", re.I),
    "reversal": re.compile(r"\b(?:reversal|reversed|refund(?:ed)?)\b", re.I),
    "from_marker": re.compile(r"\bfrom\b", re.I),
    "to_marker": re.compile(r"\bto\b", re.I),
    "current_balance": re.compile(r"\bcurrent\s+balance\b", re.I),
    "available_balance": re.compile(r"\bavailable\s+balance\b", re.I),
    "new_balance": re.compile(r"\bnew\s+balance\b", re.I),
    "reference_label": re.compile(r"\breference\s*:", re.I),
    "ref_label": re.compile(r"\bref\s*:", re.I),
    "transaction_id": re.compile(r"\btransaction\s+id\s*:", re.I),
    "financial_transaction_id": re.compile(r"\bfinancial\s+transaction\s+id\s*:", re.I),
    "external_transaction_id": re.compile(r"\bexternal\s+transaction\s+id\s*:", re.I),
    "fee_charged": re.compile(r"\bfee\s+charged\s*:", re.I),
    "transaction_fee": re.compile(r"\btransaction\s+fee\s*:", re.I),
    "fee_was": re.compile(r"\bfee\s+was\b", re.I),
    "tax_charged": re.compile(r"\btax\s+charged\s*:", re.I),
    "cash_in_free_disclaimer": re.compile(
        r"\bcash\s+in\s*\(deposit\)\s+is\s+a\s+free\s+transaction\b", re.I
    ),
    "cash_out_fee_disclaimer": re.compile(
        r"\bcash[- ]out\s+fee\s+is\s+charged\s+automatically\b", re.I
    ),
    "momo_app_link": re.compile(r"\b(?:download\s+the\s+momo\s+app|momoapp)\b", re.I),
    "mtn_mobilemoney": re.compile(r"\bmtn\s+mobile\s*money\b|\bmtn\s+mobilemoney\b", re.I),
    "successful": re.compile(r"\bsuccessful(?:ly)?\b", re.I),
}
_ANOMALY_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "bare_id_label": re.compile(r"(?i)(?<!transaction\s)(?<!financial\s)(?<!external\s)\bid\s*:"),
    "nonstandard_gh_marker": re.compile(r"(?i)\bgh\s+\d"),
    "dot_joined_balance": re.compile(r"(?i)\b(?:balance|bulance|balanse)\.\d"),
    "three_plus_decimal_fee": re.compile(r"(?i)\bfee\s*:?[^\d]{0,8}\d+(?:\.\d{3,})\b"),
    "current_balance_misspelled": re.compile(
        r"(?i)\b(?:carent|curent|currant)\s+(?:bulance|balance|balanse)\b"
    ),
    "available_balance_misspelled": re.compile(
        r"(?i)\b(?:(?:avelabil|availabil|availble)\s+(?:balance|bulance|balanse)|"
        r"available\s+(?:bulance|balanse))\b"
    ),
}
_FEE_VALUE: Final = re.compile(
    r"(?i)(?:fee(?:\s+charged|\s+was)?|transaction\s+fee)\s*:\s*"
    r"(?:GHS\s*)?([0-9][\d,]*(?:\.\d+)?)"
)
_ANCHOR_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("cash_in", _FEATURE_PATTERNS["cash_in"]),
    ("cash_out", _FEATURE_PATTERNS["cash_out"]),
    ("payment", re.compile(r"\bpayment\b", re.I)),
    ("money", _MONEY),
    ("from", _FEATURE_PATTERNS["from_marker"]),
    ("to", _FEATURE_PATTERNS["to_marker"]),
    ("current_balance", _FEATURE_PATTERNS["current_balance"]),
    ("available_balance", _FEATURE_PATTERNS["available_balance"]),
    ("new_balance", _FEATURE_PATTERNS["new_balance"]),
    ("reference", re.compile(r"\b(?:reference|ref)\s*:", re.I)),
    ("transaction_id", _FEATURE_PATTERNS["transaction_id"]),
    ("financial_transaction_id", _FEATURE_PATTERNS["financial_transaction_id"]),
    ("external_transaction_id", _FEATURE_PATTERNS["external_transaction_id"]),
    ("fee", re.compile(r"\b(?:fee\s+charged|transaction\s+fee|fee\s+was)\b", re.I)),
    ("tax", _FEATURE_PATTERNS["tax_charged"]),
)


class MtnFormatProfileError(ValueError):
    """Safe format-profile failure with a stable, non-sensitive code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StructuralSignature:
    family: MessageFamily
    feature_codes: tuple[str, ...]
    anchor_order: tuple[str, ...]
    anomaly_codes: tuple[str, ...]


@dataclass(frozen=True)
class SignatureProfile:
    signature_id: str
    count: int
    feature_codes: tuple[str, ...]
    anchor_order: tuple[str, ...]


@dataclass(frozen=True)
class FamilyProfile:
    family: MessageFamily
    record_count: int
    required_features: tuple[str, ...]
    common_features: tuple[str, ...]
    signatures: tuple[SignatureProfile, ...]
    similarity_threshold: float


@dataclass(frozen=True)
class FormatMatch:
    status: str
    family: MessageFamily
    similarity: float | None
    threshold: float | None
    anomalous: bool | None
    closest_signature_id: str | None
    required_features_missing: tuple[str, ...]
    explicit_anomaly_codes: tuple[str, ...]
    profile_version: str | None
    profile_sha256: str | None

    def as_public_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "family": self.family,
            "similarity_band": (
                "high"
                if self.similarity is not None
                and self.threshold is not None
                and self.similarity >= self.threshold
                else "low"
                if self.similarity is not None
                else "unavailable"
            ),
            "threshold": round(self.threshold, 4) if self.threshold is not None else None,
            "anomalous": self.anomalous,
            "required_feature_count_missing": len(self.required_features_missing),
            "explicit_anomaly_codes": list(self.explicit_anomaly_codes),
            "profile_version": self.profile_version,
            "profile_sha256": self.profile_sha256,
        }


class LoadedMtnFormatProfile:
    """Strict, in-memory representation of the reviewed safe artifact."""

    def __init__(
        self,
        *,
        family_profiles: Mapping[MessageFamily, FamilyProfile],
        profile_sha256: str,
        raw_bytes: bytes,
    ) -> None:
        self.schema_version = PROFILE_SCHEMA_VERSION
        self.provider = "MTN_MOMO"
        self.family_profiles = dict(family_profiles)
        self.profile_sha256 = profile_sha256
        self.raw_bytes = raw_bytes

    def match_text(self, text: str) -> FormatMatch:
        return self.match_signature(extract_structural_signature(text))

    def match_signature(self, signature: StructuralSignature) -> FormatMatch:
        family_profile = self.family_profiles.get(signature.family)
        if family_profile is None:
            return FormatMatch(
                "UNAVAILABLE",
                signature.family,
                None,
                None,
                None,
                None,
                (),
                signature.anomaly_codes,
                self.schema_version,
                self.profile_sha256,
            )
        scored = [
            (
                structural_similarity(
                    signature.feature_codes,
                    signature.anchor_order,
                    candidate,
                ),
                candidate.signature_id,
            )
            for candidate in family_profile.signatures
        ]
        similarity, closest = max(scored, key=lambda item: (item[0], item[1]))
        missing = tuple(
            sorted(set(family_profile.required_features) - set(signature.feature_codes))
        )
        return FormatMatch(
            "AVAILABLE",
            signature.family,
            similarity,
            family_profile.similarity_threshold,
            similarity < family_profile.similarity_threshold,
            closest,
            missing,
            signature.anomaly_codes,
            self.schema_version,
            self.profile_sha256,
        )


def _schema_error(message: str) -> MtnFormatProfileError:
    return MtnFormatProfileError("PROFILE_SCHEMA_INVALID", message)


def _string_tuple(value: object, label: str, allowed: frozenset[str]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise _schema_error(f"{label} must be a string list")
    if len(set(value)) != len(value) or not set(value).issubset(allowed):
        raise _schema_error(f"{label} contains invalid codes")
    return tuple(value)


def _parse_signature(value: object) -> SignatureProfile:
    if not isinstance(value, dict) or set(value) != {
        "signature_id",
        "count",
        "feature_codes",
        "anchor_order",
    }:
        raise _schema_error("signature profile keys are invalid")
    signature_id = value["signature_id"]
    count = value["count"]
    if not isinstance(signature_id, str) or _SIGNATURE_ID.fullmatch(signature_id) is None:
        raise _schema_error("signature identity is invalid")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise _schema_error("signature count is invalid")
    return SignatureProfile(
        signature_id,
        count,
        _string_tuple(value["feature_codes"], "feature_codes", _ALLOWED_FEATURES),
        _string_tuple(value["anchor_order"], "anchor_order", _ALLOWED_ORDER_CODES),
    )


def _parse_family(value: object) -> FamilyProfile:
    expected = {
        "family",
        "record_count",
        "signature_count",
        "required_features",
        "common_features",
        "signatures",
        "similarity_threshold",
    }
    if not isinstance(value, dict) or set(value) != expected:
        raise _schema_error("family profile keys are invalid")
    family = value["family"]
    record_count = value["record_count"]
    signature_count = value["signature_count"]
    threshold = value["similarity_threshold"]
    if family not in _PROFILE_FAMILIES:
        raise _schema_error("family profile name is invalid")
    if (
        isinstance(record_count, bool)
        or not isinstance(record_count, int)
        or record_count <= 0
        or isinstance(signature_count, bool)
        or not isinstance(signature_count, int)
        or signature_count <= 0
        or isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 < float(threshold) <= 1
    ):
        raise _schema_error("family profile numeric fields are invalid")
    signatures_value = value["signatures"]
    if not isinstance(signatures_value, list):
        raise _schema_error("signatures must be a list")
    signatures = tuple(_parse_signature(item) for item in signatures_value)
    if len(signatures) != signature_count:
        raise _schema_error("signature count does not match signatures")
    if len({signature.signature_id for signature in signatures}) != len(signatures):
        raise _schema_error("signature identities must be unique within a family")
    if sum(signature.count for signature in signatures) != record_count:
        raise _schema_error("signature counts do not match the family record count")
    required = _string_tuple(value["required_features"], "required_features", _ALLOWED_FEATURES)
    common = _string_tuple(value["common_features"], "common_features", _ALLOWED_FEATURES)
    if not set(required).issubset(common):
        raise _schema_error("required features must be common features")
    return FamilyProfile(
        cast(MessageFamily, family),
        record_count,
        required,
        common,
        signatures,
        float(threshold),
    )


def load_profile_bytes(
    raw: bytes,
    *,
    expected_sha256: str | None = None,
) -> LoadedMtnFormatProfile:
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None:
        if _SHA256.fullmatch(expected_sha256) is None:
            raise MtnFormatProfileError(
                "PROFILE_CONFIGURATION_INVALID", "Expected profile SHA-256 is invalid."
            )
        if digest != expected_sha256:
            raise MtnFormatProfileError(
                "PROFILE_INTEGRITY_FAILURE", "The genuine-format profile failed verification."
            )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _schema_error("profile is not valid UTF-8 JSON") from exc
    expected_keys = {
        "schema_version",
        "builder_version",
        "provider",
        "source_sha256",
        "source_row_count",
        "transaction_row_count",
        "family_profiles",
        "privacy",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise _schema_error("profile root keys are invalid")
    if (
        payload["schema_version"] != PROFILE_SCHEMA_VERSION
        or payload["builder_version"] != PROFILE_BUILDER_VERSION
        or payload["provider"] != "MTN_MOMO"
    ):
        raise _schema_error("profile identity is invalid")
    source_sha256 = payload["source_sha256"]
    source_rows = payload["source_row_count"]
    transaction_rows = payload["transaction_row_count"]
    if not isinstance(source_sha256, str) or _SHA256.fullmatch(source_sha256) is None:
        raise _schema_error("source SHA-256 is invalid")
    if (
        isinstance(source_rows, bool)
        or not isinstance(source_rows, int)
        or source_rows <= 0
        or isinstance(transaction_rows, bool)
        or not isinstance(transaction_rows, int)
        or transaction_rows <= 0
        or transaction_rows > source_rows
    ):
        raise _schema_error("profile row counts are invalid")
    if payload["privacy"] != {
        "raw_text_included": False,
        "direct_identifiers_included": False,
        "locked_test_accessed": False,
        "training_executed": False,
    }:
        raise _schema_error("profile privacy boundary is invalid")
    family_values = payload["family_profiles"]
    if not isinstance(family_values, list) or not family_values:
        raise _schema_error("family profiles must be a non-empty list")
    families = tuple(_parse_family(item) for item in family_values)
    if len({family.family for family in families}) != len(families):
        raise _schema_error("family profiles must be unique")
    if sum(family.record_count for family in families) != transaction_rows:
        raise _schema_error("family counts do not match transaction row count")
    return LoadedMtnFormatProfile(
        family_profiles={family.family: family for family in families},
        profile_sha256=digest,
        raw_bytes=raw,
    )


def load_bundled_mtn_profile() -> LoadedMtnFormatProfile:
    try:
        raw = resources.files("momo_fdvs.policies").joinpath(_PROFILE_FILENAME).read_bytes()
    except OSError as exc:
        raise MtnFormatProfileError(
            "PROFILE_UNAVAILABLE", "The genuine-format profile is unavailable."
        ) from exc
    return load_profile_bytes(raw, expected_sha256=MTN_FORMAT_PROFILE_SHA256)


def classify_message_family(text: str) -> MessageFamily:
    value = unicodedata.normalize("NFKC", text)
    if _FEATURE_PATTERNS["cash_in"].search(value):
        return "CASH_IN"
    if _FEATURE_PATTERNS["cash_out"].search(value):
        return "CASH_OUT"
    if _FEATURE_PATTERNS["payment_received_for"].search(value):
        return "PAYMENT_RECEIVED"
    if _FEATURE_PATTERNS["payment_made_for"].search(value):
        return "PAYMENT_MADE"
    if _FEATURE_PATTERNS["your_payment_of"].search(value):
        return "YOUR_PAYMENT"
    if _FEATURE_PATTERNS["payment_for"].search(value):
        return "PAYMENT_FOR"
    if _FEATURE_PATTERNS["airtime"].search(value):
        return "AIRTIME"
    if _FEATURE_PATTERNS["reversal"].search(value):
        return "REVERSAL"
    if _SECRET.search(value):
        return "SECURITY_OR_OTP"
    if _MARKETING.search(value):
        return "MARKETING"
    if _BALANCE.search(value) and _MONEY.search(value):
        return "BALANCE_OR_STATEMENT"
    return "OTHER"


def _money_count_code(text: str) -> str:
    count = len(_MONEY.findall(text))
    return (
        "money_count_0"
        if count == 0
        else "money_count_1"
        if count == 1
        else "money_count_2"
        if count == 2
        else "money_count_3_plus"
    )


def _fee_precision_code(text: str) -> str:
    precisions: list[int] = []
    for match in _FEE_VALUE.finditer(text):
        value = match.group(1).replace(",", "")
        precisions.append(len(value.rsplit(".", 1)[1]) if "." in value else 0)
    if not precisions:
        return "fee_precision_none"
    maximum = max(precisions)
    return f"fee_precision_{maximum}" if maximum <= 2 else "fee_precision_3_plus"


def extract_structural_signature(text: str) -> StructuralSignature:
    value = unicodedata.normalize("NFKC", text)
    value = "".join(character for character in value if unicodedata.category(character) != "Cf")
    features = {name for name, pattern in _FEATURE_PATTERNS.items() if pattern.search(value)}
    features.update({_money_count_code(value), _fee_precision_code(value)})
    anomalies = {name for name, pattern in _ANOMALY_PATTERNS.items() if pattern.search(value)}
    positions = [
        (match.start(), name)
        for name, pattern in _ANCHOR_PATTERNS
        if (match := pattern.search(value)) is not None
    ]
    return StructuralSignature(
        classify_message_family(value),
        tuple(sorted(features)),
        tuple(name for _position, name in sorted(positions)),
        tuple(sorted(anomalies)),
    )


def _feature_similarity(left: Iterable[str], right: Iterable[str]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 1.0


def _order_similarity(left: Sequence[str], right: Sequence[str]) -> float:
    if not left and not right:
        return 1.0
    matrix = [[0] * (len(right) + 1) for _ in range(len(left) + 1)]
    for row in range(len(left)):
        for column in range(len(right)):
            matrix[row + 1][column + 1] = (
                matrix[row][column] + 1
                if left[row] == right[column]
                else max(matrix[row][column + 1], matrix[row + 1][column])
            )
    return matrix[len(left)][len(right)] / max(len(left), len(right), 1)


def structural_similarity(
    feature_codes: Iterable[str],
    anchor_order: Sequence[str],
    profile: SignatureProfile,
) -> float:
    feature_score = _feature_similarity(feature_codes, profile.feature_codes)
    order_score = _order_similarity(anchor_order, profile.anchor_order)
    return round(0.72 * feature_score + 0.28 * order_score, 6)


__all__ = [
    "MTN_FORMAT_PROFILE_SHA256",
    "PROFILE_SCHEMA_VERSION",
    "FormatMatch",
    "LoadedMtnFormatProfile",
    "MtnFormatProfileError",
    "StructuralSignature",
    "classify_message_family",
    "extract_structural_signature",
    "load_bundled_mtn_profile",
    "load_profile_bytes",
]
