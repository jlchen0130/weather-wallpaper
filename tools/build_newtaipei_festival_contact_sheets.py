from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from audit_newtaipei_festival_assets import all_day_weathers


CITY = "NewTaipei"
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
REGULAR_WEATHERS = ("sunny", "partly_cloudy")
EXPECTED_SIZE = (1536, 2752)


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


def open_valid_png(path: Path) -> Image.Image:
    image = Image.open(path)
    image.load()
    if image.format != "PNG" or image.size != EXPECTED_SIZE:
        raise ValueError(f"Invalid source {path.name}: {image.format} {image.size}")
    return image


def paste_labeled_thumb(
    sheet: Image.Image,
    draw: ImageDraw.ImageDraw,
    path: Path,
    label: str,
    x: int,
    y: int,
    thumb_width: int,
    thumb_height: int,
    label_height: int,
    font_size: int,
) -> None:
    with open_valid_png(path) as image:
        thumbnail = image.convert("RGB").resize(
            (thumb_width, thumb_height), Image.Resampling.LANCZOS
        )
    sheet.paste(thumbnail, (x, y))
    font = fit_label_font(
        draw,
        label,
        max_width=thumb_width - 16,
        max_height=label_height - 12,
        start_size=font_size,
    )
    draw.multiline_text(
        (x + 8, y + thumb_height + 8), label, fill="white", font=font, spacing=4
    )


def build_regular_sheet(source_dir: Path, festival: str, weather: str, output: Path) -> None:
    paths = [
        source_dir / f"{festival}_{CITY}_person_{period}_{weather}.png"
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
        column = index % 3
        row = index // 3
        x = margin + column * (thumb_width + gutter)
        y = margin + row * (thumb_height + label_height + gutter)
        paste_labeled_thumb(
            sheet,
            draw,
            path,
            f"{period}\n{path.name}",
            x,
            y,
            thumb_width,
            thumb_height,
            label_height,
            24,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


def build_all_day_sheet(source_dir: Path, festival: str, output: Path) -> None:
    expected_weathers = all_day_weathers(festival)
    paths = [
        source_dir / f"{festival}_{CITY}_person_all_day_{weather}.png"
        for weather in expected_weathers
    ]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing images: {', '.join(missing)}")

    thumb_width = 384
    thumb_height = 688
    label_height = 82
    gutter = 16
    margin = 24
    columns = min(4, len(paths))
    rows = (len(paths) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (
            margin * 2 + thumb_width * columns + gutter * (columns - 1),
            margin * 2 + (thumb_height + label_height) * rows + gutter * (rows - 1),
        ),
        "#171717",
    )
    draw = ImageDraw.Draw(sheet)
    for index, (weather, path) in enumerate(zip(expected_weathers, paths, strict=True)):
        column = index % columns
        row = index // columns
        x = margin + column * (thumb_width + gutter)
        y = margin + row * (thumb_height + label_height + gutter)
        paste_labeled_thumb(
            sheet,
            draw,
            path,
            f"{weather}\n{path.name}",
            x,
            y,
            thumb_width,
            thumb_height,
            label_height,
            22,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("festival")
    args = parser.parse_args()

    qa_dir = args.source_dir / "qa"
    for weather in REGULAR_WEATHERS:
        build_regular_sheet(
            args.source_dir,
            args.festival,
            weather,
            qa_dir / f"{args.festival}_{CITY}_{weather}_6grid.png",
        )
    build_all_day_sheet(
        args.source_dir,
        args.festival,
        qa_dir / f"{args.festival}_{CITY}_all_day_{len(all_day_weathers(args.festival))}grid.png",
    )


if __name__ == "__main__":
    main()
