from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from audit_festival_assets import valid_png as valid_festival_png


PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")


def fit_label_font(
    draw: ImageDraw.ImageDraw,
    label: str,
    max_width: int,
    max_height: int,
    start_size: int,
) -> ImageFont.ImageFont:
    for size in range(start_size, 9, -1):
        font = ImageFont.load_default(size=size)
        left, top, right, bottom = draw.multiline_textbbox(
            (0, 0), label, font=font, spacing=4
        )
        if right - left <= max_width and bottom - top <= max_height:
            return font
    return ImageFont.load_default(size=10)


def build_sheet(
    source_dir: Path, city: str, weather: str, output: Path, festival: str = "none"
) -> None:
    paths = [
        source_dir / f"{festival}_{city}_person_{period}_{weather}.png"
        for period in PERIODS
    ]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing images: {', '.join(missing)}")

    thumb_width = 512
    thumb_height = 918
    label_height = 86
    gutter = 18
    margin = 24
    sheet = Image.new(
        "RGB",
        (
            margin * 2 + thumb_width * 3 + gutter * 2,
            margin * 2 + (thumb_height + label_height) * 2 + gutter,
        ),
        "#171717",
    )
    draw = ImageDraw.Draw(sheet)
    for index, (period, path) in enumerate(zip(PERIODS, paths, strict=True)):
        with Image.open(path) as image:
            if ((festival == "none" and (image.format != "PNG" or image.size != (1536, 2752)))
                    or (festival != "none" and not valid_festival_png(path))):
                raise ValueError(f"Invalid source {path.name}: {image.format} {image.size}")
            thumbnail = image.convert("RGB").resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)

        column = index % 3
        row = index // 3
        x = margin + column * (thumb_width + gutter)
        y = margin + row * (thumb_height + label_height + gutter)
        sheet.paste(thumbnail, (x, y))
        label = f"{period}\n{path.name}"
        font = fit_label_font(
            draw,
            label,
            max_width=thumb_width - 16,
            max_height=label_height - 12,
            start_size=24,
        )
        draw.multiline_text((x + 8, y + thumb_height + 8), label, fill="white", font=font, spacing=4)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("city")
    parser.add_argument("weather")
    parser.add_argument("output", type=Path)
    parser.add_argument("--festival", default="none")
    args = parser.parse_args()
    build_sheet(args.source_dir, args.city, args.weather, args.output, args.festival)


if __name__ == "__main__":
    main()
