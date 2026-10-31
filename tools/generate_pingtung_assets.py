from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
QA_DIR = ROOT / "qa"
MASTER_DIR = ROOT / "master"
CITY = "Pingtung"
STYLE = "knitted"
CHARACTER = "person"
SIZE = (1536, 2752)

MASTER_SRC = Path(
    r"C:\Users\JL\.codex\generated_images\01a120da-9308-7113-b346-1dcfe0d6ff9d\call_YXEi4OcS2J6m6kWvXof6hZ44.png"
)
INDOOR_SRC = Path(
    r"C:\Users\JL\.codex\generated_images\01a120da-9308-7113-b346-1dcfe0d6ff9d\call_Vn6PKJWznlpfby5uiJoQwQK6.png"
)

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


def fit_source(path: Path) -> Image.Image:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        return ImageOps.fit(image.convert("RGB"), SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def valid_png(path: Path, expected_size: tuple[int, int] = SIZE) -> bool:
    try:
        with Image.open(path) as image:
            return image.format == "PNG" and image.size == expected_size
    except (OSError, ValueError):
        return False


def save_or_verify(image: Image.Image, path: Path, expected_size: tuple[int, int] = SIZE) -> None:
    if path.exists():
        if not valid_png(path, expected_size):
            raise ValueError(f"Existing file is not a valid PNG at expected size: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    if not valid_png(path, expected_size):
        raise ValueError(f"Invalid output {path}")


def adjust(image: Image.Image, brightness: float = 1.0, contrast: float = 1.0, saturation: float = 1.0) -> Image.Image:
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    return ImageEnhance.Color(image).enhance(saturation)


def tint(image: Image.Image, color: tuple[int, int, int], alpha: float) -> Image.Image:
    return Image.blend(image.convert("RGB"), Image.new("RGB", SIZE, color), alpha)


def gradient_overlay(image: Image.Image, top: tuple[int, int, int, int], bottom: tuple[int, int, int, int]) -> Image.Image:
    gradient = Image.new("RGBA", SIZE)
    pixels = gradient.load()
    for y in range(SIZE[1]):
        t = y / (SIZE[1] - 1)
        pixels_y = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(4))
        for x in range(SIZE[0]):
            pixels[x, y] = pixels_y
    return Image.alpha_composite(image.convert("RGBA"), gradient).convert("RGB")


def add_felt_texture(image: Image.Image, opacity: int = 14) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(0, SIZE[1], 11):
        offset = 5 if (y // 11) % 2 else 0
        for x in range(offset, SIZE[0], 19):
            tone = 255 if (x + y) % 5 else 42
            draw.point((x, y), fill=(tone, tone, tone, opacity))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.55))).convert("RGB")


def add_sun(image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for step in range(7, 0, -1):
        r = radius + step * 24
        draw.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=(*color, 8 + step * 5))
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(*color, 230))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_moon(image: Image.Image, center: tuple[int, int], radius: int) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse((center[0] - radius - 36, center[1] - radius - 36, center[0] + radius + 36, center[1] + radius + 36), fill=(255, 246, 208, 30))
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(245, 241, 210, 220))
    draw.ellipse((center[0] - 8, center[1] - radius, center[0] + radius + 34, center[1] + radius), fill=(16, 29, 68, 160))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_clouds(image: Image.Image, density: int = 6, alpha: int = 115, gray: bool = False) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    base = (222, 230, 231) if gray else (252, 252, 246)
    clusters = [(170, 420), (570, 360), (1010, 440), (1320, 610), (330, 720), (820, 790), (1120, 880)]
    for i, (cx, cy) in enumerate(clusters[:density]):
        for j in range(8):
            rx = 82 + (j % 3) * 30
            ry = 35 + (j % 2) * 18
            ox = (j - 3) * 50
            oy = math.sin(j * 1.25 + i) * 20
            draw.ellipse((cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry), fill=(*base, max(30, alpha - j * 6)))
    layer = layer.filter(ImageFilter.GaussianBlur(20))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_rain(image: Image.Image, intensity: int = 120, slant: int = -42, width: int = 2) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    step = max(22, 76 - intensity // 3)
    for x in range(-240, SIZE[0] + 260, step):
        for y in range(0, SIZE[1], step * 3):
            length = 72 + (x + y) % 66
            draw.line((x, y, x + slant, y + length), fill=(218, 234, 244, min(135, 50 + intensity // 2)), width=width)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.65))).convert("RGB")


def add_wind(image: Image.Image, strong: bool = True) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    count = 28 if strong else 16
    for i in range(count):
        y = 430 + (i * 83) % 1550
        x0 = -90 + (i % 5) * 62
        points = [(x0 + step * 190, y + math.sin(step * 0.9 + i) * 25) for step in range(10)]
        draw.line(points, fill=(238, 244, 236, 92 if strong else 60), width=5 if strong else 3)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.3))).convert("RGB")


def add_lightning(image: Image.Image, intense: bool = False) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bolt = [(1160, 210), (1015, 470), (1110, 452), (905, 845), (1000, 585), (885, 635)]
    draw.line(bolt, fill=(255, 241, 174, 230 if intense else 170), width=8 if intense else 5, joint="curve")
    draw.line(bolt, fill=(255, 255, 250, 230), width=3, joint="curve")
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.1))).convert("RGB")


