"""Infer privacy-safe sender categories from screenshot OCR header geometry."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal

SenderKind = Literal["phone_number", "alphanumeric_provider", "mixed", "unknown"]

_GHANA_HEADER_PHONE = re.compile(r"^(?:\+?233[25]\d{8}|0[25]\d{8})$")
_TRUNCATED_PHONE = re.compile(r"^\+233[25]\d{2,7}(?:\.{2,}|…)$")
_PHONE_TOKEN = re.compile(r"^[\d+()\s.\-\u2013\u2014…,:;|'`]+$")
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
_IDENTIFIER_LABELS = {"id", "ref", "reference", "transaction id", "transaction reference"}


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


def _header_lines(header: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    by_line: dict[str, list[dict[str, Any]]] = {}
    for token in header:
        text = _token_text(token)
        if not text:
            continue
        line_id = str(token.get("line_id", ""))
        if not line_id:
            line_id = f"y:{round(_safe_int(token.get('y')) / 24)}"
        by_line.setdefault(line_id, []).append(token)
    return [sorted(line, key=lambda item: _safe_int(item.get("x"))) for line in by_line.values()]


def _phone_candidate(value: str) -> bool:
    normalized = value.replace("\u2013", "-").replace("\u2014", "-")
    truncated = bool(re.search(r"(?:\.{2,}|…)$", normalized))
    if truncated:
        suffix = "…" if normalized.endswith("…") else "..."
        normalized = re.sub(r"(?:\.{2,}|…)$", "", normalized)
    else:
        suffix = ""
    compact = re.sub(r"[\s().\-,:;|'`]", "", normalized) + suffix
    return bool(_GHANA_HEADER_PHONE.fullmatch(compact) or _TRUNCATED_PHONE.fullmatch(compact))


def _number_confidence(window: list[dict[str, Any]]) -> float:
    contributing = [
        _confidence(token.get("confidence"))
        for token in window
        if any(character.isdigit() for character in _token_text(token))
    ]
    return sum(contributing) / len(contributing) if contributing else 0.0


def _numeric_header_scores(lines: list[list[dict[str, Any]]]) -> list[float]:
    scores: list[float] = []
    for line in lines:
        for start in range(len(line)):
            prefix_parts = [
                _token_text(item).casefold().strip(" .:|-_")
                for item in line[max(0, start - 2) : start]
            ]
            prefix = " ".join(filter(None, prefix_parts))
            if prefix in _IDENTIFIER_LABELS or (
                prefix_parts and prefix_parts[-1] in _IDENTIFIER_LABELS
            ):
                continue
            window: list[dict[str, Any]] = []
            for token in line[start : start + 6]:
                text = _token_text(token)
                if not text or not _PHONE_TOKEN.fullmatch(text):
                    break
                if window:
                    previous = window[-1]
                    previous_end = _safe_int(previous.get("x")) + max(
                        1, _safe_int(previous.get("width"), 1)
                    )
                    gap = _safe_int(token.get("x")) - previous_end
                    height = max(
                        1,
                        _safe_int(previous.get("height"), 1),
                        _safe_int(token.get("height"), 1),
                    )
                    if gap > max(48, height * 3):
                        break
                window.append(token)
                combined = " ".join(_token_text(item) for item in window)
                if _phone_candidate(combined):
                    scores.append(_number_confidence(window))
    return scores


def _provider_scores(lines: list[list[dict[str, Any]]]) -> list[float]:
    scores: list[float] = []
    for line in lines:
        for start in range(len(line)):
            for size in range(1, min(3, len(line) - start) + 1):
                window = line[start : start + size]
                combined = " ".join(_token_text(item) for item in window)
                normalized = " ".join(combined.casefold().strip(" .:|-_").split())
                if normalized in _UI_WORDS:
                    continue
                if _PROVIDER_LABEL.fullmatch(normalized):
                    values = [_confidence(item.get("confidence")) for item in window]
                    scores.append(sum(values) / len(values) if values else 0.0)
    return scores


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

    lines = _header_lines(_header_tokens(tokens, image_height))
    raw_text_fallback = False
    numeric_scores = _numeric_header_scores(lines)
    provider_scores = _provider_scores(lines)
    if not lines and raw_text:
        candidates = _raw_header_candidates(raw_text)
        raw_text_fallback = True
        for raw_value, confidence in candidates:
            if _phone_candidate(raw_value):
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
            max(numeric_scores),
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
