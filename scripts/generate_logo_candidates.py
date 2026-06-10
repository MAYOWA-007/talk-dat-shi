from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "knight_flow" / "assets"
OUT = ROOT / "branding" / "logo-candidates"
SIZE = 2048
PREVIEW_SIZE = 420


def flow_frame(index: int) -> Image.Image:
    strip = Image.open(ASSETS / "flow_pill_240.png").convert("RGBA")
    meta = json.loads((ASSETS / "flow_pill_240.json").read_text(encoding="utf-8"))
    columns = int(meta["columns"])
    frame_width = int(meta["frame_width"])
    frame_height = int(meta["frame_height"])
    count = int(meta["frame_count"])
    index = max(0, min(count - 1, index))
    col = index % columns
    row = index // columns
    return strip.crop((col * frame_width, row * frame_height, (col + 1) * frame_width, (row + 1) * frame_height))


def texture(index: int, *, flip: bool = False, contrast: float = 1.18, color: float = 1.28) -> Image.Image:
    frame = flow_frame(index)
    if flip:
        frame = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    frame = frame.resize((SIZE, SIZE), Image.Resampling.BICUBIC)
    frame = ImageEnhance.Color(frame).enhance(color)
    frame = ImageEnhance.Contrast(frame).enhance(contrast)
    frame = ImageEnhance.Sharpness(frame).enhance(1.25)
    return frame


def rounded_frame_mask(outer: tuple[int, int, int, int], radius: int, thickness: int) -> Image.Image:
    mask = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(outer, radius=radius, fill=255)
    inset = thickness
    inner = (outer[0] + inset, outer[1] + inset, outer[2] - inset, outer[3] - inset)
    draw.rounded_rectangle(inner, radius=max(1, radius - inset), fill=0)
    return mask


def chamfer_frame_mask(outer: tuple[int, int, int, int], chamfer: int, thickness: int) -> Image.Image:
    x1, y1, x2, y2 = outer
    outer_poly = [(x1 + chamfer, y1), (x2 - chamfer, y1), (x2, y1 + chamfer), (x2, y2 - chamfer), (x2 - chamfer, y2), (x1 + chamfer, y2), (x1, y2 - chamfer), (x1, y1 + chamfer)]
    inner = (x1 + thickness, y1 + thickness, x2 - thickness, y2 - thickness)
    ix1, iy1, ix2, iy2 = inner
    inner_chamfer = max(10, chamfer - thickness)
    inner_poly = [(ix1 + inner_chamfer, iy1), (ix2 - inner_chamfer, iy1), (ix2, iy1 + inner_chamfer), (ix2, iy2 - inner_chamfer), (ix2 - inner_chamfer, iy2), (ix1 + inner_chamfer, iy2), (ix1, iy2 - inner_chamfer), (ix1, iy1 + inner_chamfer)]
    mask = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(outer_poly, fill=255)
    draw.polygon(inner_poly, fill=0)
    return mask


def bars_mask(spec: list[tuple[int, int, int, int, int]], *, cut: str = "round") -> Image.Image:
    mask = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(mask)
    for x, y, w, h, r in spec:
        if cut == "chamfer":
            c = min(w // 4, 46)
            draw.polygon(
                [(x + c, y), (x + w - c, y), (x + w, y + c), (x + w, y + h - c), (x + w - c, y + h), (x + c, y + h), (x, y + h - c), (x, y + c)],
                fill=255,
            )
        else:
            draw.rounded_rectangle((x, y, x + w, y + h), radius=r, fill=255)
    return mask


def paste_masked(base: Image.Image, fill: Image.Image, mask: Image.Image, alpha: int = 255) -> None:
    if alpha < 255:
        mask = mask.point(lambda p: int(p * alpha / 255))
    base.alpha_composite(Image.composite(fill, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))


def glow(mask: Image.Image, color: tuple[int, int, int], radius: int, strength: int) -> Image.Image:
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=radius))
    layer = Image.new("RGBA", (SIZE, SIZE), (*color, 0))
    layer.putalpha(blurred.point(lambda p: min(255, int(p * strength / 255))))
    return layer


def outline(mask: Image.Image, color: tuple[int, int, int, int], width: int) -> Image.Image:
    grown = mask.filter(ImageFilter.MaxFilter(width * 2 + 1))
    edge = ImageChops.subtract(grown, mask)
    layer = Image.new("RGBA", (SIZE, SIZE), color)
    layer.putalpha(edge.point(lambda p: min(color[3], p)))
    return layer


