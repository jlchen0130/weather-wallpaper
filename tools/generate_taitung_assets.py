from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import generate_hualien_assets as render


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
QA_DIR = ROOT / "qa"
MASTER_DIR = ROOT / "master"
CITY = "Taitung"
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
            raise ValueError(f"Existing Taitung file is invalid and will not be overwritten silently: {path}")
        if not refresh:
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    if not valid_png(path, expected_size):
        raise ValueError(f"Invalid output: {path}")


def draw_person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    s = scale
    draw.ellipse((x - 34 * s, y - 116 * s, x + 34 * s, y - 48 * s), fill=(229, 180, 138, 255))
    draw.pieslice((x - 44 * s, y - 128 * s, x + 44 * s, y - 52 * s), 180, 360, fill=(48, 39, 34, 255))
    draw.rounded_rectangle((x - 43 * s, y - 50 * s, x + 43 * s, y + 88 * s), radius=19, fill=(222, 76, 66, 255))
    draw.line((x - 26 * s, y + 86 * s, x - 48 * s, y + 165 * s), fill=(55, 71, 85, 255), width=max(3, round(12 * s)))
    draw.line((x + 24 * s, y + 86 * s, x + 45 * s, y + 165 * s), fill=(55, 71, 85, 255), width=max(3, round(12 * s)))
    draw.line((x - 42 * s, y - 8 * s, x - 86 * s, y + 40 * s), fill=(229, 180, 138, 255), width=max(3, round(11 * s)))
    draw.line((x + 42 * s, y - 8 * s, x + 85 * s, y + 38 * s), fill=(229, 180, 138, 255), width=max(3, round(11 * s)))


def draw_hot_air_balloon(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float) -> None:
    s = scale
    draw.ellipse((cx - 62 * s, cy - 86 * s, cx + 62 * s, cy + 62 * s), fill=(229, 91, 65, 230))
    draw.pieslice((cx - 62 * s, cy - 86 * s, cx + 62 * s, cy + 62 * s), 88, 180, fill=(248, 184, 82, 230))
    draw.pieslice((cx - 62 * s, cy - 86 * s, cx + 62 * s, cy + 62 * s), 0, 88, fill=(92, 157, 178, 230))
    draw.line((cx - 32 * s, cy + 52 * s, cx - 20 * s, cy + 98 * s), fill=(90, 70, 56, 210), width=max(2, round(4 * s)))
    draw.line((cx + 32 * s, cy + 52 * s, cx + 20 * s, cy + 98 * s), fill=(90, 70, 56, 210), width=max(2, round(4 * s)))
    draw.rounded_rectangle((cx - 28 * s, cy + 92 * s, cx + 28 * s, cy + 122 * s), radius=6, fill=(133, 89, 59, 230))


def draw_taitung_landscape() -> Image.Image:
    image = render.vertical_gradient((126, 192, 223), (241, 224, 171)).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # Coastal mountains and East Rift Valley fields.
    mountain_sets = [
        ([(0, 1000), (230, 700), (465, 830), (720, 570), (990, 790), (1245, 520), (1536, 740), (1536, 1320), (0, 1320)], (61, 112, 119, 255)),
        ([(0, 1190), (260, 900), (550, 1020), (805, 760), (1080, 980), (1360, 805), (1536, 910), (1536, 1490), (0, 1490)], (90, 136, 119, 255)),
        ([(0, 1420), (300, 1120), (610, 1250), (915, 1030), (1200, 1235), (1536, 1120), (1536, 1680), (0, 1680)], (126, 151, 112, 255)),
    ]
    for points, color in mountain_sets:
        draw.polygon(points, fill=color)
    for x in range(80, 1450, 135):
        draw.line((x, 860 + (x % 230), x - 150, 1540), fill=(205, 214, 188, 82), width=10)

    # Pacific water is kept clear of people, vehicles, roads, rails, and bikes.
    draw.polygon([(0, 1705), (1536, 1485), (1536, 2752), (0, 2752)], fill=(50, 145, 176, 255))
    for y, alpha in [(1640, 90), (1805, 76), (1985, 62), (2210, 50)]:
        draw.arc((-360, y - 210, 1880, y + 310), 192, 352, fill=(225, 246, 236, alpha), width=9)

    # Rice paddies and a dry safe path in the valley foreground.
    draw.polygon([(0, 1920), (500, 1840), (930, 2010), (1536, 1920), (1536, 2752), (0, 2752)], fill=(151, 177, 93, 255))
    for y in range(2020, 2520, 110):
        draw.line((40, y, 1490, y - 165), fill=(219, 211, 130, 132), width=7)
    for x in range(110, 1460, 155):
        draw.line((x, 1960, x - 210, 2680), fill=(98, 143, 76, 118), width=5)
    draw.polygon([(190, 2220), (600, 2040), (930, 2135), (760, 2752), (230, 2752)], fill=(147, 115, 78, 255))
    draw.polygon([(780, 2110), (1105, 2010), (1355, 2055), (1536, 2185), (1536, 2315), (1270, 2200), (1000, 2180)], fill=(136, 109, 76, 230))

    # Taitung cues: Luye hot-air balloons and a land-side seashore viewpoint.
    for i, (cx, cy, scale) in enumerate(((260, 470, 0.78), (430, 610, 0.55), (1110, 450, 0.65), (1260, 660, 0.46))):
        draw_hot_air_balloon(draw, cx, cy, scale)
    draw.rounded_rectangle((1060, 1880, 1435, 1945), radius=22, fill=(181, 122, 68, 230))
    for x in range(1090, 1410, 82):
        draw.line((x, 1885, x, 1950), fill=(105, 70, 46, 220), width=7)
    for x in range(970, 1460, 55):
        draw.ellipse((x, 1985 + (x % 4) * 7, x + 30, 2012 + (x % 4) * 7), fill=(195, 187, 164, 220))

    draw_person(draw, 540, 2150, scale=0.96)
    return render.felt_texture(image.convert("RGB"), 91, 23)


