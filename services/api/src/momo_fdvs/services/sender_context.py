"""Infer privacy-safe sender categories from screenshot OCR header geometry."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

SenderKind = Literal["phone_number", "alphanumeric_provider", "mixed", "unknown"]

_GHANA_HEADER_PHONE = re.compile(
    r"^(?:\+?233|0)(?:[\s().-]*\d){4,9}(?:\.{2,}|…)?$",
    re.IGNORECASE,
)
_TRUNCATED_PHONE = re.compile(r"^(?:\+?233|0)[\d\s().-]{4,}(?:\.{2,}|…)$")
_PROVIDER_LABEL = re.compile(
    r"(?i)^(?:mobile\s*money|mobilemoney|mtn\s*momo|momo|telecel(?:\s+cash)?|"
    r"t[- ]?cash|airteltigo(?:\s+money)?|at\s+money)$"
)
_UI_WORDS = {
    "add to",
    "contacts",
    "add to contacts",
    "block number",
    "call",
    "video",
    "back",
    "details",
    "search",
}


@dataclass(frozen=True)
class SenderContext:
    sender_kind: SenderKind
    sender_confidence: float
    header_phone_present: bool
    header_provider_label_present: bool
    source: str

    def as_public_dict(self) -> dict[str, object]:
        """Project categorical evidence without sender text, geometry, or token IDs."""

        return {
            "sender_kind": self.sender_kind,
            "sender_confidence": round(max(0.0, min(1.0, self.sender_confidence)), 4),
            "header_phone_present": self.header_phone_present,
            "header_provider_label_present": self.header_provider_label_present,
            "source": self.source,
        }


def _confidence(raw: Any) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return 0.0
    value = float(raw)
    if value > 1:
        value /= 100
    return max(0.0, min(1.0, value))


def _safe_int(raw: Any, fallback: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return fallback


def _token_text(token: dict[str, Any]) -> str:
    value = unicodedata.normalize("NFKC", str(token.get("text", "")))
    value = "".join(character for character in value if unicodedata.category(character) != "Cf")
    return " ".join(value.split()).strip()


def _header_tokens(
    tokens: Iterable[dict[str, Any]],
    image_height: int,
) -> list[dict[str, Any]]:
    if image_height <= 0:
        return []
    header_limit = max(120, round(image_height * 0.30))
    selected: list[dict[str, Any]] = []
    for token in tokens:
        try:
            y = int(token.get("y", 0))
            height = max(1, int(token.get("height", 1)))
        except (TypeError, ValueError):
            continue
        if y >= 0 and y + height <= header_limit:
            selected.append(token)
    return sorted(
        selected,
        key=lambda item: (_safe_int(item.get("y")), _safe_int(item.get("x"))),
    )


def _candidate_strings(header: list[dict[str, Any]]) -> list[tuple[str, float]]:
    candidates: list[tuple[str, float]] = []
    by_line: dict[str, list[dict[str, Any]]] = {}
    for token in header:
        text = _token_text(token)
        if text:
            candidates.append((text, _confidence(token.get("confidence"))))
        line_id = str(token.get("line_id", ""))
        if not line_id:
            line_id = f"y:{round(_safe_int(token.get('y')) / 24)}"
        by_line.setdefault(line_id, []).append(token)
    for line in by_line.values():
        ordered = sorted(line, key=lambda item: _safe_int(item.get("x")))
        combined = " ".join(filter(None, (_token_text(item) for item in ordered))).strip()
        if combined:
            values = [_confidence(item.get("confidence")) for item in ordered]
            candidates.append((combined, sum(values) / len(values) if values else 0.0))
    return candidates


def _raw_header_candidates(raw_text: str) -> list[tuple[str, float]]:
    lines = [" ".join(line.split()).strip() for line in raw_text.splitlines() if line.strip()]
    return [(line, 0.55) for line in lines[:4]]


def infer_sender_context(
    tokens: Iterable[dict[str, Any]],
    *,
    image_height: int,
    raw_text: str = "",
) -> SenderContext:
    """Infer a sender category from only the top 30 percent of OCR geometry."""

    candidates = _candidate_strings(_header_tokens(tokens, image_height))
    raw_text_fallback = False
    if not candidates and raw_text:
        candidates = _raw_header_candidates(raw_text)
        raw_text_fallback = True
    numeric_scores: list[float] = []
    provider_scores: list[float] = []
    for raw_value, confidence in candidates:
        compact = re.sub(r"\s+", "", raw_value)
        if _GHANA_HEADER_PHONE.fullmatch(compact) or _TRUNCATED_PHONE.fullmatch(compact):
            numeric_scores.append(confidence)
            continue
        normalized = " ".join(raw_value.casefold().strip(" .:|-_").split())
        if normalized in _UI_WORDS:
            continue
        if _PROVIDER_LABEL.fullmatch(normalized):
            provider_scores.append(confidence)
    if numeric_scores and provider_scores:
        return SenderContext(
            "mixed",
            (
                max(numeric_scores + provider_scores)
                if raw_text_fallback
                else max(0.75, max(numeric_scores + provider_scores))
            ),
            not raw_text_fallback,
            not raw_text_fallback,
            "raw_text_fallback" if raw_text_fallback else "ocr_header",
        )
    if numeric_scores:
        return SenderContext(
            "phone_number",
            max(numeric_scores) if raw_text_fallback else max(0.80, max(numeric_scores)),
            not raw_text_fallback,
            False,
            "raw_text_fallback" if raw_text_fallback else "ocr_header",
        )
    if provider_scores:
        return SenderContext(
            "alphanumeric_provider",
            max(provider_scores) if raw_text_fallback else max(0.75, max(provider_scores)),
            False,
            not raw_text_fallback,
            "raw_text_fallback" if raw_text_fallback else "ocr_header",
        )
    return SenderContext("unknown", 0.0, False, False, "none")


__all__ = ["SenderContext", "SenderKind", "infer_sender_context"]
