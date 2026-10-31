from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from audit_festival_assets import all_day_weathers, valid_png
from build_weather_contact_sheet import fit_label_font


def build_sheet(source_dir: Path, city: str, festival: str, output: Path) -> None:
    weathers = all_day_weathers(city, festival)
    paths = [
        source_dir / f"{festival}_{city}_person_all_day_{weather}.png"
        for weather in weathers
    ]
    invalid = [path.name for path in paths if not valid_png(path)]
    if invalid:
        raise ValueError(f"Missing or invalid images: {', '.join(invalid)}")

    width, height, label_height, gutter, margin = 512, 918, 80, 18, 24
    columns = 3
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (margin * 2 + width * columns + gutter * (columns - 1),
         margin * 2 + (height + label_height) * rows + gutter * (rows - 1)),
        "#171717",
    )
    draw = ImageDraw.Draw(sheet)
    for index, (weather, path) in enumerate(zip(weathers, paths, strict=True)):
        with Image.open(path) as source:
            thumbnail = source.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
        x = margin + (index % columns) * (width + gutter)
        y = margin + (index // columns) * (height + label_height + gutter)
        sheet.paste(thumbnail, (x, y))
        label = f"{weather}\n{path.name}"
        font = fit_label_font(draw, label, width - 16, label_height - 12, 24)
        draw.multiline_text((x + 8, y + height + 8), label, fill="white", font=font, spacing=4)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("city")
    parser.add_argument("festival")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_sheet(args.source_dir, args.city, args.festival, args.output)


if __name__ == "__main__":
    main()
