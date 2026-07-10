from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


APP_DIR = Path(__file__).resolve().parents[1]
ASSET_DIR = APP_DIR / "assets"


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
    ]

    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    return ImageFont.load_default()


def draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), "#2563eb")
    draw = ImageDraw.Draw(image)
    margin = int(size * 0.12)

    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=int(size * 0.18),
        fill="#ffffff",
    )

    chart_box = [
        int(size * 0.22),
        int(size * 0.28),
        int(size * 0.78),
        int(size * 0.66),
    ]
    line = [
        (chart_box[0], int(size * 0.58)),
        (int(size * 0.36), int(size * 0.48)),
        (int(size * 0.49), int(size * 0.54)),
        (int(size * 0.62), int(size * 0.38)),
        (chart_box[2], int(size * 0.32)),
    ]
    draw.line(line, fill="#ef4444", width=max(4, size // 28), joint="curve")

    for x, y in line:
        radius = max(3, size // 48)
        draw.ellipse(
            [x - radius, y - radius, x + radius, y + radius],
            fill="#ef4444",
        )

    label = "MS"
    label_font = font(max(18, size // 6), bold=True)
    bbox = draw.textbbox((0, 0), label, font=label_font)
    text_width = bbox[2] - bbox[0]
    draw.text(
        ((size - text_width) / 2, int(size * 0.68)),
        label,
        fill="#111827",
        font=label_font,
    )

    return image


def draw_splash(width: int = 1242, height: int = 2688) -> Image.Image:
    image = Image.new("RGB", (width, height), "#f7f8fb")
    draw = ImageDraw.Draw(image)
    icon = draw_icon(420)
    image.paste(icon, ((width - 420) // 2, int(height * 0.34)), icon)

    title = "Morning Stock"
    subtitle = "AI Quant Briefing"
    title_font = font(74, bold=True)
    subtitle_font = font(34)

    for text, y, fill, fnt in [
        (title, int(height * 0.53), "#111827", title_font),
        (subtitle, int(height * 0.58), "#64748b", subtitle_font),
    ]:
        bbox = draw.textbbox((0, 0), text, font=fnt)
        text_width = bbox[2] - bbox[0]
        draw.text(((width - text_width) / 2, y), text, fill=fill, font=fnt)

    return image


def main():
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    icon = draw_icon(1024)
    icon.save(ASSET_DIR / "icon.png")
    icon.save(ASSET_DIR / "adaptive_icon_foreground.png")
    draw_splash().save(ASSET_DIR / "splash.png")


if __name__ == "__main__":
    main()
