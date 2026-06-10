from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "knight_flow" / "assets"
SHEET_PATH = ASSETS / "flow_pill_240.png"
META_PATH = ASSETS / "flow_pill_240.json"


def resample() -> int:
    return getattr(Image.Resampling, "LANCZOS", Image.LANCZOS)


def rounded_mask(size: int, inset: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((inset, inset, size - inset, size - inset), radius=radius, fill=255)
    return mask


def flow_texture(size: int) -> Image.Image:
    if SHEET_PATH.exists() and META_PATH.exists():
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        frame_width = int(meta.get("frame_width", 320))
        frame_height = int(meta.get("frame_height", 58))
        sheet = Image.open(SHEET_PATH).convert("RGBA")
        frame = sheet.crop((0, 0, frame_width, frame_height))
        frame = frame.resize((size, size), resample())
        frame = frame.filter(ImageFilter.GaussianBlur(0.8))
        return frame

    texture = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(texture)
    stops = [
        (0.00, (255, 39, 49)),
        (0.28, (255, 70, 35)),
        (0.46, (255, 206, 111)),
        (0.68, (0, 122, 126)),
        (1.00, (6, 30, 43)),
    ]
    for x in range(size):
        t = x / max(1, size - 1)
        left = stops[0]
        right = stops[-1]
        for index in range(len(stops) - 1):
            if stops[index][0] <= t <= stops[index + 1][0]:
                left = stops[index]
                right = stops[index + 1]
                break
        span = max(0.001, right[0] - left[0])
        amount = (t - left[0]) / span
        color = tuple(int(left[1][i] + (right[1][i] - left[1][i]) * amount) for i in range(3))
        draw.line((x, 0, x, size), fill=(*color, 255))
    return texture


def paste_with_mask(base: Image.Image, fill: Image.Image | tuple[int, int, int, int], mask: Image.Image) -> None:
    layer = fill if isinstance(fill, Image.Image) else Image.new("RGBA", base.size, fill)
    base.alpha_composite(Image.composite(layer, Image.new("RGBA", base.size, (0, 0, 0, 0)), mask))


def dilate(mask: Image.Image, pixels: int) -> Image.Image:
    amount = max(1, pixels * 2 + 1)
    if amount % 2 == 0:
        amount += 1
    return mask.filter(ImageFilter.MaxFilter(amount))


def stroke_mask(mask: Image.Image, outer: int, inner: int) -> Image.Image:
    return ImageChops.subtract(dilate(mask, outer), mask.filter(ImageFilter.MinFilter(max(3, inner * 2 + 1))))


def arc_mask(size: int, box: tuple[int, int, int, int], start: int, end: int, width: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.arc(box, start=start, end=end, fill=255, width=width)
    left, top, right, bottom = box
    cx = (left + right) / 2
    cy = (top + bottom) / 2
    rx = (right - left) / 2
    ry = (bottom - top) / 2
    radius = width / 2
    for angle in (start, end):
        radians = math.radians(angle)
        x = cx + math.cos(radians) * rx
        y = cy + math.sin(radians) * ry
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(0.35)).point(lambda value: 255 if value > 62 else 0)


def lion_roar_mask(size: int) -> tuple[Image.Image, Image.Image]:
    s = size / 1024
    glyph = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(glyph)

    cx, cy = int(382 * s), int(514 * s)
    mane: list[tuple[int, int]] = []
    for index in range(34):
        angle = math.radians(-116 + index * (304 / 33))
        radius = (300 if index % 2 == 0 else 242) * s
        mane.append((int(cx + math.cos(angle) * radius), int(cy + math.sin(angle) * radius)))
    draw.polygon(mane, fill=255)
    draw.ellipse((int(182 * s), int(226 * s), int(602 * s), int(795 * s)), fill=255)
    draw.polygon(
        [
            (int(278 * s), int(298 * s)),
            (int(220 * s), int(142 * s)),
            (int(410 * s), int(248 * s)),
        ],
        fill=255,
    )
    draw.polygon(
        [
            (int(494 * s), int(280 * s)),
            (int(642 * s), int(178 * s)),
            (int(604 * s), int(392 * s)),
        ],
        fill=255,
    )
    draw.ellipse((int(315 * s), int(326 * s), int(638 * s), int(706 * s)), fill=255)
    draw.ellipse((int(392 * s), int(505 * s), int(678 * s), int(742 * s)), fill=255)
    draw.polygon(
        [
            (int(566 * s), int(494 * s)),
            (int(724 * s), int(550 * s)),
            (int(575 * s), int(628 * s)),
        ],
        fill=255,
    )
    draw.rounded_rectangle(
        (int(462 * s), int(622 * s), int(628 * s), int(820 * s)),
        radius=int(86 * s),
        fill=255,
    )

    waves = Image.new("L", (size, size), 0)
    for box, width in (
        ((570, 366, 805, 666), 48),
        ((548, 300, 922, 742), 58),
        ((520, 228, 1010, 824), 68),
    ):
        waves = ImageChops.lighter(
            waves,
            arc_mask(size, tuple(int(value * s) for value in box), -55, 55, int(width * s)),
        )

    return glyph, waves


def make_icon(size: int = 1024) -> Image.Image:
    texture = flow_texture(size)
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    glass_mask = rounded_mask(size, int(size * 0.075), int(size * 0.22))
    glass = Image.new("RGBA", (size, size), (2, 17, 23, 232))
    texture_soft = texture.filter(ImageFilter.GaussianBlur(size * 0.012))
    texture_soft.putalpha(glass_mask.point(lambda value: int(value * 0.38)))
    glass.alpha_composite(texture_soft)
    paste_with_mask(icon, glass, glass_mask)

    lion_mask, wave_mask = lion_roar_mask(size)
    combined = ImageChops.lighter(lion_mask, wave_mask)

    glow = dilate(combined, int(size * 0.045)).filter(ImageFilter.GaussianBlur(size * 0.03))
    paste_with_mask(icon, (255, 52, 34, 62), glow)
    teal_glow = dilate(wave_mask, int(size * 0.035)).filter(ImageFilter.GaussianBlur(size * 0.028))
    paste_with_mask(icon, (0, 220, 210, 74), teal_glow)

    outline_outer = stroke_mask(combined, int(size * 0.026), int(size * 0.008))
    paste_with_mask(icon, (3, 20, 25, 220), outline_outer)
    outline_inner = stroke_mask(combined, int(size * 0.012), int(size * 0.005))
    paste_with_mask(icon, (244, 231, 190, 176), outline_inner)
    paste_with_mask(icon, texture, combined)

    s = size / 1024
    detail = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(detail)
    dark = (3, 18, 24, 205)
    warm = (255, 239, 195, 170)
    draw.ellipse((int(432 * s), int(408 * s), int(486 * s), int(456 * s)), fill=dark)
    draw.polygon(
        [
            (int(560 * s), int(492 * s)),
            (int(694 * s), int(548 * s)),
            (int(568 * s), int(610 * s)),
        ],
        fill=dark,
    )
    draw.arc((int(310 * s), int(470 * s), int(596 * s), int(755 * s)), 18, 82, fill=warm, width=max(3, int(12 * s)))
    draw.line((int(312 * s), int(352 * s), int(238 * s), int(198 * s)), fill=warm, width=max(3, int(10 * s)))
    draw.line((int(510 * s), int(330 * s), int(632 * s), int(210 * s)), fill=warm, width=max(3, int(10 * s)))
    detail = detail.filter(ImageFilter.GaussianBlur(0.25))
    icon.alpha_composite(detail)

    sheen = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sheen_draw = ImageDraw.Draw(sheen)
    sheen_draw.rounded_rectangle(
        (int(size * 0.11), int(size * 0.095), int(size * 0.89), int(size * 0.34)),
        radius=int(size * 0.16),
        fill=(255, 247, 208, 34),
    )
    icon.alpha_composite(Image.composite(sheen.filter(ImageFilter.GaussianBlur(size * 0.012)), Image.new("RGBA", icon.size, (0, 0, 0, 0)), glass_mask))

    border = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle(
        (int(size * 0.075), int(size * 0.075), int(size * 0.925), int(size * 0.925)),
        radius=int(size * 0.22),
        outline=(22, 232, 213, 96),
        width=max(2, int(size * 0.012)),
    )
    border_draw.rounded_rectangle(
        (int(size * 0.095), int(size * 0.095), int(size * 0.905), int(size * 0.905)),
        radius=int(size * 0.19),
        outline=(255, 219, 155, 60),
        width=max(1, int(size * 0.006)),
    )
    icon.alpha_composite(border)
    return icon


def save_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.save(ASSETS / "app_icon.png")
    icon.save(ASSETS / "logo.png")

    favicon = icon.resize((256, 256), resample())
    favicon.save(ASSETS / "favicon.png")

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(ASSETS / "app_icon.ico", sizes=sizes)
    icon.save(ASSETS / "logo.ico", sizes=sizes)
    favicon.save(ASSETS / "favicon.ico", sizes=sizes)


if __name__ == "__main__":
    save_assets()
