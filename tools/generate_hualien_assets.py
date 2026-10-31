from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
QA_DIR = ROOT / "qa"
MASTER_DIR = ROOT / "master"
CITY = "Hualien"
STYLE = "knitted"
CHARACTER = "person"
SIZE = (1536, 2752)
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
REGULAR_WEATHERS = ("sunny", "partly_cloudy")
ALL_DAY_WEATHERS = (
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


def valid_png(path: Path, expected_size: tuple[int, int] = SIZE) -> bool:
    try:
        with Image.open(path) as image:
            return image.format == "PNG" and image.size == expected_size
    except (OSError, ValueError):
        return False


def save_or_verify(image: Image.Image, path: Path, expected_size: tuple[int, int] = SIZE, refresh: bool = False) -> None:
    if path.exists():
        if not valid_png(path, expected_size):
            raise ValueError(f"Existing Hualien file is invalid and will not be overwritten silently: {path}")
        if not refresh:
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    if not valid_png(path, expected_size):
        raise ValueError(f"Invalid output: {path}")


def vertical_gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    strip = Image.new("RGB", (1, SIZE[1]))
    pixels = strip.load()
    for y in range(SIZE[1]):
        t = y / (SIZE[1] - 1)
        pixels[0, y] = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
    return strip.resize(SIZE)


def blend_color(image: Image.Image, color: tuple[int, int, int], alpha: float) -> Image.Image:
    return Image.blend(image.convert("RGB"), Image.new("RGB", SIZE, color), alpha)


def enhance(image: Image.Image, brightness: float = 1.0, contrast: float = 1.0, color: float = 1.0) -> Image.Image:
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    return ImageEnhance.Color(image).enhance(color)


def felt_texture(image: Image.Image, seed: int = 0, opacity: int = 24) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(0, SIZE[1], 7):
        offset = (y * 13 + seed * 17) % 19
        for x in range(-offset, SIZE[0], 19):
            tone = 245 if ((x * 3 + y * 5 + seed) % 11) else 52
            draw.line(
                (x, y, x + 8, y + 2 + ((x + y) % 3)),
                fill=(tone, tone, tone, opacity),
                width=1,
            )
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.45))).convert("RGB")


def soft_ellipse(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: tuple[int, int, int, int]) -> None:
    draw.ellipse(box, fill=fill)


def draw_hualien_landscape() -> Image.Image:
    image = vertical_gradient((123, 190, 222), (239, 229, 182)).convert("RGBA")
    draw = ImageDraw.Draw(image)

    # Central mountain range and Taroko marble cliffs.
    ranges = [
        ([(0, 980), (210, 690), (420, 800), (650, 565), (880, 730), (1100, 500), (1536, 760), (1536, 1320), (0, 1320)], (62, 112, 118, 255)),
        ([(0, 1170), (250, 870), (520, 980), (770, 700), (1010, 960), (1270, 730), (1536, 900), (1536, 1440), (0, 1440)], (87, 137, 126, 255)),
        ([(0, 1360), (330, 1040), (620, 1190), (860, 940), (1130, 1160), (1536, 1010), (1536, 1580), (0, 1580)], (116, 151, 129, 255)),
    ]
    for points, fill in ranges:
        draw.polygon(points, fill=fill)
    for x in range(80, 1460, 120):
        draw.line((x, 820 + (x % 260), x - 120, 1460), fill=(206, 212, 198, 90), width=12)

    # Pacific coast kept clear of roads, rails, people, vehicles, and bikes.
    draw.polygon([(0, 1710), (1536, 1460), (1536, 2752), (0, 2752)], fill=(58, 146, 171, 255))
    for y, alpha in [(1640, 90), (1775, 80), (1930, 68), (2150, 50)]:
        draw.arc((-420, y - 230, 1950, y + 330), 190, 350, fill=(222, 245, 236, alpha), width=10)

    # Land path and safe viewpoint plaza for the small person.
    draw.polygon([(0, 1970), (430, 1900), (950, 2070), (1536, 1990), (1536, 2752), (0, 2752)], fill=(160, 137, 104, 255))
    draw.polygon([(120, 2085), (540, 1995), (1020, 2130), (1380, 2070), (1536, 2190), (1536, 2752), (0, 2752), (0, 2240)], fill=(116, 159, 101, 255))
    for x in range(20, 1510, 92):
        draw.ellipse((x, 2190 + (x % 70), x + 64, 2248 + (x % 70)), fill=(89, 131, 82, 170))

    # Hualien cue: Qixingtan pebble beach and a Taroko-style red footbridge on land.
    draw.rounded_rectangle((930, 1855, 1410, 1925), radius=24, fill=(161, 57, 50, 255))
    for x in range(965, 1390, 80):
        draw.line((x, 1858, x, 1938), fill=(96, 44, 45, 220), width=8)
    for x in range(210, 820, 50):
        draw.ellipse((x, 2030 + (x % 5) * 7, x + 28, 2054 + (x % 5) * 7), fill=(198, 190, 174, 220))

    draw_person(draw, 730, 2050, scale=1.0)
    return felt_texture(image.convert("RGB"), 73, 22)


