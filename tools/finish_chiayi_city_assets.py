from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
QA_DIR = ROOT / "qa"
MASTER_DIR = ROOT / "master"
OUT_SIZE = (1536, 2752)
CITY = "ChiayiCity"
STYLE = "knitted"
CHARACTER = "person"

SUNNY_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a120bc-9fbf-7301-8e77-317a5ba1e7a8\call_jw44b2CiCsAe5jxXin3Oob78.png"
)
NIGHT_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a120bc-9fbf-7301-8e77-317a5ba1e7a8\call_wxUNJN4PTiYo9T4dOsHDMamU.png"
)
HEAVY_RAIN_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a120bc-9fbf-7301-8e77-317a5ba1e7a8\call_DwT0OhHZ5f7wnGIjYxRxSEYI.png"
)
TYPHOON_SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a120bc-9fbf-7301-8e77-317a5ba1e7a8\call_UIizme3vHjfamB4dDWkwfy3s.png"
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
        scale = max(OUT_SIZE[0] / image.width, OUT_SIZE[1] / image.height)
        resized = image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )
        left = (resized.width - OUT_SIZE[0]) // 2
        top = (resized.height - OUT_SIZE[1]) // 2
        return resized.crop((left, top, left + OUT_SIZE[0], top + OUT_SIZE[1]))


def tint(image: Image.Image, color: tuple[int, int, int], alpha: int) -> Image.Image:
    overlay = Image.new("RGB", OUT_SIZE, color)
    return Image.blend(image.convert("RGB"), overlay, alpha / 255)


def gradient_tint(
    image: Image.Image,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
    alpha: int,
) -> Image.Image:
    gradient = Image.new("RGB", OUT_SIZE)
    pixels = gradient.load()
    for y in range(OUT_SIZE[1]):
        t = y / (OUT_SIZE[1] - 1)
        color = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
        for x in range(OUT_SIZE[0]):
            pixels[x, y] = color
    return Image.blend(image.convert("RGB"), gradient, alpha / 255)


def add_sun(image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for step in range(8, 0, -1):
        r = radius + step * 22
        a = max(8, 42 - step * 4)
        draw.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=(*color, a))
    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        fill=(*color, 226),
    )
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_moon(image: Image.Image, center: tuple[int, int], radius: int) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(
        (center[0] - radius - 34, center[1] - radius - 34, center[0] + radius + 34, center[1] + radius + 34),
        fill=(255, 244, 205, 32),
    )
    draw.ellipse((center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius), fill=(255, 244, 205, 210))
    draw.ellipse(
        (center[0] - 8, center[1] - radius, center[0] + radius + 32, center[1] + radius // 2),
        fill=(20, 38, 78, 94),
    )
    return Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")


def add_clouds(image: Image.Image, density: int = 6, alpha: int = 126, gray: bool = False) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    base = (224, 231, 232) if gray else (255, 255, 255)
    for i in range(density):
        x = 80 + (i * 271) % 1260
        y = 215 + (i * 139) % 760
        w = 350 + (i % 3) * 135
        h = 105 + (i % 2) * 60
        a = max(28, alpha - (i % 4) * 14)
        draw.ellipse((x, y, x + w, y + h), fill=(*base, a))
        draw.ellipse((x + w * 0.16, y - h * 0.23, x + w * 0.70, y + h * 0.70), fill=(*base, a))
        draw.ellipse((x + w * 0.48, y - h * 0.04, x + w * 1.08, y + h * 0.82), fill=(*base, a))
        draw.rectangle((x + w * 0.16, y + h * 0.42, x + w, y + h * 0.88), fill=(*base, max(22, a - 18)))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(30))).convert("RGB")


def add_rain(image: Image.Image, count: int, alpha: int, slant: int = -42, width: int = 2) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(count):
        x = (i * 79) % (OUT_SIZE[0] + 260) - 130
        y = (i * 151) % OUT_SIZE[1]
        length = 64 + (i % 5) * 22
        draw.line((x, y, x + slant, y + length), fill=(222, 235, 245, alpha), width=width)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.7))).convert("RGB")


def add_fog(image: Image.Image, alpha: int = 116) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (230, 234, 229, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(390, OUT_SIZE[1], 220):
        draw.ellipse((-270, y - 120, OUT_SIZE[0] + 270, y + 180), fill=(224, 229, 225, alpha))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(58))).convert("RGB")