def compose(name: str, frame_mask: Image.Image, bar_mask: Image.Image, tex: Image.Image, *, inner_line: bool = True) -> Image.Image:
    shape = ImageChops.lighter(frame_mask, bar_mask)
    art = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    art.alpha_composite(glow(shape, (255, 72, 36), 46, 92))
    art.alpha_composite(glow(shape, (25, 224, 210), 72, 68))

    dark_edge = shape.filter(ImageFilter.MaxFilter(51))
    dark_edge = ImageChops.subtract(dark_edge, shape.filter(ImageFilter.MinFilter(5)))
    edge_layer = Image.new("RGBA", (SIZE, SIZE), (0, 8, 9, 210))
    edge_layer.putalpha(dark_edge.point(lambda p: min(210, int(p * 0.86))))
    art.alpha_composite(edge_layer)

    paste_masked(art, tex, frame_mask, 255)
    paste_masked(art, tex, bar_mask, 255)

    if inner_line:
        thin = ImageChops.lighter(
            frame_mask.filter(ImageFilter.MinFilter(23)),
            bar_mask.filter(ImageFilter.MinFilter(19)),
        )
        line = Image.new("RGBA", (SIZE, SIZE), (255, 242, 190, 78))
        line.putalpha(thin.point(lambda p: int(p * 0.34)))
        art.alpha_composite(line)

    shine = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(shine)
    draw.rounded_rectangle((245, 222, 1803, 536), radius=118, fill=(255, 255, 255, 34))
    shine.putalpha(ImageChops.multiply(shine.getchannel("A"), shape))
    art.alpha_composite(shine)
    art.save(OUT / f"{name}.png", compress_level=3)
    return art


def make_checker(w: int, h: int, cell: int = 28) -> Image.Image:
    image = Image.new("RGBA", (w, h), (240, 244, 244, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if (x // cell + y // cell) % 2:
                draw.rectangle((x, y, x + cell, y + cell), fill=(209, 218, 216, 255))
    return image


def preview(candidates: list[tuple[str, Image.Image]]) -> None:
    pad = 54
    label_h = 50
    sheet = make_checker((PREVIEW_SIZE + pad) * len(candidates) + pad, PREVIEW_SIZE + label_h + pad * 2)
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("seguisb.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for i, (name, image) in enumerate(candidates):
        x = pad + i * (PREVIEW_SIZE + pad)
        y = pad
        preview_image = image.resize((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.LANCZOS)
        sheet.alpha_composite(preview_image, (x, y))
        draw.text((x, y + PREVIEW_SIZE + 10), name.replace("flow-logo-", "v"), fill=(3, 24, 25, 255), font=font)
    sheet.convert("RGB").save(OUT / "preview-sheet.png", quality=95)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    variants: list[tuple[str, Image.Image]] = []

    frame = rounded_frame_mask((238, 238, 1810, 1810), 202, 182)
    bars = bars_mask([(500, 846, 176, 416, 88), (740, 512, 176, 918, 88), (980, 664, 176, 704, 88), (1220, 576, 176, 854, 88), (1460, 846, 176, 416, 88)])
    variants.append(("flow-logo-01-meter", compose("flow-logo-01-meter", frame, bars, texture(22))))

    frame = rounded_frame_mask((220, 230, 1828, 1818), 172, 190)
    bars = bars_mask([(480, 850, 190, 400, 64), (720, 464, 190, 1030, 64), (960, 640, 190, 780, 64), (1200, 464, 190, 1030, 64), (1440, 850, 190, 400, 64)], cut="chamfer")
    variants.append(("flow-logo-02-cut-edge", compose("flow-logo-02-cut-edge", frame, bars, texture(58, flip=True, contrast=1.24), inner_line=True)))

    frame = rounded_frame_mask((224, 274, 1824, 1774), 248, 178)
    bars = bars_mask([(500, 908, 166, 352, 83), (730, 620, 192, 806, 96), (980, 436, 192, 1182, 96), (1230, 650, 192, 776, 96), (1460, 908, 166, 352, 83)])
    variants.append(("flow-logo-03-fan-rise", compose("flow-logo-03-fan-rise", frame, bars, texture(96, color=1.36), inner_line=True)))

    frame = chamfer_frame_mask((218, 218, 1830, 1830), 190, 190)
    bars = bars_mask([(480, 812, 180, 468, 44), (720, 536, 180, 984, 44), (960, 704, 180, 648, 44), (1200, 536, 180, 984, 44), (1440, 812, 180, 468, 44)], cut="chamfer")
    variants.append(("flow-logo-04-chamfer", compose("flow-logo-04-chamfer", frame, bars, texture(136, flip=True, contrast=1.3), inner_line=False)))

    frame = rounded_frame_mask((210, 210, 1838, 1838), 236, 210)
    bars = bars_mask([(480, 874, 166, 320, 83), (720, 684, 178, 704, 89), (970, 500, 204, 1086, 102), (1220, 684, 178, 704, 89), (1460, 874, 166, 320, 83)])
    variants.append(("flow-logo-05-heavy-glass", compose("flow-logo-05-heavy-glass", frame, bars, texture(178, contrast=1.34, color=1.42), inner_line=True)))

    preview(variants)
    print(f"Wrote {len(variants)} logo candidates to {OUT}")


if __name__ == "__main__":
    main()