def draw_person(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    s = scale
    draw.ellipse((x - 36 * s, y - 120 * s, x + 36 * s, y - 48 * s), fill=(232, 185, 145, 255))
    draw.pieslice((x - 45 * s, y - 132 * s, x + 45 * s, y - 52 * s), 180, 360, fill=(52, 42, 38, 255))
    draw.rounded_rectangle((x - 44 * s, y - 50 * s, x + 44 * s, y + 92 * s), radius=20, fill=(230, 80, 74, 255))
    draw.line((x - 28 * s, y + 90 * s, x - 45 * s, y + 170 * s), fill=(58, 72, 86, 255), width=max(3, round(12 * s)))
    draw.line((x + 25 * s, y + 90 * s, x + 48 * s, y + 170 * s), fill=(58, 72, 86, 255), width=max(3, round(12 * s)))
    draw.line((x - 44 * s, y - 8 * s, x - 90 * s, y + 42 * s), fill=(232, 185, 145, 255), width=max(3, round(12 * s)))
    draw.line((x + 44 * s, y - 8 * s, x + 88 * s, y + 40 * s), fill=(232, 185, 145, 255), width=max(3, round(12 * s)))


def draw_indoor_storm_base() -> Image.Image:
    image = vertical_gradient((114, 99, 85), (194, 174, 143)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1536, 2752), fill=(156, 133, 106, 255))
    draw.rectangle((148, 140, 1388, 2048), fill=(72, 105, 119, 255))
    draw.rectangle((196, 188, 1340, 1990), fill=(68, 126, 148, 255))
    draw.rectangle((148, 140, 1388, 2048), outline=(89, 64, 48, 255), width=34)
    draw.line((768, 156, 768, 2032), fill=(88, 63, 47, 255), width=24)
    draw.line((164, 1080, 1372, 1080), fill=(88, 63, 47, 255), width=24)
    draw.polygon([(196, 1390), (590, 1210), (825, 1310), (1120, 1115), (1340, 1215), (1340, 1990), (196, 1990)], fill=(72, 105, 102, 255))
    draw.polygon([(196, 1605), (1340, 1450), (1340, 1990), (196, 1990)], fill=(43, 112, 142, 255))
    for x in range(260, 1290, 145):
        draw.arc((x - 160, 1510, x + 190, 1680), 200, 345, fill=(185, 215, 214, 72), width=6)
    draw.rectangle((0, 2030, 1536, 2752), fill=(121, 88, 65, 255))
    draw.rounded_rectangle((470, 2230, 1045, 2445), radius=28, fill=(174, 134, 92, 255))
    draw_person(draw, 420, 2350, scale=0.95)
    return felt_texture(image.convert("RGB"), 211, 20)


def add_sun(image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for step in range(8, 0, -1):
        r = radius + step * 22
        draw.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=(*color, 9 + step * 5))
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(*color, 224))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_moon(image: Image.Image, center: tuple[int, int], radius: int) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse((center[0] - radius - 36, center[1] - radius - 36, center[0] + radius + 36, center[1] + radius + 36), fill=(254, 245, 211, 36))
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(244, 237, 204, 224))
    draw.ellipse((center[0] + 4, center[1] - radius, center[0] + radius + 48, center[1] + radius), fill=(24, 38, 76, 154))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_clouds(image: Image.Image, density: int = 6, alpha: int = 120, gray: bool = False) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    color = (219, 226, 226) if gray else (250, 251, 244)
    positions = [(190, 390), (520, 315), (930, 410), (1260, 575), (340, 760), (760, 780), (1100, 890)]
    for i, (cx, cy) in enumerate(positions[:density]):
        for j in range(7):
            rx = 88 + (j % 3) * 28
            ry = 42 + (j % 2) * 17
            ox = (j - 3) * 54
            oy = math.sin(i + j * 1.2) * 21
            soft_ellipse(draw, (round(cx + ox - rx), round(cy + oy - ry), round(cx + ox + rx), round(cy + oy + ry)), (*color, max(32, alpha - j * 7)))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(18))).convert("RGB")


