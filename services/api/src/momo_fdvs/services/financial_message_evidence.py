"""OCR-tolerant, privacy-safe financial language and formatting evidence."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Final

_FINANCIAL_TERMS: Final = frozenset(
    {
        "available",
        "balance",
        "charged",
        "current",
        "financial",
        "payment",
        "received",
        "reference",
        "successful",
        "transaction",
        "transferred",
    }
)
_TRANSACTION = re.compile(
    r"(?i)\b(?:cash\s*(?:in|out)|payment|transaction|current\s+balance|"
    r"available\s+balance|fee|reference|received|sent|transfer(?:red)?)\b"
)
_MONEY_OR_AMOUNT = re.compile(r"(?i)(?:GHS|GHC|GH[₵¢]|₵)\s*\d|\b\d+\.\d{2,3}\b")
_FORMAT_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "NONSTANDARD_CURRENCY_MARKER": re.compile(r"(?i)\bgh\s+\d"),
    "BALANCE_VALUE_JOINED_TO_LABEL": re.compile(r"(?i)\b(?:balance|bulance|balanse)\s*[.:]\s*\d"),
    "FEE_HAS_MORE_THAN_TWO_DECIMALS": re.compile(r"(?i)\bfee\s*:?[^\d]{0,10}\d+(?:\.\d{3,})\b"),
    "BARE_ID_LABEL_IN_TRANSACTION_MESSAGE": re.compile(
        r"(?i)(?<!transaction\s)(?<!financial\s)(?<!external\s)\bid\s*:"
    ),
}


@dataclass(frozen=True)
class LanguageFormatEvidence:
    spelling_anomaly_count: int
    formatting_anomaly_count: int
    spelling_codes: tuple[str, ...]
    formatting_codes: tuple[str, ...]
    transaction_claim: bool

    def as_public_dict(self) -> dict[str, object]:
        """Return only aggregate counts and allowlisted reason codes."""

        return {
            "spelling_anomaly_count": self.spelling_anomaly_count,
            "formatting_anomaly_count": self.formatting_anomaly_count,
            "spelling_codes": list(self.spelling_codes),
            "formatting_codes": list(self.formatting_codes),
            "transaction_claim": self.transaction_claim,
        }


def _normalize_word(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(character for character in normalized if character.isalpha())


def _token_confidence(raw: Any) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return 0.0
    value = float(raw)
    if value > 1:
        value /= 100
    return max(0.0, min(1.0, value))


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for row, left_character in enumerate(left, start=1):
        current = [row]
        for column, right_character in enumerate(right, start=1):
            substitution = previous[column - 1] + (left_character != right_character)
            insertion = current[column - 1] + 1
            deletion = previous[column] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


def _nearest_financial_term(word: str) -> tuple[str | None, int]:
    best_term: str | None = None
    best_distance = 100
    for term in _FINANCIAL_TERMS:
        distance = _edit_distance(word, term)
        if distance < best_distance or (distance == best_distance and term < (best_term or "~")):
            best_term, best_distance = term, distance
    return best_term, best_distance


def _misspelled_financial_terms(tokens: Iterable[dict[str, Any]]) -> set[str]:
    findings: set[str] = set()
    for token in tokens:
        if _token_confidence(token.get("confidence")) < 0.62:
            continue
        candidate = _normalize_word(str(token.get("text", "")))
        if candidate in _FINANCIAL_TERMS or len(candidate) < 5:
            continue
        nearest, distance = _nearest_financial_term(candidate)
        if nearest is None:
            continue
        similarity = 1.0 - distance / max(len(candidate), len(nearest))
        if distance <= 2 and similarity >= 0.68:
            findings.add(nearest)
    return findings


def analyze_language_and_format(
    raw_text: str,
    tokens: Iterable[dict[str, Any]],
) -> LanguageFormatEvidence:
    """Analyze a transaction claim without returning matched words or values."""

    canonical = unicodedata.normalize("NFKC", raw_text)
    canonical = "".join(
        character for character in canonical if unicodedata.category(character) != "Cf"
    )
    transaction_claim = bool(_TRANSACTION.search(canonical) and _MONEY_OR_AMOUNT.search(canonical))
    if not transaction_claim:
        return LanguageFormatEvidence(0, 0, (), (), False)
    misspellings = _misspelled_financial_terms(tokens)
    spelling_codes = ("MULTIPLE_FINANCIAL_TERM_MISSPELLINGS",) if len(misspellings) >= 2 else ()
    formatting_codes = tuple(
        sorted(code for code, pattern in _FORMAT_PATTERNS.items() if pattern.search(canonical))
    )
    return LanguageFormatEvidence(
        spelling_anomaly_count=len(misspellings),
        formatting_anomaly_count=len(formatting_codes),
        spelling_codes=spelling_codes,
        formatting_codes=formatting_codes,
        transaction_claim=True,
    )


__all__ = ["LanguageFormatEvidence", "analyze_language_and_format"]
