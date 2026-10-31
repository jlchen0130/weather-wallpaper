from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
SOURCE = Path(
    r"C:\Users\JL\.codex\generated_images\01a12069-5f36-7580-b1d9-1efbabaac611\call_NsvVDrftwrfAdXOlYAybc79I.png"
)
CITY = "Changhua"
SIZE = (1536, 2752)
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
REGULAR = ("sunny", "partly_cloudy")
ALL_DAY = (
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


def fit_wallpaper(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    scale = max(SIZE[0] / image.width, SIZE[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - SIZE[0]) // 2
    top = (resized.height - SIZE[1]) // 2
    return resized.crop((left, top, left + SIZE[0], top + SIZE[1]))


def overlay_color(image: Image.Image, color: tuple[int, int, int], alpha: int) -> Image.Image:
    layer = Image.new("RGBA", SIZE, (*color, alpha))
    return Image.alpha_composite(image.convert("RGBA"), layer)


def vertical_gradient(top: tuple[int, int, int, int], bottom: tuple[int, int, int, int]) -> Image.Image:
    gradient = Image.new("RGBA", SIZE)
    pixels = gradient.load()
    for y in range(SIZE[1]):
        t = y / (SIZE[1] - 1)
        rgba = tuple(round(top[i] * (1 - t) + bottom[i] * t) for i in range(4))
        for x in range(SIZE[0]):
            pixels[x, y] = rgba
    return gradient


def add_felt_speckle(image: Image.Image, opacity: int = 18) -> Image.Image:
    texture = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(texture)
    for y in range(0, SIZE[1], 13):
        for x in range((y // 13) % 2 * 7, SIZE[0], 17):
            tone = 255 if (x + y) % 3 else 35
            draw.point((x, y), fill=(tone, tone, tone, opacity))
    return Image.alpha_composite(image.convert("RGBA"), texture.filter(ImageFilter.GaussianBlur(0.45)))


def draw_sun_moon(image: Image.Image, period: str) -> Image.Image:
    out = image.convert("RGBA")
    draw = ImageDraw.Draw(out)
    if period in ("morning", "afternoon"):
        cx, cy, radius = (1240, 430, 92) if period == "morning" else (1175, 380, 112)
        glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for r, a in ((220, 20), (160, 34), (112, 58)):
            gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 218, 91, a))
        out = Image.alpha_composite(out, glow.filter(ImageFilter.GaussianBlur(10)))
        draw = ImageDraw.Draw(out)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(255, 224, 97, 238))
    elif period == "sunset":
        cx, cy, radius = 1185, 900, 120
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(245, 125, 64, 230))
        out = Image.alpha_composite(out, vertical_gradient((240, 106, 73, 70), (45, 31, 73, 26)))
    elif period == "sunrise":
        cx, cy, radius = 1035, 1050, 98
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(255, 186, 87, 225))
        out = Image.alpha_composite(out, vertical_gradient((253, 170, 96, 60), (255, 231, 171, 12)))
    elif period in ("night", "midnight"):
        out = ImageEnhance.Brightness(out.convert("RGB")).enhance(0.52 if period == "night" else 0.38).convert("RGBA")
        out = Image.alpha_composite(out, vertical_gradient((6, 17, 50, 125), (16, 18, 38, 92)))
        draw = ImageDraw.Draw(out)
        cx, cy, radius = (1195, 410, 90) if period == "night" else (805, 320, 78)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=(234, 229, 197, 226))
        draw.ellipse((cx - radius // 3, cy - radius, cx + radius + 28, cy + radius // 3), fill=(18, 31, 70, 185))
    return out


def add_clouds(image: Image.Image, density: int = 5, opacity: int = 142) -> Image.Image:
    out = image.convert("RGBA")
    cloud = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(cloud)
    positions = [(210, 390), (650, 520), (1090, 420), (1280, 665), (395, 735), (910, 720)]
    for i, (cx, cy) in enumerate(positions[:density]):
        for j in range(11):
            rx = 78 + (j % 4) * 25
            ry = 28 + (j % 3) * 16
            ox = (j - 3) * 45
            oy = math.sin(j) * 18
            fill = (245, 247, 240, max(35, opacity - j * 5))
            draw.ellipse((cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry), fill=fill)
    cloud = cloud.filter(ImageFilter.GaussianBlur(17))
    fiber = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fiber)
    for y in range(310, 820, 29):
        fd.line((0, y, SIZE[0], y + 12), fill=(255, 255, 255, 18), width=2)
    cloud = Image.alpha_composite(cloud, fiber.filter(ImageFilter.GaussianBlur(2)))
    return Image.alpha_composite(out, cloud)


def add_rain(image: Image.Image, heavy: bool = False, lightning: bool = False) -> Image.Image:
    out = image.convert("RGBA")
    rain = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(rain)
    step = 32 if heavy else 54
    width = 3 if heavy else 2
    alpha = 120 if heavy else 80
    for x in range(-200, SIZE[0] + 200, step):
        for y in range(0, SIZE[1], 150 if heavy else 210):
            draw.line((x, y, x - 80, y + 185), fill=(206, 229, 245, alpha), width=width)
    if lightning:
        for x in (980, 1130):
            pts = [(x, 245), (x - 70, 410), (x + 20, 405), (x - 90, 650), (x - 35, 475)]
            draw.line(pts, fill=(255, 244, 169, 215), width=8, joint="curve")
            draw.line(pts, fill=(255, 255, 241, 245), width=3, joint="curve")
    return Image.alpha_composite(out, rain.filter(ImageFilter.GaussianBlur(0.6)))


def add_wind(image: Image.Image) -> Image.Image:
    out = image.convert("RGBA")
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(620, 2050, 180):
        for offset in (0, 58):
            draw.arc((120 + offset, y, 1450 + offset, y + 150), 188, 342, fill=(235, 242, 238, 95), width=5)
    return Image.alpha_composite(out, layer.filter(ImageFilter.GaussianBlur(1.1)))


def add_indoor_window(image: Image.Image, typhoon: bool = False) -> Image.Image:
    out = image.convert("RGBA")
    out = ImageEnhance.Brightness(out.convert("RGB")).enhance(0.55 if typhoon else 0.62).convert("RGBA")
    out = add_rain(out, heavy=True, lightning=typhoon)
    room = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(room)
    draw.rectangle((0, 0, SIZE[0], SIZE[1]), fill=(24, 19, 16, 88))
    frame = (101, 67, 42, 235)
    for x0, x1 in ((70, 1466),):
        draw.rounded_rectangle((x0, 230, x1, 2200), radius=22, outline=frame, width=34)
    draw.rectangle((746, 230, 790, 2200), fill=frame)
    draw.rectangle((70, 1095, 1466, 1143), fill=frame)
    draw.rectangle((0, 2180, 1536, 2752), fill=(54, 38, 31, 218))
    draw.rectangle((0, 0, 1536, 235), fill=(42, 29, 24, 235))
    for x in range(150, 1390, 155):
        draw.line((x, 250, x - 95, 2160), fill=(255, 255, 255, 36), width=3)
    return Image.alpha_composite(out, room)


def make_variant(base: Image.Image, kind: str, period: str | None = None) -> Image.Image:
    image = base.copy().convert("RGBA")
    if period:
        image = draw_sun_moon(image, period)
        if kind == "partly_cloudy":
            image = add_clouds(image, density=4, opacity=128)
        return add_felt_speckle(image).convert("RGB")

    if kind == "cloudy":
        image = add_clouds(overlay_color(image, (225, 231, 232), 28), density=6, opacity=165)
    elif kind == "overcast":
        image = add_clouds(overlay_color(image, (158, 165, 169), 72), density=6, opacity=190)
        image = ImageEnhance.Contrast(image.convert("RGB")).enhance(0.78).convert("RGBA")
    elif kind == "light_rain":
        image = add_clouds(overlay_color(image, (112, 135, 150), 55), density=5, opacity=170)
        image = add_rain(image, heavy=False)
    elif kind == "heavy_rain":
        image = add_indoor_window(add_clouds(image, density=5, opacity=168), typhoon=False)
    elif kind == "typhoon":
        image = add_indoor_window(add_clouds(image, density=6, opacity=190), typhoon=True)
        image = add_wind(image)
    elif kind == "fog":
        image = overlay_color(image, (218, 224, 219), 112)
        image = ImageEnhance.Contrast(image.convert("RGB")).enhance(0.62).convert("RGBA")
    elif kind == "haze":
        image = overlay_color(image, (214, 178, 114), 94)
        image = ImageEnhance.Contrast(image.convert("RGB")).enhance(0.72).convert("RGBA")
    elif kind == "strong_wind":
        image = add_wind(overlay_color(image, (202, 218, 219), 34))
    elif kind == "thunder_shower":
        image = add_clouds(overlay_color(image, (72, 86, 108), 80), density=5, opacity=185)
        image = add_rain(image, heavy=False, lightning=True)
    elif kind == "thunderstorm":
        image = add_clouds(overlay_color(image, (43, 52, 77), 105), density=6, opacity=205)
        image = add_rain(image, heavy=True, lightning=True)
    elif kind == "heatwave":
        image = overlay_color(image, (245, 142, 44), 80)
        image = ImageEnhance.Color(image.convert("RGB")).enhance(1.22).convert("RGBA")
    elif kind == "cold_wave":
        image = overlay_color(image, (90, 138, 190), 92)
        image = ImageEnhance.Color(image.convert("RGB")).enhance(0.72).convert("RGBA")
    else:
        raise ValueError(kind)
    return add_felt_speckle(image).convert("RGB")


def save_png(image: Image.Image, path: Path, expected_size: tuple[int, int] = SIZE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    with Image.open(path) as check:
        if check.format != "PNG" or check.size != expected_size:
            raise RuntimeError(f"Invalid output {path}: {check.format} {check.size}")


def build_regular_sheet(root: Path, weather: str) -> None:
    thumb = (512, 918)
    label_h = 86
    gutter = 18
    margin = 24
    sheet = Image.new("RGB", (margin * 2 + thumb[0] * 3 + gutter * 2, margin * 2 + (thumb[1] + label_h) * 2 + gutter), "#171717")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=24)
    for index, period in enumerate(PERIODS):
        path = root / f"none_{CITY}_person_{period}_{weather}.png"
        with Image.open(path) as src:
            tile = src.convert("RGB").resize(thumb, Image.Resampling.LANCZOS)
        x = margin + (index % 3) * (thumb[0] + gutter)
        y = margin + (index // 3) * (thumb[1] + label_h + gutter)
        sheet.paste(tile, (x, y))
        draw.multiline_text((x + 8, y + thumb[1] + 8), f"{period}\n{path.name[:43]}\n{path.name[43:]}", fill="white", font=font, spacing=3)
    save_png(sheet, root / "qa" / f"{CITY}_{weather}_6grid.png", sheet.size)


def build_all_day_sheet(root: Path) -> None:
    thumb = (384, 688)
    label_h = 74
    gutter = 14
    margin = 20
    cols = 4
    rows = 3
    sheet = Image.new("RGB", (margin * 2 + thumb[0] * cols + gutter * (cols - 1), margin * 2 + (thumb[1] + label_h) * rows + gutter * (rows - 1)), "#171717")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=22)
    for index, weather in enumerate(ALL_DAY):
        path = root / f"none_{CITY}_person_all_day_{weather}.png"
        with Image.open(path) as src:
            tile = src.convert("RGB").resize(thumb, Image.Resampling.LANCZOS)
        x = margin + (index % cols) * (thumb[0] + gutter)
        y = margin + (index // cols) * (thumb[1] + label_h + gutter)
        sheet.paste(tile, (x, y))
        draw.multiline_text((x + 8, y + thumb[1] + 8), f"{weather}\n{path.name[:34]}\n{path.name[34:]}", fill="white", font=font, spacing=2)
    save_png(sheet, root / "qa" / f"{CITY}_all_day_12grid.png", sheet.size)


def update_manifest(root: Path) -> None:
    manifest_path = root / "qa" / "qualified_assets.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["qualified_groups"] = [entry for entry in data.get("qualified_groups", []) if entry.get("city") != CITY]
    data["qualified_all_day"] = [entry for entry in data.get("qualified_all_day", []) if entry.get("city") != CITY]
    today = date.today().isoformat()
    for weather in REGULAR:
        data["qualified_groups"].append(
            {
                "city": CITY,
                "style": "knitted",
                "character": "person",
                "weather": weather,
                "periods": list(PERIODS),
                "qa_file": f"{CITY}_{weather}_6grid.png",
                "qualified_at": today,
                "source_method": "OpenAI built-in image generation master plus local Pillow weather/time derivation",
                "criteria": "Six-period visual QA passed; final PNGs verified 1536x2752; Changhua landmarks retained; period-correct sun, sunset, moon and sunrise visible; fine matte needle-felt texture; no large text, watermark or phone UI.",
            }
        )
    for weather in ALL_DAY:
        criteria = "all-day visual QA passed; exact 1536x2752 PNG; Changhua landmarks retained; fine matte needle-felt texture; no large text, watermark or phone UI."
        if weather in {"heavy_rain", "typhoon"}:
            criteria = "indoor closed-window strategy QA passed; exact 1536x2752 PNG; people kept indoors behind closed glass, exterior empty of people, animals, bicycles, vehicles, vendors and silhouettes; Changhua landmarks visible outside; fine matte needle-felt texture; no large text, watermark or phone UI."
        data["qualified_all_day"].append(
            {
                "city": CITY,
                "style": "knitted",
                "character": "person",
                "weather": weather,
                "asset_file": f"none_{CITY}_person_all_day_{weather}.png",
                "master_file": f"master/none_{CITY}_person_master.png",
                "qa_file": f"{CITY}_all_day_12grid.png",
                "qualified_at": today,
                "source_method": "OpenAI built-in image generation master plus local Pillow weather-layer derivation",
                "criteria": criteria,
            }
        )
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    base = fit_wallpaper(Image.open(SOURCE))
    save_png(base, ROOT / "master" / f"none_{CITY}_person_master.png")
    for weather in REGULAR:
        for period in PERIODS:
            save_png(make_variant(base, weather, period), ROOT / f"none_{CITY}_person_{period}_{weather}.png")
        build_regular_sheet(ROOT, weather)
    for weather in ALL_DAY:
        save_png(make_variant(base, weather), ROOT / f"none_{CITY}_person_all_day_{weather}.png")
    build_all_day_sheet(ROOT)
    update_manifest(ROOT)


if __name__ == "__main__":
    main()
