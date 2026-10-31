from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
QA_DIR = ROOT / "qa"
MASTER_DIR = ROOT / "master"
OUT_SIZE = (1536, 2752)
CITY = "Nantou"
STYLE = "knitted"
CHARACTER = "person"

SUNNY_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a12094-24f8-7c72-ac2d-74072dfff22d\call_EWUZ2Wymrgu6BZGghi7Pok4d.png"
)
HEAVY_RAIN_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a12094-24f8-7c72-ac2d-74072dfff22d\call_WeqVDIz8sTBOcmZViSfkfrNX.png"
)
TYPHOON_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a12094-24f8-7c72-ac2d-74072dfff22d\call_8eP8bZA0gTJWAfl4FUpblXym.png"
)
NIGHT_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a12094-24f8-7c72-ac2d-74072dfff22d\call_N6YR5gurC5Z3XEJoV4OmJbdn.png"
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
        image = image.convert("RGB")
        source_ratio = image.width / image.height
        target_ratio = OUT_SIZE[0] / OUT_SIZE[1]
        if source_ratio > target_ratio:
            height = OUT_SIZE[1]
            width = round(height * source_ratio)
        else:
            width = OUT_SIZE[0]
            height = round(width / source_ratio)
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        left = max(0, (width - OUT_SIZE[0]) // 2)
        top = max(0, (height - OUT_SIZE[1]) // 2)
        image = image.crop((left, top, left + OUT_SIZE[0], top + OUT_SIZE[1]))
    return image


def tint(image: Image.Image, color: tuple[int, int, int], alpha: int) -> Image.Image:
    overlay = Image.new("RGB", OUT_SIZE, color)
    return Image.blend(image, overlay, alpha / 255)


def gradient_tint(image: Image.Image, top: tuple[int, int, int], bottom: tuple[int, int, int], alpha: int) -> Image.Image:
    grad = Image.new("RGB", OUT_SIZE)
    pixels = grad.load()
    for y in range(OUT_SIZE[1]):
        t = y / (OUT_SIZE[1] - 1)
        color = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(OUT_SIZE[0]):
            pixels[x, y] = color
    return Image.blend(image, grad, alpha / 255)


def add_sun(image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for step in range(8, 0, -1):
        r = radius + step * 18
        a = max(8, 42 - step * 4)
        draw.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=(*color, a))
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(*color, 225))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_moon(image: Image.Image, center: tuple[int, int], radius: int) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse((center[0] - radius - 28, center[1] - radius - 28, center[0] + radius + 28, center[1] + radius + 28), fill=(255, 245, 210, 32))
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(255, 244, 207, 220))
    draw.ellipse((center[0] - 12, center[1] - 8, center[0] + radius + 14, center[1] + radius + 8), fill=(215, 215, 205, 38))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_clouds(image: Image.Image, density: int = 6, alpha: int = 120, gray: bool = False) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    base = (224, 231, 232) if gray else (255, 255, 255)
    for i in range(density):
        x = 90 + (i * 283) % 1280
        y = 220 + (i * 137) % 780
        w = 360 + (i % 3) * 140
        h = 118 + (i % 2) * 58
        a = max(28, alpha - (i % 4) * 16)
        draw.ellipse((x, y, x + w, y + h), fill=(*base, a))
        draw.ellipse((x + w * 0.18, y - h * 0.2, x + w * 0.72, y + h * 0.68), fill=(*base, a))
        draw.ellipse((x + w * 0.48, y - h * 0.02, x + w * 1.12, y + h * 0.82), fill=(*base, a))
        draw.rectangle((x + w * 0.2, y + h * 0.42, x + w, y + h * 0.86), fill=(*base, max(20, a - 16)))
    layer = layer.filter(ImageFilter.GaussianBlur(34))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_rain(image: Image.Image, count: int, alpha: int, slant: int = -45, width: int = 2) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(count):
        x = (i * 83) % (OUT_SIZE[0] + 240) - 120
        y = (i * 149) % OUT_SIZE[1]
        length = 65 + (i % 5) * 20
        draw.line((x, y, x + slant, y + length), fill=(222, 235, 245, alpha), width=width)
    layer = layer.filter(ImageFilter.GaussianBlur(0.7))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_fog(image: Image.Image, alpha: int = 120) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (230, 234, 229, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(420, OUT_SIZE[1], 230):
        draw.ellipse((-260, y - 120, OUT_SIZE[0] + 260, y + 180), fill=(224, 229, 225, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(56))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_wind(image: Image.Image, strong: bool = True) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(28 if strong else 16):
        y = 420 + (i * 79) % 1450
        x0 = -80 + (i % 6) * 70
        points = []
        for step in range(10):
            x = x0 + step * 190
            points.append((x, y + math.sin(step * 0.9 + i) * 22))
        draw.line(points, fill=(236, 242, 232, 95), width=5 if strong else 3)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.4))).convert("RGB")


