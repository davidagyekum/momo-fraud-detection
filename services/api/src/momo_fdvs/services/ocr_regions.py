"""Deterministic private OCR-region discovery for chat screenshots and receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

RegionKind = Literal["FULL_IMAGE", "HEADER", "BODY", "MESSAGE_BUBBLE"]


@dataclass(frozen=True)
class ImageRegion:
    kind: RegionKind
    x: int
    y: int
    width: int
    height: int
    score: float

    def crop(self, image: np.ndarray) -> np.ndarray:
        return image[self.y : self.y + self.height, self.x : self.x + self.width].copy()

    def as_public_dict(self) -> dict[str, str]:
        """Return only non-geometric evidence suitable for public projections."""

        score_band = "high" if self.score >= 0.8 else "medium" if self.score >= 0.5 else "low"
        return {"kind": self.kind, "score_band": score_band}


def _clamp_region(
    kind: RegionKind,
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
    score: float,
) -> ImageRegion | None:
    x = max(0, min(x, image_width - 1))
    y = max(0, min(y, image_height - 1))
    width = max(1, min(width, image_width - x))
    height = max(1, min(height, image_height - y))
    if width < 80 or height < 60:
        return None
    return ImageRegion(kind, x, y, width, height, max(0.0, min(1.0, score)))


def _bubble_regions(image: np.ndarray) -> list[ImageRegion]:
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask = cv2.inRange(gray, 35, 225)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 15))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    regions: list[ImageRegion] = []
    image_area = float(width * height)
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        area_ratio = (box_width * box_height) / image_area
        if not 0.04 <= area_ratio <= 0.75:
            continue
        if box_width < width * 0.35 or box_height < height * 0.08:
            continue
        if y + box_height < height * 0.25:
            continue
        padding_x = round(box_width * 0.04)
        padding_y = round(box_height * 0.06)
        region = _clamp_region(
            "MESSAGE_BUBBLE",
            x - padding_x,
            y - padding_y,
            box_width + 2 * padding_x,
            box_height + 2 * padding_y,
            width,
            height,
            min(0.98, 0.55 + area_ratio),
        )
        if region is not None:
            regions.append(region)
    regions.sort(key=lambda item: (-item.score, -(item.width * item.height), item.y, item.x))
    return regions[:3]


def discover_ocr_regions(image: np.ndarray) -> tuple[ImageRegion, ...]:
    """Return deterministic full/header/body/bubble regions with private geometry."""

    if image.ndim != 3 or image.shape[2] not in {3, 4}:
        raise ValueError("OCR region discovery expects a BGR or BGRA image")
    height, width = image.shape[:2]
    if width < 100 or height < 100:
        raise ValueError("OCR region discovery requires a usable image")
    regions: list[ImageRegion] = [ImageRegion("FULL_IMAGE", 0, 0, width, height, 1.0)]
    header = _clamp_region("HEADER", 0, 0, width, round(height * 0.32), width, height, 0.8)
    body_y = round(height * 0.20)
    body = _clamp_region("BODY", 0, body_y, width, height - body_y, width, height, 0.78)
    if header is not None:
        regions.append(header)
    if body is not None:
        regions.append(body)
    regions.extend(_bubble_regions(image))

    unique: list[ImageRegion] = []
    seen: set[tuple[int, int, int, int]] = set()
    for region in regions:
        key = (region.x, region.y, region.width, region.height)
        if key not in seen:
            unique.append(region)
            seen.add(key)
    return tuple(unique)


__all__ = ["ImageRegion", "RegionKind", "discover_ocr_regions"]