def add_rain(image: Image.Image, count: int, slant: int, width: int, alpha: int = 92) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(count):
        x = (i * 79) % (SIZE[0] + 260) - 130
        y = (i * 151) % (SIZE[1] + 160) - 80
        length = 58 + (i % 6) * 16
        draw.line((x, y, x + slant, y + length), fill=(218, 234, 244, alpha), width=width)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.55))).convert("RGB")


def add_wind(image: Image.Image, alpha: int = 92) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(28):
        y = 530 + (i * 86) % 1500
        x0 = -110 + (i % 6) * 55
        points = [(x0 + step * 185, y + math.sin(step * 0.86 + i) * 24) for step in range(10)]
        draw.line(points, fill=(232, 241, 234, alpha), width=5)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.2))).convert("RGB")


def add_lightning(image: Image.Image, intense: bool) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bolt = [(1190, 205), (1030, 505), (1130, 486), (915, 905), (1010, 610), (905, 665)]
    draw.line(bolt, fill=(255, 243, 174, 230 if intense else 170), width=8 if intense else 5)
    draw.line(bolt, fill=(255, 255, 245, 225), width=3)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.0))).convert("RGB")


def window_mask() -> Image.Image:
    mask = Image.new("L", SIZE, 0)
    draw = ImageDraw.Draw(mask)
    panes = ((196, 188, 750, 1068), (786, 188, 1340, 1068), (196, 1092, 750, 1990), (786, 1092, 1340, 1990))
    for pane in panes:
        draw.rectangle(pane, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(1.2))


def add_window_weather(indoor: Image.Image, weather: str) -> Image.Image:
    base = enhance(indoor, 0.84 if weather == "heavy_rain" else 0.70, 1.08, 0.84)
    base = blend_color(base, (31, 42, 55), 0.12)
    exterior = base.copy()
    exterior = add_rain(exterior, 760 if weather == "heavy_rain" else 980, -36 if weather == "heavy_rain" else -70, 3, 96)
    if weather == "typhoon":
        exterior = add_wind(exterior, 108)
        exterior = add_lightning(exterior, False)
    return Image.composite(exterior, base, window_mask())


def fog_layer(image: Image.Image, alpha: int) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(520, 2400, 230):
        draw.ellipse((-360, y - 135, 1900, y + 155), fill=(224, 228, 222, alpha))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(52))).convert("RGB")


def period_variant(master: Image.Image, period: str, weather: str) -> Image.Image:
    image = master.copy()
    if period == "morning":
        image = blend_color(enhance(image, 1.05, 1.02, 1.03), (255, 239, 206), 0.06)
        image = add_sun(image, (1180, 330), 78, (255, 224, 98))
    elif period == "afternoon":
        image = blend_color(enhance(image, 1.09, 1.03, 1.04), (255, 247, 215), 0.035)
        image = add_sun(image, (1250, 255), 90, (255, 235, 118))
    elif period == "sunset":
        image = Image.blend(enhance(image, 0.92, 1.07, 1.06), vertical_gradient((255, 125, 75), (72, 50, 102)), 0.25)
        image = add_sun(image, (1150, 965), 96, (255, 135, 62))
    elif period == "night":
        image = Image.blend(enhance(image, 0.52, 1.08, 0.72), vertical_gradient((14, 28, 72), (16, 23, 45)), 0.38)
        image = add_moon(image, (1205, 340), 76)
    elif period == "midnight":
        image = Image.blend(enhance(image, 0.38, 1.13, 0.62), vertical_gradient((3, 10, 34), (8, 14, 28)), 0.52)
        image = add_moon(image, (850, 305), 70)
    elif period == "sunrise":
        image = Image.blend(enhance(image, 0.98, 1.04, 1.05), vertical_gradient((255, 190, 120), (255, 236, 186)), 0.18)
        image = add_sun(image, (1060, 1080), 88, (255, 176, 82))
    else:
        raise ValueError(period)
    if weather == "partly_cloudy":
        image = add_clouds(image, 5, 96 if period in {"night", "midnight"} else 130, period in {"night", "midnight"})
    return felt_texture(image, hash((period, weather)) & 255, 14)


