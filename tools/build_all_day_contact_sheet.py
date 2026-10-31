from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WEATHERS = (
    "cloudy",
    "overcast",
    "light_rain",
    "heavy_rain",
    "typhoon",
    "fog",
    "haze",
    "strong_wind",
    "thunder_shower",
    "thunderstorm",
    "heatwave",
    "cold_wave",
)


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


def build_sheet(source_dir: Path, city: str, output: Path) -> None:
    paths = [source_dir / f"none_{city}_person_all_day_{weather}.png" for weather in WEATHERS]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing images: {', '.join(missing)}")

    thumb_width = 384
    thumb_height = 688
    label_height = 82
    gutter = 16
    margin = 24
    columns = 4
    rows = 3
    sheet = Image.new(
        "RGB",
        (
            margin * 2 + thumb_width * columns + gutter * (columns - 1),
            margin * 2 + (thumb_height + label_height) * rows + gutter * (rows - 1),
        ),
        "#171717",
    )
    draw = ImageDraw.Draw(sheet)
    for index, (weather, path) in enumerate(zip(WEATHERS, paths, strict=True)):
        with Image.open(path) as image:
            if image.format != "PNG" or image.size != (1536, 2752):
                raise ValueError(f"Invalid source {path.name}: {image.format} {image.size}")
            thumbnail = image.convert("RGB").resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)

        column = index % columns
        row = index // columns
        x = margin + column * (thumb_width + gutter)
        y = margin + row * (thumb_height + label_height + gutter)
        sheet.paste(thumbnail, (x, y))
        label = f"{weather}\n{path.name}"
        font = fit_label_font(
            draw,
            label,
            max_width=thumb_width - 16,
            max_height=label_height - 12,
            start_size=22,
        )
        draw.multiline_text((x + 8, y + thumb_height + 8), label, fill="white", font=font, spacing=4)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("city")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_sheet(args.source_dir, args.city, args.output)


if __name__ == "__main__":
    main()