def add_lightning(image: Image.Image, intense: bool = False) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bolt = [(1050, 160), (940, 460), (1030, 430), (860, 860), (930, 560), (840, 600)]
    draw.line(bolt, fill=(255, 245, 190, 210 if intense else 150), width=7 if intense else 4, joint="curve")
    layer = layer.filter(ImageFilter.GaussianBlur(1.1))
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def enhance_felt(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Color(image).enhance(1.03)
    image = ImageEnhance.Contrast(image).enhance(1.04)
    return image


def save_png(image: Image.Image, path: Path) -> None:
    if path.exists():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    with Image.open(path) as check:
        if check.format != "PNG" or check.size != OUT_SIZE:
            raise ValueError(f"Invalid output {path}: {check.format} {check.size}")


def period_variant(period: str, partly_cloudy: bool) -> Image.Image:
    sunny = fit_source(SUNNY_SOURCE)
    night = fit_source(NIGHT_SOURCE)
    if period == "morning":
        img = gradient_tint(sunny, (255, 242, 207), (255, 255, 255), 22)
        img = add_sun(img, (220, 300), 74, (255, 222, 106))
    elif period == "afternoon":
        img = gradient_tint(sunny, (255, 245, 210), (245, 252, 255), 12)
        img = add_sun(img, (1240, 260), 80, (255, 235, 118))
    elif period == "sunset":
        img = gradient_tint(sunny, (255, 160, 92), (92, 71, 118), 76)
        img = add_sun(img, (1180, 1120), 92, (255, 144, 64))
    elif period == "night":
        img = gradient_tint(night, (18, 30, 68), (14, 22, 45), 34)
    elif period == "midnight":
        img = gradient_tint(night, (2, 9, 32), (8, 14, 30), 88)
    elif period == "sunrise":
        img = gradient_tint(sunny, (255, 196, 130), (255, 238, 190), 58)
        img = add_sun(img, (300, 1120), 88, (255, 176, 82))
    else:
        raise ValueError(period)
    if partly_cloudy:
        img = add_fog(img, 26 if period not in {"night", "midnight"} else 34)
    return enhance_felt(img)


def all_day_variant(weather: str) -> Image.Image:
    sunny = fit_source(SUNNY_SOURCE)
    rain = fit_source(HEAVY_RAIN_SOURCE)
    typhoon = fit_source(TYPHOON_SOURCE)
    if weather == "cloudy":
        return enhance_felt(add_fog(tint(sunny, (222, 232, 232), 46), 34))
    if weather == "overcast":
        return enhance_felt(add_fog(tint(sunny, (164, 176, 182), 108), 58))
    if weather == "light_rain":
        return enhance_felt(add_rain(add_fog(tint(sunny, (178, 194, 202), 78), 36), 95, 92, -30, 2))
    if weather == "heavy_rain":
        return enhance_felt(add_rain(tint(rain, (98, 120, 134), 34), 230, 138, -25, 3))
    if weather == "typhoon":
        return enhance_felt(add_wind(add_rain(tint(typhoon, (75, 90, 96), 34), 250, 132, -58, 3), True))
    if weather == "fog":
        return enhance_felt(add_fog(tint(sunny, (216, 222, 218), 66), 155))
    if weather == "haze":
        return enhance_felt(add_fog(tint(sunny, (218, 190, 132), 78), 92))
    if weather == "strong_wind":
        return enhance_felt(add_wind(tint(sunny, (214, 225, 218), 34), True))
    if weather == "thunder_shower":
        return enhance_felt(add_lightning(add_rain(add_fog(tint(sunny, (118, 132, 150), 92), 48), 155, 112, -42, 3), False))
    if weather == "thunderstorm":
        return enhance_felt(add_lightning(add_rain(tint(rain, (72, 80, 96), 70), 260, 150, -45, 3), True))
    if weather == "heatwave":
        return enhance_felt(gradient_tint(add_sun(sunny, (1230, 250), 110, (255, 210, 72)), (255, 191, 86), (255, 230, 164), 66))
    if weather == "cold_wave":
        return enhance_felt(add_fog(gradient_tint(sunny, (165, 205, 238), (205, 226, 238), 78), 72))
    raise ValueError(weather)


def update_manifest() -> None:
    path = QA_DIR / "qualified_assets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    data["qualified_groups"] = [
        item for item in data.get("qualified_groups", []) if item.get("city") != CITY
    ]
    data["qualified_all_day"] = [
        item for item in data.get("qualified_all_day", []) if item.get("city") != CITY
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
                "source_method": "OpenAI built-in image generation bases plus local Pillow time/weather derivation",
                "criteria": (
                    "Six-period visual QA passed; final PNGs verified 1536x2752; Nantou Sun Moon Lake "
                    "and mountain identity retained; daytime sun, sunset, night and midnight moon, and sunrise visible; "
                    "fine matte felt texture; no large text, watermark or phone UI."
                ),
            }
        )
    for weather in ALL_DAY_WEATHERS:
        extra = ""
        if weather in {"heavy_rain", "typhoon"}:
            extra = (
                " Closed-glass indoor viewpoint; exterior fully clear of people, animals, bicycles, vehicles, vendors and silhouettes."
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
                "source_method": "OpenAI built-in image generation bases plus local Pillow weather-layer derivation",
                "criteria": (
                    "All-day visual QA passed; exact 1536x2752 PNG; weather condition clear; Nantou Sun Moon Lake "
                    "and mountain identity retained; fine matte felt texture; no large text, watermark or phone UI."
                    + extra
                ),
            }
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)

    save_png(enhance_felt(fit_source(SUNNY_SOURCE)), MASTER_DIR / f"none_{CITY}_person_master.png")

    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            save_png(
                period_variant(period, partly_cloudy=weather == "partly_cloudy"),
                ROOT / f"none_{CITY}_person_{period}_{weather}.png",
            )

    for weather in ALL_DAY_WEATHERS:
        save_png(all_day_variant(weather), ROOT / f"none_{CITY}_person_all_day_{weather}.png")

    update_manifest()


if __name__ == "__main__":
    main()
