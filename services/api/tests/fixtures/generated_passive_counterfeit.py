"""Generate a fictitious screenshot for the passive-counterfeit regression."""

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


def generated_passive_counterfeit_png() -> bytes:
    """Return a wholly fictitious chat screenshot without private source data."""

    image = Image.new("RGB", (960, 1280), "black")
    draw = ImageDraw.Draw(image)
    header_font = _font(46)
    body_font = _font(38)
    date_font = _font(30)

    draw.text((105, 55), "+2335500...", fill="white", font=header_font)
    draw.rounded_rectangle((25, 180, 450, 360), radius=45, fill=(52, 52, 52))
    draw.rounded_rectangle((485, 180, 935, 360), radius=45, fill=(52, 52, 52))
    draw.multiline_text(
        (150, 225),
        "Add to\ncontacts",
        fill="white",
        font=body_font,
        align="center",
    )
    draw.text((560, 250), "Block number", fill="white", font=body_font)
    draw.text((260, 480), "Wednesday, 19 May 2021", fill="white", font=date_font)
    draw.rounded_rectangle((125, 565, 820, 1050), radius=45, fill=(101, 101, 101))

    lines = (
        "Cash In for Gh 700.00",
        "from EXAMPLE TRADERS",
        "carent bulance.700.04",
        "avelabil bulance.700.04",
        "ID: 90000000000001",
        "FEE: 00.000",
    )
    y = 610
    for line in lines:
        draw.text((165, y), line, fill="white", font=body_font)
        y += 58

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


__all__ = ["generated_passive_counterfeit_png"]
