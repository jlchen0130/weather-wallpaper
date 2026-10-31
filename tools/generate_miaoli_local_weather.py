from __future__ import annotations

import argparse
import math
import random
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


SIZE = (1536, 2752)
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
WEATHERS = (
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


def rng_for(label: str) -> random.Random:
    return random.Random(0x4D49414F ^ sum((index + 1) * ord(char) for index, char in enumerate(label)))


def validate(image: Image.Image) -> Image.Image:
    if image.size != SIZE:
        raise ValueError(f"Expected {SIZE}, got {image.size}")
    return image.convert("RGB")


def color_grade(image: Image.Image, tint: tuple[int, int, int], opacity: int, contrast: float = 1.0, saturation: float = 1.0) -> Image.Image:
    graded = ImageEnhance.Color(image).enhance(saturation)
    graded = ImageEnhance.Contrast(graded).enhance(contrast)
    wash = Image.new("RGB", image.size, tint)
    return Image.blend(graded, wash, opacity / 255)


def fibrous_fill(size: tuple[int, int], color: tuple[int, int, int], seed: int, strength: int = 24) -> Image.Image:
    noise = Image.effect_noise(size, 34).filter(ImageFilter.GaussianBlur(1.4))
    lo = tuple(max(0, channel - strength) for channel in color)
    hi = tuple(min(255, channel + strength) for channel in color)
    return ImageOps.colorize(noise, lo, hi).convert("RGBA")


def cloud_overlay(label: str, clusters: list[tuple[int, int, int, int]], tone: tuple[int, int, int], opacity: int = 220, size: tuple[int, int] = SIZE) -> Image.Image:
    rng = rng_for(label)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for cx, cy, width, height in clusters:
        for _ in range(18):
            rx = rng.randint(max(45, width // 8), max(70, width // 3))
            ry = rng.randint(max(28, height // 8), max(55, height // 3))
            x = cx + rng.randint(-width // 2, width // 2) - rx
            y = cy + rng.randint(-height // 3, height // 3) - ry
            draw.ellipse((x, y, x + rx * 2, y + ry * 2), fill=rng.randint(175, 245))
    mask = mask.filter(ImageFilter.GaussianBlur(28))
    texture = fibrous_fill(size, tone, rng.randint(0, 2**31 - 1), 20)
    texture.putalpha(ImageChops.multiply(mask, Image.new("L", size, opacity)))

    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow_mask = ImageChops.offset(mask, 0, 24).filter(ImageFilter.GaussianBlur(20))
    shadow.putalpha(ImageChops.multiply(shadow_mask, Image.new("L", size, min(110, opacity // 2))))
    dark = Image.new("RGBA", size, tuple(max(0, c - 55) for c in tone) + (255,))
    dark.putalpha(shadow.getchannel("A"))
    return Image.alpha_composite(dark, texture)


def add_clouds(image: Image.Image, label: str, clusters: list[tuple[int, int, int, int]], tone: tuple[int, int, int], opacity: int = 220) -> Image.Image:
    return Image.alpha_composite(image.convert("RGBA"), cloud_overlay(label, clusters, tone, opacity, image.size)).convert("RGB")


def add_rain(image: Image.Image, label: str, density: int, slant: int, alpha: int, y_start: int = 260) -> Image.Image:
    rng = rng_for(label)
    width_px, height_px = image.size
    rain = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(rain)
    for _ in range(density):
        x = rng.randint(-120, width_px + 120)
        y = rng.randint(y_start, height_px - 80)
        length = rng.randint(55, 150)
        width = rng.choice((1, 1, 2, 2, 3))
        draw.line((x, y, x + slant, y + length), fill=(220, 235, 242, rng.randint(alpha // 2, alpha)), width=width)
    rain = rain.filter(ImageFilter.GaussianBlur(0.6))
    return Image.alpha_composite(image.convert("RGBA"), rain).convert("RGB")


def add_fog(image: Image.Image, label: str, strength: int = 180) -> Image.Image:
    rng = rng_for(label)
    fog = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(fog)
    for index, y in enumerate((650, 920, 1180, 1460, 1740, 2050)):
        height = rng.randint(170, 320)
        draw.ellipse((-350, y - height // 2, 1150, y + height // 2), fill=(218, 228, 225, max(35, strength - index * 16)))
        draw.ellipse((420, y - height // 3, 1900, y + height), fill=(230, 234, 229, max(30, strength - index * 18)))
    fog = fog.filter(ImageFilter.GaussianBlur(95))
    return Image.alpha_composite(image.convert("RGBA"), fog).convert("RGB")


def add_lightning(image: Image.Image, label: str, count: int) -> Image.Image:
    rng = rng_for(label)
    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    sharp = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    sharp_draw = ImageDraw.Draw(sharp)
    for index in range(count):
        x = 470 + index * 430 + rng.randint(-110, 110)
        y = 260 + rng.randint(-40, 80)
        points = [(x, y)]
        for step in range(rng.randint(5, 8)):
            x += rng.randint(-95, 85)
            y += rng.randint(95, 165)
            points.append((x, y))
        glow_draw.line(points, fill=(210, 225, 255, 190), width=34, joint="curve")
        sharp_draw.line(points, fill=(244, 246, 255, 245), width=7, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(28))
    return Image.alpha_composite(Image.alpha_composite(image.convert("RGBA"), glow), sharp).convert("RGB")


def add_wind(image: Image.Image, label: str) -> Image.Image:
    rng = rng_for(label)
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for _ in range(46):
        y = rng.randint(140, 2380)
        x = rng.randint(-300, 1150)
        length = rng.randint(260, 720)
        amp = rng.randint(12, 42)
        points = []
        for step in range(24):
            px = x + length * step / 23
            py = y + math.sin(step / 23 * math.pi * 2) * amp
            points.append((px, py))
        draw.line(points, fill=(232, 237, 222, rng.randint(45, 100)), width=rng.choice((2, 3, 4)))
    for _ in range(85):
        x = rng.randint(0, SIZE[0])
        y = rng.randint(780, SIZE[1] - 200)
        draw.ellipse((x, y, x + rng.randint(8, 22), y + rng.randint(3, 8)), fill=(188, 205, 137, rng.randint(80, 145)))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.8))).convert("RGB")


def heat_shimmer(image: Image.Image) -> Image.Image:
    source = image.copy()
    result = image.copy()
    for y in range(350, 1420, 8):
        offset = int(math.sin(y / 24) * 6)
        strip = source.crop((0, y, SIZE[0], min(y + 8, SIZE[1])))
        result.paste(strip, (offset, y))
    return result


def frost_edges(image: Image.Image, label: str) -> Image.Image:
    rng = rng_for(label)
    layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for side in (0, SIZE[0]):
        for _ in range(46):
            x = rng.randint(0, 180) if side == 0 else rng.randint(SIZE[0] - 180, SIZE[0])
            y = rng.randint(0, SIZE[1])
            radius = rng.randint(18, 70)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(225, 242, 246, rng.randint(35, 90)), width=rng.randint(2, 7))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(2.2))).convert("RGB")


def blend_reference_sky(
    image: Image.Image,
    reference: Image.Image,
    opacity: int,
    limit: int = 1080,
    preserve: tuple[int, int, int] | None = None,
    left_clouds_only: bool = False,
) -> Image.Image:
    if left_clouds_only:
        band = reference.crop((0, 0, 760, limit)).resize((SIZE[0], limit), Image.Resampling.LANCZOS)
    else:
        band = reference.crop((0, 0, SIZE[0], limit))
    overlay = image.copy()
    overlay.paste(band, (0, 0))

    mask = Image.new("L", SIZE, 0)
    pixels = mask.load()
    for y in range(limit):
        fade = 1.0 if y < limit * 0.65 else max(0.0, (limit - y) / (limit * 0.35))
        value = int(opacity * fade)
        for x in range(SIZE[0]):
            pixels[x, y] = value
    if preserve is not None:
        cx, cy, radius = preserve
        cutout = Image.new("L", SIZE, 255)
        draw = ImageDraw.Draw(cutout)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=0)
        cutout = cutout.filter(ImageFilter.GaussianBlur(70))
        mask = ImageChops.multiply(mask, cutout)
    return Image.composite(overlay, image, mask)


def indoor_storm(source: Image.Image, reference: Image.Image, label: str, typhoon: bool) -> Image.Image:
    outside = source.crop((0, 0, 1536, 1600))
    outside = ImageOps.fit(outside, SIZE, Image.Resampling.LANCZOS)
    outside = color_grade(outside, (62, 78, 86), 112 if typhoon else 94, contrast=0.92, saturation=0.65)
    storm_sky = reference.crop((0, 0, 1536, 980)).resize((1536, 1200), Image.Resampling.LANCZOS)
    storm_layer = outside.copy()
    storm_layer.paste(storm_sky, (0, 0))
    storm_mask = Image.new("L", outside.size, 0)
    storm_draw = ImageDraw.Draw(storm_mask)
    storm_draw.rectangle((0, 0, 1536, 700), fill=255)
    for y in range(700, 1200):
        value = int(255 * (1200 - y) / 500)
        storm_draw.line((0, y, 1536, y), fill=value)
    outside = Image.composite(storm_layer, outside, storm_mask)
    outside = add_rain(outside, label + "-rain", 980 if typhoon else 760, 32 if typhoon else 12, 205, 120)

    scene = Image.new("RGB", SIZE, (76, 58, 48))
    scene.paste(outside, (0, 0))
    glass = Image.new("RGBA", SIZE, (175, 195, 200, 22))
    scene = Image.alpha_composite(scene.convert("RGBA"), glass)

    rng = rng_for(label + "-drops")
    drops = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    dd = ImageDraw.Draw(drops)
    for _ in range(240):
        x = rng.randint(30, 1470)
        y = rng.randint(90, 2200)
        radius = rng.randint(2, 8)
        dd.ellipse((x - radius, y - radius * 2, x + radius, y + radius * 2), outline=(225, 238, 239, rng.randint(80, 170)), width=1)
    for _ in range(34):
        x = rng.randint(40, 1460)
        y = rng.randint(170, 1700)
        dd.line((x, y, x + (18 if typhoon else 5), y + rng.randint(90, 230)), fill=(220, 233, 235, 115), width=rng.randint(2, 5))
    scene = Image.alpha_composite(scene, drops.filter(ImageFilter.GaussianBlur(0.5)))

    interior_mask = Image.new("L", SIZE, 0)
    interior_draw = ImageDraw.Draw(interior_mask)
    interior_draw.rectangle((0, 2380, 1536, 2752), fill=255)
    interior_draw.rectangle((0, 0, 46, 2752), fill=255)
    interior_draw.rectangle((1470, 0, 1536, 2752), fill=255)
    interior_draw.ellipse((900, 1950, 1630, 2920), fill=255)
    interior_draw.ellipse((-180, 2280, 480, 2900), fill=255)
    interior_mask = interior_mask.filter(ImageFilter.GaussianBlur(24))
    scene = Image.composite(reference.convert("RGBA"), scene, interior_mask)

    return scene.convert("RGB")


def partly_cloudy(source: Image.Image, period: str, reference: Image.Image) -> Image.Image:
    celestial = {
        "morning": (1080, 300, 210),
        "afternoon": (1080, 260, 210),
        "sunset": (760, 640, 230),
        "night": (1050, 420, 220),
        "midnight": (1050, 360, 220),
        "sunrise": (760, 650, 230),
    }[period]
    opacity = 170 if period in ("night", "midnight") else 150
    return blend_reference_sky(source, reference, opacity, 1040, celestial, left_clouds_only=True)


def all_day(source: Image.Image, weather: str, reference: Image.Image) -> Image.Image:
    if weather == "cloudy":
        image = color_grade(source, (178, 190, 185), 35, saturation=0.88)
        return blend_reference_sky(image, reference, 210, 1120)
    if weather == "overcast":
        image = color_grade(source, (127, 139, 140), 85, contrast=0.88, saturation=0.68)
        return blend_reference_sky(image, reference, 238, 1180)
    if weather == "light_rain":
        image = color_grade(source, (132, 151, 150), 75, contrast=0.9, saturation=0.7)
        image = blend_reference_sky(image, reference, 230, 1180)
        image = add_fog(image, weather + "-mist", 80)
        return add_rain(image, weather, 260, 8, 115, 430)
    if weather in ("heavy_rain", "typhoon"):
        return indoor_storm(source, reference, weather, weather == "typhoon")
    if weather == "fog":
        image = color_grade(source, (191, 202, 198), 60, contrast=0.72, saturation=0.58)
        return add_fog(image, weather, 205)
    if weather == "haze":
        image = color_grade(source, (207, 175, 126), 84, contrast=0.72, saturation=0.66)
        return add_fog(image, weather, 90)
    if weather == "strong_wind":
        image = color_grade(source, (166, 179, 173), 50, contrast=1.02, saturation=0.76)
        image = blend_reference_sky(image, reference, 215, 1160)
        return add_wind(image, weather)
    if weather == "thunder_shower":
        image = color_grade(source, (55, 70, 84), 116, contrast=1.08, saturation=0.62)
        image = blend_reference_sky(image, reference, 245, 1180)
        image = add_rain(image, weather, 470, 16, 170, 420)
        return add_lightning(image, weather, 1)
    if weather == "thunderstorm":
        image = color_grade(source, (32, 43, 60), 145, contrast=1.14, saturation=0.54)
        image = blend_reference_sky(image, reference, 250, 1240)
        image = add_rain(image, weather, 850, 22, 220, 300)
        return add_lightning(image, weather, 3)
    if weather == "heatwave":
        image = color_grade(source, (242, 173, 70), 78, contrast=1.08, saturation=1.05)
        image = heat_shimmer(image)
        glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for radius, alpha in ((300, 24), (220, 34), (145, 52)):
            gd.ellipse((1080 - radius, 420 - radius, 1080 + radius, 420 + radius), fill=(255, 220, 112, alpha))
        return Image.alpha_composite(image.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(55))).convert("RGB")
    if weather == "cold_wave":
        image = color_grade(source, (116, 153, 178), 105, contrast=0.96, saturation=0.52)
        image = add_fog(image, weather + "-breath", 75)
        return frost_edges(image, weather)
    raise ValueError(weather)


def save_atomic(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name("." + destination.name + ".pending")
    if temporary.exists():
        temporary.unlink()
    validate(image).save(temporary, "PNG", optimize=True)
    with Image.open(temporary) as check:
        check.load()
        if check.format != "PNG" or check.size != SIZE:
            raise ValueError(f"Invalid output {destination.name}: {check.format} {check.size}")
    for attempt in range(5):
        try:
            temporary.replace(destination)
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.2 * (attempt + 1))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    for period in PERIODS:
        source_path = args.source_root / f"none_Miaoli_person_{period}_sunny.png"
        with Image.open(source_path) as source_image:
            source = validate(source_image.copy())
        reference_path = args.source_root / f"none_HsinchuCounty_person_{period}_partly_cloudy.png"
        with Image.open(reference_path) as reference_image:
            reference = validate(reference_image.copy())
        save_atomic(partly_cloudy(source, period, reference), args.output_dir / f"none_Miaoli_person_{period}_partly_cloudy.png")

    with Image.open(args.source_root / "master" / "none_Miaoli_person_master.png") as master_image:
        master = validate(master_image.copy())
    for weather in WEATHERS:
        reference_path = args.source_root / f"none_HsinchuCounty_person_all_day_{weather}.png"
        with Image.open(reference_path) as reference_image:
            reference = validate(reference_image.copy())
        save_atomic(all_day(master, weather, reference), args.output_dir / f"none_Miaoli_person_all_day_{weather}.png")


if __name__ == "__main__":
    main()