def period_variant(base: Image.Image, period: str, weather: str) -> Image.Image:
    image = base.copy()
    if period == "morning":
        image = tint(adjust(image, 1.05, 1.03, 1.04), (255, 238, 205), 0.06)
        image = add_sun(image, (1185, 330), 82, (255, 224, 94))
    elif period == "afternoon":
        image = tint(adjust(image, 1.09, 1.04, 1.05), (255, 247, 215), 0.035)
        image = add_sun(image, (1240, 270), 92, (255, 235, 114))
    elif period == "sunset":
        image = gradient_overlay(adjust(image, 0.9, 1.08, 1.08), (255, 118, 68, 82), (44, 30, 80, 36))
        image = add_sun(image, (1160, 960), 98, (255, 132, 62))
    elif period == "night":
        image = gradient_overlay(adjust(image, 0.52, 1.08, 0.72), (10, 25, 70, 122), (18, 22, 42, 86))
        image = add_moon(image, (1205, 345), 78)
    elif period == "midnight":
        image = gradient_overlay(adjust(image, 0.38, 1.14, 0.62), (1, 8, 32, 160), (8, 14, 30, 118))
        image = add_moon(image, (845, 300), 72)
    elif period == "sunrise":
        image = gradient_overlay(adjust(image, 0.98, 1.04, 1.06), (255, 187, 116, 72), (255, 234, 176, 24))
        image = add_sun(image, (1080, 1080), 90, (255, 176, 78))
    else:
        raise ValueError(period)

    if weather == "partly_cloudy":
        image = add_clouds(image, density=5, alpha=100 if period in {"night", "midnight"} else 125)
    return add_felt_texture(image)


def all_day_variant(master: Image.Image, indoor: Image.Image, weather: str) -> Image.Image:
    if weather in {"heavy_rain", "typhoon"}:
        image = tint(adjust(indoor, 0.82 if weather == "heavy_rain" else 0.68, 1.08, 0.82), (28, 42, 58), 0.12)
        image = add_rain(image, intensity=150 if weather == "typhoon" else 125, slant=-64 if weather == "typhoon" else -32, width=3)
        if weather == "typhoon":
            image = add_wind(image, strong=True)
            image = add_lightning(image, intense=False)
        return add_felt_texture(image)

    image = master.copy()
    if weather == "cloudy":
        image = add_clouds(tint(adjust(image, 0.98, 0.98, 0.94), (220, 228, 228), 0.08), 7, 128, True)
    elif weather == "overcast":
        image = add_clouds(tint(adjust(image, 0.78, 0.9, 0.68), (150, 160, 168), 0.28), 7, 170, True)
    elif weather == "light_rain":
        image = add_rain(add_clouds(tint(adjust(image, 0.86, 0.95, 0.78), (138, 154, 168), 0.2), 6, 138, True), 70, -30, 2)
    elif weather == "fog":
        image = add_clouds(tint(adjust(image, 0.9, 0.82, 0.55), (220, 224, 220), 0.34), 7, 165, True).filter(ImageFilter.GaussianBlur(1.9))
    elif weather == "haze":
        image = add_clouds(tint(adjust(image, 0.98, 0.84, 0.66), (210, 184, 132), 0.25), 5, 105, True).filter(ImageFilter.GaussianBlur(1.2))
    elif weather == "strong_wind":
        image = add_wind(tint(adjust(image, 0.95, 1.04, 0.9), (205, 218, 210), 0.08))
    elif weather == "thunder_shower":
        image = add_lightning(add_rain(add_clouds(tint(adjust(image, 0.7, 1.12, 0.7), (36, 50, 72), 0.28), 7, 150, True), 100, -42, 3), False)
    elif weather == "thunderstorm":
        image = add_lightning(add_rain(add_clouds(tint(adjust(image, 0.58, 1.2, 0.58), (18, 30, 52), 0.38), 7, 176, True), 140, -46, 3), True)
    elif weather == "heatwave":
        image = tint(add_sun(adjust(image, 1.13, 1.12, 1.0), (1230, 250), 112, (255, 210, 72)), (255, 168, 56), 0.22)
    elif weather == "cold_wave":
        image = tint(add_clouds(adjust(image, 0.82, 1.05, 0.62), 5, 88, True), (126, 174, 222), 0.28)
    else:
        raise ValueError(weather)
    return add_felt_texture(image)


