"""Generate fictitious genuine/advisory screenshots for real-OCR boundaries."""

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


def _message_screenshot(
    lines: tuple[str, ...],
    *,
    header: str = "MobileMoney",
) -> bytes:
    image = Image.new("RGB", (960, 1280), "white")
    draw = ImageDraw.Draw(image)
    header_font = _font(46)
    body_font = _font(34)
    date_font = _font(28)

    draw.text((105, 60), header, fill=(30, 30, 30), font=header_font)
    draw.line((0, 145, 960, 145), fill=(210, 210, 210), width=3)
    draw.text((290, 205), "Today, 10:30", fill=(95, 95, 95), font=date_font)
    draw.rounded_rectangle((70, 285, 890, 1020), radius=40, fill=(235, 235, 235))

    y = 335
    for line in lines:
        draw.text((115, y), line, fill=(25, 25, 25), font=body_font)
        y += 58

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def generated_genuine_cash_in_png() -> bytes:
    """Return a fictitious cash-in matching the reviewed safe format profile."""

    return _message_screenshot(
        (
            "Cash In received for GHS 10.00",
            "from SAMPLE SHOP.",
            "Current Balance GHS 20.00.",
            "Available Balance GHS 20.00.",
            "Transaction ID: 123456789.",
            "Fee charged: GHS 0.",
            "Cash In is free.",
        )
    )


def generated_official_advisory_png() -> bytes:
    """Return a fictitious provider safety advisory with negated secret terms."""

    return _message_screenshot(
        (
            "Security reminder from MTN MoMo:",
            "Never share your PIN or OTP with anyone.",
            "MTN will never ask you to disclose",
            "a PIN, OTP or security code.",
            "Use only official provider channels",
            "if you need support.",
        )
    )


def generated_genuine_payment_made_png() -> bytes:
    """Return a fictitious payment matching a reviewed payment-made format."""

    return _message_screenshot(
        (
            "Payment made for GHS 15.00",
            "to SAMPLE STORE.",
            "Current Balance GHS 85.00.",
            "Available Balance GHS 85.00.",
            "Reference: DEMO PURCHASE.",
            "Transaction ID: 456789123.",
            "Fee charged: GHS 0.00.",
            "Tax charged: GHS 0.00.",
        )
    )


def generated_genuine_cash_in_one_typo_png() -> bytes:
    """Return a genuine-format cash-in with one OCR-like vocabulary typo."""

    return _message_screenshot(
        (
            "Cash In received for GHS 10.00",
            "from SAMPLE SHOP.",
            "Current Balanse GHS 20.00.",
            "Available Balance GHS 20.00.",
            "Transaction ID: 123456789.",
            "Fee charged: GHS 0.",
            "Cash In is free.",
        )
    )


def generated_numeric_sender_ordinary_chat_png() -> bytes:
    """Return non-financial chat under a numeric sender header."""

    return _message_screenshot(
        (
            "Hello, your appointment is tomorrow.",
            "Please bring your identification card.",
            "The office opens at nine in the morning.",
            "Thank you.",
        ),
        header="+2335500...",
    )


def generated_body_phone_unknown_sender_png() -> bytes:
    """Return a body-only phone number beneath an unclassified header."""

    return _message_screenshot(
        (
            "Community meeting reminder.",
            "The meeting starts tomorrow morning.",
            "Bring your membership card.",
            "For directions only, contact",
            "0244000000 before arriving.",
        ),
        header="Messages",
    )


__all__ = [
    "generated_body_phone_unknown_sender_png",
    "generated_genuine_cash_in_one_typo_png",
    "generated_genuine_cash_in_png",
    "generated_genuine_payment_made_png",
    "generated_numeric_sender_ordinary_chat_png",
    "generated_official_advisory_png",
]