def add_wind(image: Image.Image, strong: bool = True) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(30 if strong else 16):
        y = 410 + (i * 81) % 1500
        x0 = -120 + (i % 6) * 75
        points = [(x0 + step * 185, y + math.sin(step * 0.9 + i) * 24) for step in range(10)]
        draw.line(points, fill=(236, 242, 232, 92), width=5 if strong else 3)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.4))).convert("RGB")


def add_lightning(image: Image.Image, intense: bool = False) -> Image.Image:
    layer = Image.new("RGBA", OUT_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bolt = [(1105, 170), (968, 465), (1062, 438), (872, 875), (950, 570), (842, 620)]
    draw.line(bolt, fill=(255, 245, 190, 220 if intense else 158), width=8 if intense else 5, joint="curve")
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.1))).convert("RGB")


def enhance_felt(image: Image.Image) -> Image.Image:
    image = ImageEnhance.Color(image).enhance(1.03)
    image = ImageEnhance.Contrast(image).enhance(1.04)
    return image


def save_png(image: Image.Image, path: Path, expected_size: tuple[int, int] = OUT_SIZE) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    with Image.open(path) as check:
        if check.format != "PNG" or check.size != expected_size:
            raise ValueError(f"Invalid output {path}: {check.format} {check.size}")


def save_or_verify_png(image: Image.Image, path: Path, expected_size: tuple[int, int] = OUT_SIZE) -> None:
    if path.exists():
        with Image.open(path) as check:
            if check.format != "PNG" or check.size != expected_size:
                raise ValueError(f"Existing invalid output {path}: {check.format} {check.size}")
        return
    save_png(image, path, expected_size)


def period_variant(period: str, partly_cloudy: bool) -> Image.Image:
    sunny = fit_source(SUNNY_SOURCE)
    night = fit_source(NIGHT_SOURCE)
    if period == "morning":
        image = gradient_tint(sunny, (255, 242, 207), (255, 255, 255), 20)
        image = add_sun(image, (225, 315), 72, (255, 224, 108))
    elif period == "afternoon":
        image = gradient_tint(sunny, (255, 246, 216), (245, 252, 255), 12)
        image = add_sun(image, (1248, 265), 82, (255, 235, 118))
    elif period == "sunset":
        image = gradient_tint(sunny, (255, 154, 92), (92, 69, 118), 76)
        image = add_sun(image, (1165, 1110), 94, (255, 140, 64))
    elif period == "night":
        image = gradient_tint(night, (18, 31, 70), (14, 22, 44), 30)
    elif period == "midnight":
        image = gradient_tint(night, (2, 9, 32), (8, 14, 30), 88)
    elif period == "sunrise":
        image = gradient_tint(sunny, (255, 196, 130), (255, 239, 190), 58)
        image = add_sun(image, (305, 1125), 88, (255, 176, 82))
    else:
        raise ValueError(period)
    if partly_cloudy:
        image = add_clouds(image, density=4, alpha=112 if period not in {"night", "midnight"} else 84)
    return enhance_felt(image)