def all_day_variant(master: Image.Image, indoor: Image.Image, weather: str) -> Image.Image:
    if weather in {"heavy_rain", "typhoon"}:
        image = add_window_weather(indoor, weather)
        return felt_texture(image, 31 if weather == "heavy_rain" else 32, 14)

    image = master.copy()
    if weather == "cloudy":
        image = add_clouds(blend_color(enhance(image, 0.98, 0.98, 0.94), (220, 228, 228), 0.08), 7, 132, True)
    elif weather == "overcast":
        image = add_clouds(blend_color(enhance(image, 0.78, 0.9, 0.68), (150, 160, 168), 0.28), 7, 174, True)
    elif weather == "light_rain":
        image = add_rain(add_clouds(blend_color(enhance(image, 0.86, 0.95, 0.78), (138, 154, 168), 0.2), 6, 138, True), 360, -30, 2, 78)
    elif weather == "fog":
        image = fog_layer(blend_color(enhance(image, 0.9, 0.82, 0.56), (220, 224, 220), 0.32), 118)
    elif weather == "haze":
        image = fog_layer(blend_color(enhance(image, 0.98, 0.84, 0.66), (212, 184, 132), 0.25), 76)
    elif weather == "strong_wind":
        image = add_wind(blend_color(enhance(image, 0.96, 1.03, 0.9), (205, 218, 210), 0.08), 104)
    elif weather == "thunder_shower":
        image = add_lightning(add_rain(add_clouds(blend_color(enhance(image, 0.70, 1.12, 0.70), (36, 50, 72), 0.28), 7, 150, True), 560, -42, 3, 100), False)
    elif weather == "thunderstorm":
        image = add_lightning(add_rain(add_clouds(blend_color(enhance(image, 0.58, 1.20, 0.58), (18, 30, 52), 0.38), 7, 176, True), 820, -46, 3, 118), True)
    elif weather == "heatwave":
        image = blend_color(add_sun(enhance(image, 1.12, 1.12, 1.0), (1230, 250), 110, (255, 210, 72)), (255, 168, 56), 0.22)
    elif weather == "cold_wave":
        image = fog_layer(blend_color(add_clouds(enhance(image, 0.82, 1.05, 0.62), 5, 88, True), (126, 174, 222), 0.28), 48)
    else:
        raise ValueError(weather)
    return felt_texture(image, hash(weather) & 255, 14)


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
    raise RuntimeError("Rejected flat-geometry Hualien generator cannot qualify assets; use reviewed imagegen originals.")
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
                "source_method": "Local Pillow Hualien master render plus local Pillow time/weather derivation",
                "criteria": (
                    "Six-period visual QA passed; final PNGs verified 1536x2752; Hualien mountain, Taroko gorge, Qixingtan/Pacific coast "
                    "identity retained; daytime sun, sunset setting sun, night and midnight moon, and sunrise visible; fine matte needle-felt "
                    "and handmade wool-felt texture; person on safe land viewpoint only; water surfaces clear of people, bicycles, vehicles, "
                    "roads and rails; no large text, watermark or phone UI."
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
                    "Local Pillow Hualien closed-glass indoor storm render plus local Pillow weather-layer derivation"
                    if indoor
                    else "Local Pillow Hualien master render plus local Pillow weather-layer derivation"
                ),
                "criteria": (
                    "Closed-glass indoor storm QA passed; exact 1536x2752 PNG; heavy rain/typhoon visible through glass; person indoors only; "
                    "exterior fully clear of people, animals, bicycles, vehicles, vendors and silhouettes; Hualien mountain/Pacific identity retained; "
                    "fine matte needle-felt and handmade wool-felt texture; no large text, watermark or phone UI."
                    if indoor
                    else "All-day visual QA passed; exact 1536x2752 PNG; weather condition clear; Hualien mountain, Taroko gorge, Qixingtan/Pacific coast identity retained; fine matte needle-felt and handmade wool-felt texture; person on safe land viewpoint only; water surfaces clear of people, bicycles, vehicles, roads and rails; no large text, watermark or phone UI."
                ),
            }
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(refresh: bool = False) -> None:
    raise RuntimeError("This Hualien generator was rejected by visual QA on 2026-10-10. Do not overwrite reviewed imagegen assets.")
    QA_DIR.mkdir(parents=True, exist_ok=True)
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    master = draw_hualien_landscape()
    indoor = draw_indoor_storm_base()

    save_or_verify(master, MASTER_DIR / f"none_{CITY}_person_master.png", refresh=refresh)
    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            save_or_verify(period_variant(master, period, weather), ROOT / f"none_{CITY}_person_{period}_{weather}.png", refresh=refresh)
        build_regular_sheet(weather, refresh=refresh)

    for weather in ALL_DAY_WEATHERS:
        save_or_verify(all_day_variant(master, indoor, weather), ROOT / f"none_{CITY}_person_all_day_{weather}.png", refresh=refresh)
    build_all_day_sheet(refresh=refresh)
    update_manifest()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Regenerate Hualien outputs in place after visual QA repairs.")
    args = parser.parse_args()
    main(refresh=args.refresh)
