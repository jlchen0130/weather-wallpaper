from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import generate_hualien_assets as render


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
QA_DIR = ROOT / "qa"
MASTER_DIR = ROOT / "master"
CITY = "Penghu"
STYLE = "knitted"
CHARACTER = "person"
SIZE = render.SIZE
PERIODS = render.PERIODS
REGULAR_WEATHERS = render.REGULAR_WEATHERS
ALL_DAY_WEATHERS = render.ALL_DAY_WEATHERS


def valid_png(path: Path, expected_size: tuple[int, int] = SIZE) -> bool:
    try:
        with Image.open(path) as image:
            return image.format == "PNG" and image.size == expected_size
    except (OSError, ValueError):
        return False


def save_or_verify(image: Image.Image, path: Path, expected_size: tuple[int, int] = SIZE, refresh: bool = False) -> None:
    if path.exists():
        if not valid_png(path, expected_size):
            raise ValueError(f"Existing Penghu file is invalid and will not be overwritten silently: {path}")
        if not refresh:
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    if not valid_png(path, expected_size):
        raise ValueError(f"Invalid output: {path}")


def load_master() -> Image.Image:
    path = MASTER_DIR / f"none_{CITY}_person_master.png"
    if not valid_png(path):
        raise FileNotFoundError(f"Verified Penghu master PNG is required before derivation: {path}")
    with Image.open(path) as image:
        return image.convert("RGB")


def draw_penghu_indoor_storm_base() -> Image.Image:
    image = render.vertical_gradient((124, 104, 86), (196, 172, 136)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1536, 2752), fill=(156, 130, 100, 255))
    draw.rectangle((128, 128, 1408, 2060), fill=(68, 94, 109, 255))
    draw.rectangle((186, 190, 1350, 1990), fill=(62, 118, 144, 255))
    draw.rectangle((128, 128, 1408, 2060), outline=(88, 62, 45, 255), width=36)
    draw.line((768, 150, 768, 2040), fill=(86, 61, 45, 255), width=24)
    draw.line((158, 1084, 1378, 1084), fill=(86, 61, 45, 255), width=24)

    # Penghu sea, basalt shore, and bridge are seen only through closed glass.
    draw.rectangle((186, 1240, 1350, 1990), fill=(35, 103, 139, 255))
    draw.polygon([(186, 1500), (420, 1360), (650, 1485), (850, 1325), (1110, 1450), (1350, 1385), (1350, 1990), (186, 1990)], fill=(86, 105, 94, 255))
    draw.arc((420, 1060, 1280, 1450), 190, 352, fill=(220, 226, 221, 205), width=16)
    for x in range(520, 1210, 120):
        draw.line((x, 1288, x - 18, 1500), fill=(210, 214, 208, 170), width=8)
    for x in range(210, 1320, 125):
        draw.arc((x - 150, 1515, x + 195, 1695), 200, 345, fill=(185, 215, 214, 72), width=6)
    for x in range(260, 1300, 115):
        draw.rectangle((x, 1690 + (x % 4) * 11, x + 55, 1775 + (x % 4) * 11), fill=(64, 66, 62, 210))

    draw.rectangle((0, 2035, 1536, 2752), fill=(120, 84, 61, 255))
    draw.rounded_rectangle((450, 2240, 1085, 2452), radius=28, fill=(175, 134, 91, 255))
    render.draw_person(draw, 414, 2352, scale=0.95)
    return render.felt_texture(image.convert("RGB"), 229, 20)