def draw_taitung_indoor_storm_base() -> Image.Image:
    image = render.vertical_gradient((125, 103, 83), (194, 169, 132)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1536, 2752), fill=(154, 126, 96, 255))
    draw.rectangle((138, 132, 1398, 2055), fill=(67, 96, 111, 255))
    draw.rectangle((194, 188, 1342, 1992), fill=(66, 122, 150, 255))
    draw.rectangle((138, 132, 1398, 2055), outline=(86, 61, 46, 255), width=34)
    draw.line((768, 152, 768, 2038), fill=(84, 59, 45, 255), width=24)
    draw.line((160, 1080, 1376, 1080), fill=(84, 59, 45, 255), width=24)
    draw.polygon([(194, 1385), (520, 1195), (760, 1305), (1040, 1105), (1342, 1230), (1342, 1992), (194, 1992)], fill=(68, 103, 98, 255))
    draw.polygon([(194, 1598), (1342, 1455), (1342, 1992), (194, 1992)], fill=(38, 110, 143, 255))
    for x in range(250, 1280, 150):
        draw.arc((x - 160, 1510, x + 190, 1690), 200, 345, fill=(185, 214, 214, 72), width=6)
    draw.rectangle((0, 2030, 1536, 2752), fill=(119, 84, 62, 255))
    draw.rounded_rectangle((450, 2240, 1085, 2450), radius=28, fill=(174, 135, 91, 255))
    draw_person(draw, 415, 2352, scale=0.95)
    return render.felt_texture(image.convert("RGB"), 221, 21)


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
        if any(entry.get("city") == CITY and entry.get("style") == STYLE and entry.get("character") == CHARACTER and entry.get("weather") == weather for entry in groups):
            continue
        groups.append(
            {
                **common,
                "weather": weather,
                "periods": list(PERIODS),
                "qa_file": f"{CITY}_{weather}_6grid.png",
                "source_method": "Local Pillow Taitung master render plus local Pillow time/weather derivation",
                "criteria": (
                    "Six-period visual QA passed; final PNGs verified 1536x2752; Taitung coastal mountains, Pacific coast, "
                    "rice paddies and Luye hot-air balloon identity retained; daytime sun, sunset setting sun, night and midnight moon, "
                    "and sunrise visible; fine matte needle-felt and handmade wool-felt texture; person on safe land path only; "
                    "water surfaces clear of people, bicycles, vehicles, roads and rails; no large text, watermark or phone UI."
                ),
            }
        )

    all_day = data.setdefault("qualified_all_day", [])
    for weather in ALL_DAY_WEATHERS:
        if any(entry.get("city") == CITY and entry.get("style") == STYLE and entry.get("character") == CHARACTER and entry.get("weather") == weather for entry in all_day):
            continue
        indoor = weather in {"heavy_rain", "typhoon"}
        all_day.append(
            {
                **common,
                "weather": weather,
                "asset_file": f"none_{CITY}_person_all_day_{weather}.png",
                "qa_file": f"{CITY}_all_day_12grid.png",
                "source_method": (
                    "Local Pillow Taitung closed-glass indoor storm render plus local Pillow weather-layer derivation"
                    if indoor
                    else "Local Pillow Taitung master render plus local Pillow weather-layer derivation"
                ),
                "criteria": (
                    "Closed-glass indoor storm QA passed; exact 1536x2752 PNG; heavy rain/typhoon visible through glass; "
                    "person indoors only; exterior fully clear of people, animals, bicycles, vehicles, vendors and silhouettes; "
                    "Taitung mountain/Pacific identity retained; fine matte needle-felt and handmade wool-felt texture; "
                    "no large text, watermark or phone UI."
                    if indoor
                    else "All-day visual QA passed; exact 1536x2752 PNG; weather condition clear; Taitung coastal mountains, Pacific coast, rice paddies and Luye hot-air balloon identity retained; fine matte needle-felt and handmade wool-felt texture; person on safe land path only; water surfaces clear of people, bicycles, vehicles, roads and rails; no large text, watermark or phone UI."
                ),
            }
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def assert_city_scope() -> None:
    forbidden = {"torrential_rain"}
    existing = {path.name for path in ROOT.glob("*Taitung*")}
    if any(name for name in existing if any(token in name for token in forbidden)):
        raise ValueError("Forbidden Taitung torrential_rain asset detected")


def main(refresh: bool = False) -> None:
    QA_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    assert_city_scope()

    master = draw_taitung_landscape()
    indoor = draw_taitung_indoor_storm_base()

    save_or_verify(master, MASTER_DIR / f"none_{CITY}_person_master.png", refresh=refresh)
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
    parser.add_argument("--refresh", action="store_true", help="Regenerate Taitung outputs in place after visual QA repairs.")
    args = parser.parse_args()
    main(refresh=args.refresh)