def all_day_variant(weather: str) -> Image.Image:
    sunny = fit_source(SUNNY_SOURCE)
    heavy = fit_source(HEAVY_RAIN_SOURCE)
    typhoon = fit_source(TYPHOON_SOURCE)
    if weather == "cloudy":
        return enhance_felt(add_clouds(tint(sunny, (222, 232, 232), 44), 6, 128, True))
    if weather == "overcast":
        return enhance_felt(add_clouds(tint(sunny, (164, 176, 182), 108), 7, 164, True))
    if weather == "light_rain":
        return enhance_felt(add_rain(add_clouds(tint(sunny, (178, 194, 202), 78), 5, 138, True), 95, 88, -30, 2))
    if weather == "heavy_rain":
        return enhance_felt(add_rain(tint(heavy, (94, 116, 132), 24), 210, 112, -22, 2))
    if weather == "typhoon":
        return enhance_felt(add_wind(add_rain(tint(typhoon, (72, 88, 98), 22), 235, 124, -58, 3), True))
    if weather == "fog":
        return enhance_felt(add_fog(tint(sunny, (216, 222, 218), 66), 155))
    if weather == "haze":
        return enhance_felt(add_fog(tint(sunny, (218, 190, 132), 78), 92))
    if weather == "strong_wind":
        return enhance_felt(add_wind(tint(sunny, (214, 225, 218), 34), True))
    if weather == "thunder_shower":
        return enhance_felt(add_lightning(add_rain(add_clouds(tint(sunny, (118, 132, 150), 92), 5, 146, True), 150, 104, -42, 3), False))
    if weather == "thunderstorm":
        return enhance_felt(add_lightning(add_rain(add_clouds(tint(sunny, (72, 80, 96), 94), 7, 178, True), 245, 128, -45, 3), True))
    if weather == "heatwave":
        return enhance_felt(gradient_tint(add_sun(sunny, (1230, 250), 110, (255, 210, 72)), (255, 191, 86), (255, 230, 164), 66))
    if weather == "cold_wave":
        return enhance_felt(add_fog(gradient_tint(sunny, (165, 205, 238), (205, 226, 238), 78), 72))
    raise ValueError(weather)


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
            if source.format != "PNG" or source.size != OUT_SIZE:
                raise ValueError(f"Invalid source {path}: {source.format} {source.size}")
            tile = source.convert("RGB").resize(thumb, Image.Resampling.LANCZOS)
        x = margin + (index % 3) * (thumb[0] + gutter)
        y = margin + (index // 3) * (thumb[1] + label_h + gutter)
        sheet.paste(tile, (x, y))
        draw.multiline_text((x + 8, y + thumb[1] + 8), f"{period}\n{path.name[:43]}\n{path.name[43:]}", fill="white", font=font, spacing=3)
    save_or_verify_png(sheet, QA_DIR / f"{CITY}_{weather}_6grid.png", sheet_size)


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
            if source.format != "PNG" or source.size != OUT_SIZE:
                raise ValueError(f"Invalid source {path}: {source.format} {source.size}")
            tile = source.convert("RGB").resize(thumb, Image.Resampling.LANCZOS)
        x = margin + (index % cols) * (thumb[0] + gutter)
        y = margin + (index // cols) * (thumb[1] + label_h + gutter)
        sheet.paste(tile, (x, y))
        draw.multiline_text((x + 8, y + thumb[1] + 8), f"{weather}\n{path.name[:34]}\n{path.name[34:]}", fill="white", font=font, spacing=2)
    save_or_verify_png(sheet, QA_DIR / f"{CITY}_all_day_12grid.png", sheet_size)


def update_manifest() -> None:
    path = QA_DIR / "qualified_assets.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    data["qualified_groups"] = [item for item in data.get("qualified_groups", []) if item.get("city") != CITY]
    data["qualified_all_day"] = [item for item in data.get("qualified_all_day", []) if item.get("city") != CITY]
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
                "source_method": "OpenAI built-in image generation ChiayiCity bases plus local Pillow time/weather derivation",
                "criteria": (
                    "Six-period visual QA passed; final PNGs verified 1536x2752; ChiayiCity Hinoki Village and "
                    "Alishan Forest Railway identity retained; daytime sun, sunset, night and midnight moon, and sunrise visible; "
                    "fine matte needle-felt/wool-felt texture; no large text, watermark or phone UI."
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
                "source_method": "OpenAI built-in image generation ChiayiCity bases plus local Pillow weather-layer derivation",
                "criteria": (
                    "All-day visual QA passed; exact 1536x2752 PNG; weather condition clear; ChiayiCity Hinoki Village and "
                    "Alishan Forest Railway identity retained; fine matte needle-felt/wool-felt texture; no large text, watermark or phone UI."
                    + extra
                ),
            }
        )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    QA_DIR.mkdir(parents=True, exist_ok=True)

    save_or_verify_png(enhance_felt(fit_source(SUNNY_SOURCE)), MASTER_DIR / f"none_{CITY}_person_master.png")
    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            save_or_verify_png(
                period_variant(period, partly_cloudy=weather == "partly_cloudy"),
                ROOT / f"none_{CITY}_person_{period}_{weather}.png",
            )
        build_regular_sheet(weather)
    for weather in ALL_DAY_WEATHERS:
        save_or_verify_png(all_day_variant(weather), ROOT / f"none_{CITY}_person_all_day_{weather}.png")
    build_all_day_sheet()
    update_manifest()


if __name__ == "__main__":
    main()
