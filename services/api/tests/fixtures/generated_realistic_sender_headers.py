"""Generate fictitious chat screenshots for sender-header OCR boundaries."""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _chat_screenshot(
    header: str,
    lines: tuple[str, ...],
    *,
    phone_line_index: int | None = None,
) -> bytes:
    image = Image.new("RGB", (1080, 1440), "black")
    draw = ImageDraw.Draw(image)
    header_font = _font(42)
    body_font = _font(34)
    small_font = _font(27)

    draw.text((28, 58), "<", fill="white", font=header_font)
    draw.text((105, 58), header, fill="white", font=header_font)
    draw.text((745, 64), "CALL  VIDEO  MENU", fill="white", font=small_font)
    draw.line((0, 145, 1080, 145), fill=(80, 80, 80), width=3)
    draw.text((370, 190), "Today, 10:30", fill=(210, 210, 210), font=small_font)
    draw.rounded_rectangle((90, 275, 990, 1190), radius=42, fill=(92, 92, 92))

    y = 330
    for index, line in enumerate(lines):
        if phone_line_index is not None and index == phone_line_index:
            y = max(y, 680)
        draw.text((135, y), line, fill="white", font=body_font)
        y += 62

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def generated_spaced_phone_counterfeit_png() -> bytes:
    """Return a synthetic counterfeit under a full spaced Ghana sender."""

    return _chat_screenshot(
        "+233 55 812 4076",
        (
            "Cash In recieved for GH 420.00",
            "from SAMPLE MARKET",
            "Curent Balanse GH 420.04",
            "Avelable Balanse GH 420.04",
            "Tranction ID: 84000000000031",
            "FEE: 00.000",
        ),
    )


def generated_realistic_genuine_mobilemoney_png() -> bytes:
    """Return a genuine-format MTN message with an official sender label."""

    return _chat_screenshot(
        "MobileMoney",
        (
            "Cash In received for GHS 25.00",
            "from SAMPLE MERCHANT.",
            "Current Balance GHS 80.00.",
            "Available Balance GHS 80.00.",
            "Transaction ID: 246813579.",
            "Fee charged: GHS 0.",
            "Cash In is free.",
        ),
    )


def generated_spaced_numeric_ordinary_chat_png() -> bytes:
    """Return ordinary non-financial chat beneath a full spaced number."""

    return _chat_screenshot(
        "+233 24 618 3057",
        (
            "Hello, the community meeting is tomorrow.",
            "Please bring your membership card.",
            "The hall opens at nine in the morning.",
            "Thank you.",
        ),
    )


def generated_body_only_spaced_phone_png() -> bytes:
    """Return a spaced Ghana number only in the lower message body."""

    return _chat_screenshot(
        "Messages",
        (
            "Community directions are available.",
            "The meeting starts tomorrow morning.",
            "Bring your membership card.",
            "For directions contact +233 20 481 3076.",
        ),
        phone_line_index=3,
    )


def generated_header_transaction_id_png() -> bytes:
    """Return a phone-shaped transaction identifier in the header."""

    return _chat_screenshot(
        "Transaction ID: 233 55 812 4076",
        (
            "Your archived document is ready.",
            "Open the records desk during office hours.",
            "No payment action is required.",
        ),
    )


def generated_header_datetime_count_png() -> bytes:
    """Return header date/time and count digits without a sender number."""

    return _chat_screenshot(
        "23 Aug 2026  10:30  2 messages",
        (
            "This is a calendar reminder.",
            "The appointment begins tomorrow morning.",
            "No reply is needed.",
        ),
    )


__all__ = [
    "generated_body_only_spaced_phone_png",
    "generated_header_datetime_count_png",
    "generated_header_transaction_id_png",
    "generated_realistic_genuine_mobilemoney_png",
    "generated_spaced_numeric_ordinary_chat_png",
    "generated_spaced_phone_counterfeit_png",
]
