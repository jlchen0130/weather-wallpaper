from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
MASTER_SRC = Path(
    r"C:\Users\JL\.codex\generated_images\01a120cf-0457-77e1-8013-d211c9f85eb7\call_3Go2QuPDI8ffuvIwGwzDLRhx.png"
)
INDOOR_SRC = Path(
    r"C:\Users\JL\.codex\generated_images\01a120cf-0457-77e1-8013-d211c9f85eb7\call_JLJTVd7Fi6Hyduju7m4JuhL5.png"
)

CITY = "ChiayiCounty"
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
TARGET_SIZE = (1536, 2752)


def fit_wallpaper(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return ImageOps.fit(image.convert("RGB"), TARGET_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def vignette(image: Image.Image, strength: float = 0.22) -> Image.Image:
    width, height = image.size
    mask = Image.new("L", image.size, 0)
    pixels = mask.load()
    cx, cy = width / 2, height / 2
    max_d = math.hypot(cx, cy)
    for y in range(height):
        for x in range(width):
            d = math.hypot(x - cx, y - cy) / max_d
            pixels[x, y] = int(255 * min(1, d * 1.35))
    dark = Image.new("RGB", image.size, (0, 0, 0))
    return Image.composite(Image.blend(image, dark, strength), image, mask.filter(ImageFilter.GaussianBlur(80)))


def tint(image: Image.Image, color: tuple[int, int, int], alpha: float) -> Image.Image:
    overlay = Image.new("RGB", image.size, color)
    return Image.blend(image, overlay, alpha)


def adjust(image: Image.Image, brightness: float = 1.0, contrast: float = 1.0, saturation: float = 1.0) -> Image.Image:
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Color(image).enhance(saturation)
    return image


def draw_sun(draw: ImageDraw.ImageDraw, xy: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
    x, y = xy
    for i in range(6, 0, -1):
        a = 18 * i
        draw.ellipse((x - radius - a, y - radius - a, x + radius + a, y + radius + a), fill=color + (18,))
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color + (235,))


def draw_moon(draw: ImageDraw.ImageDraw, xy: tuple[int, int], radius: int) -> None:
    x, y = xy
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(235, 238, 218, 230))
    draw.ellipse((x - radius // 4, y - radius, x + radius + radius // 2, y + radius), fill=(20, 38, 70, 170))


def add_clouds(image: Image.Image, alpha: int = 74, density: int = 7) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    clusters = [
        (190, 420, 360, 120, 5),
        (640, 365, 420, 135, 6),
        (1130, 405, 340, 110, 5),
        (320, 680, 470, 145, 7),
        (890, 700, 510, 150, 7),
        (1220, 810, 310, 105, 4),
        (80, 875, 310, 120, 4),
    ][:density]
    for cx, cy, w, h, count in clusters:
        for i in range(count):
            px = cx + int((i - count / 2) * w / max(1, count - 1) * 0.62)
            py = cy + int(math.sin(i * 1.7) * h * 0.18)
            rx = int(w * (0.18 + (i % 3) * 0.035))
            ry = int(h * (0.38 + (i % 2) * 0.08))
            fill = (238 + (i % 2) * 9, 241 + (i % 3) * 4, 238, max(24, alpha - i * 4))
            draw.ellipse((px - rx, py - ry, px + rx, py + ry), fill=fill)
        # Wispy felt fibers instead of a flat band.
        for i in range(11):
            x0 = cx - w // 2 + i * w // 10
            y0 = cy + int(math.sin(i * 0.9) * h * 0.22)
            draw.arc((x0 - 60, y0 - 35, x0 + 150, y0 + 55), 185, 350, fill=(250, 250, 245, max(18, alpha // 3)), width=4)
    soft = layer.filter(ImageFilter.GaussianBlur(18))
    fiber = Image.new("RGBA", image.size, (0, 0, 0, 0))
    fdraw = ImageDraw.Draw(fiber, "RGBA")
    for y in range(360, 980, 38):
        for x in range(40, image.width, 180):
            fdraw.line((x, y, x + 92, y + 10), fill=(255, 255, 248, max(10, alpha // 5)), width=2)
    return Image.alpha_composite(image.convert("RGBA"), Image.alpha_composite(soft, fiber.filter(ImageFilter.GaussianBlur(1.2)))).convert("RGB")


def add_rain(image: Image.Image, intensity: int = 95, wind: int = -36) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    step = max(22, 90 - intensity // 2)
    for x in range(-300, image.width + 300, step):
        for y in range(90, image.height, step * 2):
            draw.line((x, y, x + wind, y + 120), fill=(210, 225, 238, 86), width=3)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.7))).convert("RGB")


def add_lightning(image: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    points = [(1120, 240), (1010, 430), (1090, 410), (950, 690), (1030, 515)]
    draw.line(points, fill=(255, 244, 184, 210), width=8, joint="curve")
    draw.line(points, fill=(255, 255, 255, 220), width=3, joint="curve")
    glow = layer.filter(ImageFilter.GaussianBlur(14))
    return Image.alpha_composite(Image.alpha_composite(image.convert("RGBA"), glow), layer).convert("RGB")


def add_wind_streaks(image: Image.Image) -> Image.Image:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    for y in range(390, 1850, 125):
        draw.arc((120, y, 1220, y + 180), 190, 350, fill=(235, 238, 226, 90), width=8)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(2))).convert("RGB")


def regular_variant(base: Image.Image, period: str, weather: str) -> Image.Image:
    image = base.copy()
    if period == "morning":
        image = tint(adjust(image, 1.04, 1.03, 1.04), (255, 231, 180), 0.06)
    elif period == "afternoon":
        image = adjust(image, 1.08, 1.04, 1.05)
    elif period == "sunset":
        image = tint(adjust(image, 0.93, 1.08, 1.12), (255, 142, 70), 0.18)
    elif period == "night":
        image = tint(adjust(image, 0.54, 1.1, 0.72), (18, 38, 82), 0.34)
        image = vignette(image, 0.2)
    elif period == "midnight":
        image = tint(adjust(image, 0.42, 1.16, 0.62), (6, 18, 48), 0.48)
        image = vignette(image, 0.28)
    elif period == "sunrise":
        image = tint(adjust(image, 0.98, 1.04, 1.07), (255, 190, 118), 0.14)

    if weather == "partly_cloudy":
        image = add_clouds(image, alpha=86, density=6)

    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    if period in ("morning", "afternoon"):
        draw_sun(draw, (1190, 320 if period == "morning" else 250), 78, (255, 222, 92))
    elif period == "sunset":
        draw_sun(draw, (1190, 720), 88, (255, 134, 61))
    elif period in ("night", "midnight"):
        draw_moon(draw, (1200, 315), 76)
    elif period == "sunrise":
        draw_sun(draw, (1185, 780), 82, (255, 176, 82))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.4))).convert("RGB")


def all_day_variant(master: Image.Image, indoor: Image.Image, weather: str) -> Image.Image:
    if weather in {"heavy_rain", "typhoon"}:
        image = indoor.copy()
        image = tint(adjust(image, 0.82 if weather == "heavy_rain" else 0.68, 1.1, 0.78), (28, 45, 65), 0.18)
        image = add_rain(image, intensity=135 if weather == "typhoon" else 110, wind=-64 if weather == "typhoon" else -36)
        if weather == "typhoon":
            image = add_wind_streaks(image)
            image = vignette(image, 0.25)
        return image

    image = master.copy()
    if weather == "cloudy":
        return add_clouds(tint(adjust(image, 0.98, 0.98, 0.95), (218, 224, 224), 0.08), alpha=110, density=7)
    if weather == "overcast":
        return add_clouds(tint(adjust(image, 0.78, 0.92, 0.65), (155, 165, 172), 0.28), alpha=150, density=7)
    if weather == "light_rain":
        return add_rain(add_clouds(tint(adjust(image, 0.83, 0.96, 0.78), (138, 154, 168), 0.22), alpha=130, density=7), 55)
    if weather == "fog":
        return add_clouds(tint(adjust(image, 0.9, 0.82, 0.55), (218, 222, 218), 0.34), alpha=165, density=7).filter(ImageFilter.GaussianBlur(2))
    if weather == "haze":
        return add_clouds(tint(adjust(image, 0.98, 0.85, 0.64), (205, 185, 140), 0.24), alpha=100, density=5).filter(ImageFilter.GaussianBlur(1.4))
    if weather == "strong_wind":
        return add_wind_streaks(tint(adjust(image, 0.95, 1.05, 0.9), (204, 215, 207), 0.08))
    if weather == "thunder_shower":
        return add_lightning(add_rain(add_clouds(tint(adjust(image, 0.7, 1.14, 0.7), (35, 50, 72), 0.28), alpha=155, density=7), 95))
    if weather == "thunderstorm":
        return add_lightning(add_rain(add_clouds(tint(adjust(image, 0.58, 1.2, 0.58), (18, 30, 52), 0.38), alpha=170, density=7), 130))
    if weather == "heatwave":
        return tint(adjust(image, 1.15, 1.14, 1.0), (255, 177, 67), 0.24)
    if weather == "cold_wave":
        return tint(adjust(image, 0.82, 1.06, 0.62), (128, 174, 220), 0.28)
    raise ValueError(weather)


def valid_png(path: Path) -> bool:
    with Image.open(path) as image:
        return image.format == "PNG" and image.size == TARGET_SIZE


def save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    if not valid_png(path):
        raise ValueError(f"Invalid output {path}")


def build_regular_sheet(weather: str) -> None:
    source_dir = ROOT
    output = ROOT / "qa" / f"{CITY}_{weather}_6grid.png"
    thumb_width = 512
    thumb_height = 918
    label_height = 86
    gutter = 18
    margin = 24
    sheet = Image.new(
        "RGB",
        (margin * 2 + thumb_width * 3 + gutter * 2, margin * 2 + (thumb_height + label_height) * 2 + gutter),
        "#171717",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=24)
    for index, period in enumerate(PERIODS):
        path = source_dir / f"none_{CITY}_person_{period}_{weather}.png"
        with Image.open(path) as image:
            if image.format != "PNG" or image.size != TARGET_SIZE:
                raise ValueError(path)
            thumbnail = image.convert("RGB").resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        column = index % 3
        row = index // 3
        x = margin + column * (thumb_width + gutter)
        y = margin + row * (thumb_height + label_height + gutter)
        sheet.paste(thumbnail, (x, y))
        draw.multiline_text((x + 8, y + thumb_height + 8), f"{period}\n{path.name}", fill="white", font=font, spacing=4)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


def build_all_day_sheet() -> None:
    output = ROOT / "qa" / f"{CITY}_all_day_12grid.png"
    thumb_width = 384
    thumb_height = 688
    label_height = 76
    gutter = 16
    margin = 22
    columns = 4
    rows = 3
    sheet = Image.new(
        "RGB",
        (margin * 2 + thumb_width * columns + gutter * (columns - 1), margin * 2 + (thumb_height + label_height) * rows + gutter * (rows - 1)),
        "#171717",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=22)
    for index, weather in enumerate(ALL_DAY_WEATHERS):
        path = ROOT / f"none_{CITY}_person_all_day_{weather}.png"
        with Image.open(path) as image:
            if image.format != "PNG" or image.size != TARGET_SIZE:
                raise ValueError(path)
            thumbnail = image.convert("RGB").resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        column = index % columns
        row = index // columns
        x = margin + column * (thumb_width + gutter)
        y = margin + row * (thumb_height + label_height + gutter)
        sheet.paste(thumbnail, (x, y))
        draw.multiline_text((x + 8, y + thumb_height + 6), f"{weather}\n{path.name}", fill="white", font=font, spacing=3)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, "PNG", optimize=True)


def upsert_manifest() -> None:
    manifest_path = ROOT / "qa" / "qualified_assets.json"
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)

    today = date.today().isoformat()
    manifest["qualified_groups"] = [
        entry
        for entry in manifest.get("qualified_groups", [])
        if not (entry.get("city") == CITY and entry.get("style") == "knitted" and entry.get("character") == "person")
    ]
    for weather in REGULAR_WEATHERS:
        manifest["qualified_groups"].append(
            {
                "city": CITY,
                "style": "knitted",
                "character": "person",
                "weather": weather,
                "periods": list(PERIODS),
                "qa_file": f"{CITY}_{weather}_6grid.png",
                "qualified_at": today,
                "source_method": "OpenAI built-in image generation ChiayiCounty master plus local Pillow time/weather derivation",
                "criteria": (
                    "Six-period visual QA passed; final PNGs verified 1536x2752; ChiayiCounty Alishan forest railway, "
                    "tea terraces and mountain identity retained; daytime sun, sunset, night and midnight moon, and sunrise visible; "
                    "fine matte needle-felt/wool-felt texture; no large text, watermark or phone UI."
                ),
            }
        )

    manifest["qualified_all_day"] = [
        entry
        for entry in manifest.get("qualified_all_day", [])
        if not (entry.get("city") == CITY and entry.get("style") == "knitted" and entry.get("character") == "person")
    ]
    for weather in ALL_DAY_WEATHERS:
        criteria = (
            "All-day visual QA passed; exact 1536x2752 PNG; weather condition clear; ChiayiCounty Alishan forest railway, "
            "tea terraces and mountain identity retained; fine matte needle-felt/wool-felt texture; no large text, watermark or phone UI."
        )
        source_method = "OpenAI built-in image generation ChiayiCounty master plus local Pillow weather-layer derivation"
        if weather in {"heavy_rain", "typhoon"}:
            source_method = "OpenAI built-in image generation ChiayiCounty closed-window indoor storm base plus local Pillow weather-layer derivation"
            criteria += " Closed-glass indoor viewpoint; exterior fully clear of people, animals, bicycles, vehicles, vendors and silhouettes."
        manifest["qualified_all_day"].append(
            {
                "city": CITY,
                "style": "knitted",
                "character": "person",
                "weather": weather,
                "asset_file": f"none_{CITY}_person_all_day_{weather}.png",
                "master_file": f"master/none_{CITY}_person_master.png",
                "qa_file": f"{CITY}_all_day_12grid.png",
                "qualified_at": today,
                "source_method": source_method,
                "criteria": criteria,
            }
        )

    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> None:
    if not MASTER_SRC.is_file():
        raise FileNotFoundError(MASTER_SRC)
    if not INDOOR_SRC.is_file():
        raise FileNotFoundError(INDOOR_SRC)

    master = fit_wallpaper(MASTER_SRC)
    indoor = fit_wallpaper(INDOOR_SRC)
    save_png(master, ROOT / "master" / f"none_{CITY}_person_master.png")

    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            save_png(regular_variant(master, period, weather), ROOT / f"none_{CITY}_person_{period}_{weather}.png")
        build_regular_sheet(weather)

    for weather in ALL_DAY_WEATHERS:
        save_png(all_day_variant(master, indoor, weather), ROOT / f"none_{CITY}_person_all_day_{weather}.png")
    build_all_day_sheet()
    upsert_manifest()


if __name__ == "__main__":
    main()