def build_regular_sheet(weather: str, refresh: bool = False) -> None:
    thumb = (512, 918)
    label_h = 86
    gutter = 18
    margin = 24
    sheet_size = (margin * 2 + thumb[0] * 3 + gutter * 2, margin * 2 + (thumb[1] + label_h) * 2 + gutter)
    sheet = Image.new("RGB", sheet_size, "#171717")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=24)
    for index, period in enumerate(PERIODS):
        path = ROOT / f"none_{CITY}_person_{period}_{weather}.png"
        with Image.open(path) as source:
            if source.format != "PNG" or source.size != SIZE:
                raise ValueError(f"Invalid source {path}: {source.format} {source.size}")
            tile = source.convert("RGB").resize(thumb, Image.Resampling.LANCZOS)
        x = margin + (index % 3) * (thumb[0] + gutter)
        y = margin + (index // 3) * (thumb[1] + label_h + gutter)
        sheet.paste(tile, (x, y))
        draw.multiline_text((x + 8, y + thumb[1] + 8), f"{period}\n{path.name[:43]}\n{path.name[43:]}", fill="white", font=font, spacing=3)
    save_or_verify(sheet, QA_DIR / f"{CITY}_{weather}_6grid.png", sheet_size, refresh=refresh)


def build_all_day_sheet(refresh: bool = False) -> None:
    thumb = (384, 688)
    label_h = 76
    gutter = 14
    margin = 20
    cols = 4
    rows = 3
    sheet_size = (margin * 2 + thumb[0] * cols + gutter * (cols - 1), margin * 2 + (thumb[1] + label_h) * rows + gutter * (rows - 1))
    sheet = Image.new("RGB", sheet_size, "#171717")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=22)
    for index, weather in enumerate(ALL_DAY_WEATHERS):
        path = ROOT / f"none_{CITY}_person_all_day_{weather}.png"
        with Image.open(path) as source:
            if source.format != "PNG" or source.size != SIZE:
                raise ValueError(f"Invalid source {path}: {source.format} {source.size}")
            tile = source.convert("RGB").resize(thumb, Image.Resampling.LANCZOS)
        x = margin + (index % cols) * (thumb[0] + gutter)
        y = margin + (index // cols) * (thumb[1] + label_h + gutter)
        sheet.paste(tile, (x, y))
        draw.multiline_text((x + 8, y + thumb[1] + 8), f"{weather}\n{path.name[:34]}\n{path.name[34:]}", fill="white", font=font, spacing=2)
    save_or_verify(sheet, QA_DIR / f"{CITY}_all_day_12grid.png", sheet_size, refresh=refresh)


def update_manifest() -> None:
    path = QA_DIR / "qualified_assets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    common = {
        "city": CITY,
        "style": STYLE,
        "character": CHARACTER,
        "qualified_at": today,
        "master_file": f"master/none_{CITY}_person_master.png",
    }

    groups = data.setdefault("qualified_groups", [])
    for weather in REGULAR_WEATHERS:
        groups[:] = [
            entry
            for entry in groups
            if not (entry.get("city") == CITY and entry.get("style") == STYLE and entry.get("character") == CHARACTER and entry.get("weather") == weather)
        ]
        groups.append(
            {
                **common,
                "weather": weather,
                "periods": list(PERIODS),
                "qa_file": f"{CITY}_{weather}_6grid.png",
                "source_method": "Verified 1536x2752 Gemini Penghu master and sunny_morning original downloads plus local Pillow time/weather derivation",
                "criteria": (
                    "Six-period visual QA passed; final PNGs verified 1536x2752; Penghu basalt coastline, island village, ocean and Penghu Great Bridge identity retained; "
                    "daytime sun, sunset setting sun, night and midnight moon, and sunrise visible; fine matte needle-felt and handmade wool-felt texture; "
                    "people on safe land path/plaza only; sea surfaces clear of people, bicycles, vehicles, roads and rails; no large text, watermark or phone UI."
                ),
            }
        )

    all_day = data.setdefault("qualified_all_day", [])
    for weather in ALL_DAY_WEATHERS:
        all_day[:] = [
            entry
            for entry in all_day
            if not (entry.get("city") == CITY and entry.get("style") == STYLE and entry.get("character") == CHARACTER and entry.get("weather") == weather)
        ]
        indoor = weather in {"heavy_rain", "typhoon"}
        all_day.append(
            {
                **common,
                "weather": weather,
                "asset_file": f"none_{CITY}_person_all_day_{weather}.png",
                "qa_file": f"{CITY}_all_day_12grid.png",
                "source_method": (
                    "Local Pillow Penghu closed-glass indoor storm render plus local Pillow weather-layer derivation"
                    if indoor
                    else "Verified 1536x2752 Gemini Penghu master plus local Pillow weather-layer derivation"
                ),
                "criteria": (
                    "Closed-glass indoor storm QA passed; exact 1536x2752 PNG; heavy rain/typhoon visible through closed glass; "
                    "person indoors only; exterior fully clear of people, animals, bicycles, vehicles, vendors and silhouettes; "
                    "Penghu sea, basalt shore and bridge identity retained; fine matte needle-felt and handmade wool-felt texture; "
                    "no large text, watermark or phone UI."
                    if indoor
                    else "All-day visual QA passed; exact 1536x2752 PNG; weather condition clear; Penghu basalt coastline, island village, ocean and bridge identity retained; fine matte needle-felt and handmade wool-felt texture; people on safe land path/plaza only; sea surfaces clear of people, bicycles, vehicles, roads and rails; no large text, watermark or phone UI."
                ),
            }
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_city_scope() -> None:
    if list(ROOT.glob("*Penghu*torrrential_rain*")) or list(ROOT.glob("*Penghu*torrential_rain*")):
        raise ValueError("Forbidden Penghu torrential_rain asset detected")


def main(refresh: bool = False) -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    assert_city_scope()

    master = load_master()
    indoor = draw_penghu_indoor_storm_base()

    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            save_or_verify(render.period_variant(master, period, weather), ROOT / f"none_{CITY}_person_{period}_{weather}.png", refresh=refresh)
        build_regular_sheet(weather, refresh=refresh)

    for weather in ALL_DAY_WEATHERS:
        source = render.add_window_weather(indoor, weather) if weather in {"heavy_rain", "typhoon"} else render.all_day_variant(master, indoor, weather)
        source = render.felt_texture(source, hash((CITY, weather)) & 255, 14)
        save_or_verify(source, ROOT / f"none_{CITY}_person_all_day_{weather}.png", refresh=refresh)
    build_all_day_sheet(refresh=refresh)
    update_manifest()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Regenerate Penghu outputs in place after visual QA repairs.")
    args = parser.parse_args()
    main(refresh=args.refresh)