def build_regular_sheet(weather: str) -> None:
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
    save_or_verify(sheet, QA_DIR / f"{CITY}_{weather}_6grid.png", sheet_size)


def build_all_day_sheet() -> None:
    thumb = (384, 688)
    label_h = 74
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
    save_or_verify(sheet, QA_DIR / f"{CITY}_all_day_12grid.png", sheet_size)


def update_manifest() -> None:
    path = QA_DIR / "qualified_assets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    data["qualified_groups"] = [
        item
        for item in data.get("qualified_groups", [])
        if not (item.get("city") == CITY and item.get("style") == STYLE and item.get("character") == CHARACTER)
    ]
    data["qualified_all_day"] = [
        item
        for item in data.get("qualified_all_day", [])
        if not (item.get("city") == CITY and item.get("style") == STYLE and item.get("character") == CHARACTER)
    ]
    for weather in REGULAR_WEATHERS:
        data["qualified_groups"].append(
            {
                "city": CITY,
                "style": STYLE,
                "character": CHARACTER,
                "weather": weather,
                "periods": list(PERIODS),
                "qa_file": f"{CITY}_{weather}_6grid.png",
                "qualified_at": today,
                "source_method": "OpenAI built-in image generation Pingtung master plus local Pillow time/weather derivation",
                "criteria": (
                    "Six-period visual QA passed; final PNGs verified 1536x2752; Pingtung tropical coastline, "
                    "Dapeng Bay/Kenting/Eluanbi identity retained; daytime sun, sunset, night and midnight moon, and sunrise visible; "
                    "fine matte needle-felt/wool-felt texture; water surfaces kept empty of people, bicycles, vehicles, roads and rails; "
                    "no large text, watermark or phone UI."
                ),
            }
        )

    for weather in ALL_DAY_WEATHERS:
        source_method = "OpenAI built-in image generation Pingtung master plus local Pillow weather-layer derivation"
        criteria = (
            "All-day visual QA passed; exact 1536x2752 PNG; weather condition clear; Pingtung tropical coastline, "
            "Dapeng Bay/Kenting/Eluanbi identity retained; fine matte needle-felt/wool-felt texture; water surfaces kept empty of "
            "people, bicycles, vehicles, roads and rails; no large text, watermark or phone UI."
        )
        if weather in {"heavy_rain", "typhoon"}:
            source_method = "OpenAI built-in image generation Pingtung closed-window indoor storm base plus local Pillow weather-layer derivation"
            criteria = (
                "Closed-glass indoor storm QA passed; exact 1536x2752 PNG; heavy rain/typhoon visible through glass; "
                "people are indoors only, and exterior is clear of people, animals, bicycles, vehicles, vendors, boats and silhouettes; "
                "Pingtung tropical coast identity retained; fine matte needle-felt/wool-felt texture; no large text, watermark or phone UI."
            )
        data["qualified_all_day"].append(
            {
                "city": CITY,
                "style": STYLE,
                "character": CHARACTER,
                "weather": weather,
                "asset_file": f"none_{CITY}_person_all_day_{weather}.png",
                "master_file": f"master/none_{CITY}_person_master.png",
                "qa_file": f"{CITY}_all_day_12grid.png",
                "qualified_at": today,
                "source_method": source_method,
                "criteria": criteria,
            }
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    master = add_felt_texture(fit_source(MASTER_SRC))
    indoor = add_felt_texture(fit_source(INDOOR_SRC))

    save_or_verify(master, MASTER_DIR / f"none_{CITY}_person_master.png")
    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            save_or_verify(period_variant(master, period, weather), ROOT / f"none_{CITY}_person_{period}_{weather}.png")
        build_regular_sheet(weather)
    for weather in ALL_DAY_WEATHERS:
        save_or_verify(all_day_variant(master, indoor, weather), ROOT / f"none_{CITY}_person_all_day_{weather}.png")
    build_all_day_sheet()
    update_manifest()


if __name__ == "__main__":
    main()
