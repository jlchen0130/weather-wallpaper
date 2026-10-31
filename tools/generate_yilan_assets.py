from __future__ import annotations

import argparse
import json
import math
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageStat

import generate_pingtung_assets as render


FORMAL = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
STAGE = Path(__file__).resolve().parents[1] / "generated" / "Yilan"
DAY_SOURCE = Path(r"C:\Users\JL\Downloads\Gemini_Generated_Image_sd55mcsd55mcsd55 (1).jfif")
STORM_SOURCE = Path(r"C:\Users\JL\Downloads\Gemini_Generated_Image_dxagcgdxagcgdxag.jfif")
SIZE = (1536, 2752)
DATE = "2026-10-10"


def source(path):
    with Image.open(path) as image:
        if image.size != SIZE:
            raise ValueError(f"Source is not original size: {path}: {image.size}")
        image.load()
        return image.convert("RGB")


def rain(image, intensity=120, slant=-42, width=2):
    rng = random.Random(417 + intensity)
    layer = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(layer)
    for _ in range(intensity * 6):
        x, y = rng.randrange(-100, 1636), rng.randrange(-80, 2752)
        length = rng.randrange(30, 105)
        draw.line((x, y, x + slant * length / 85, y + length),
                  fill=(214, 230, 239, rng.randrange(24, 84)), width=width)
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(0.65))).convert("RGB")


def clouds(image, density=6, alpha=115, gray=False):
    # Reuse the photographed felt cloud structure instead of drawing new blobs.
    luminance = ImageOps.grayscale(image)
    night = ImageStat.Stat(luminance.crop((0,0,1536,800))).mean[0] < 90
    if night:
        sky = ImageEnhance.Contrast(image).enhance(1.35)
    elif gray:
        sky = ImageOps.colorize(ImageEnhance.Contrast(luminance).enhance(1.45),
                               (55,65,78),(220,225,226))
    else:
        sky = ImageEnhance.Contrast(image).enhance(1.24)
        sky = ImageEnhance.Color(sky).enhance(.78)
    mask = Image.new("L",(1,2752))
    for y in range(2752):
        mask.putpixel((0,y),round(alpha*max(0,min(1,(1120-y)/240))))
    return Image.composite(sky,image,mask.resize(SIZE))


def wind(image, strong=True):
    layer = Image.new("RGBA", SIZE)
    draw = ImageDraw.Draw(layer)
    rng = random.Random(388)
    for _ in range(32 if strong else 16):
        x, y = rng.randrange(-150, 1450), rng.randrange(1020, 1990)
        points = [(x + j*22, y - j*4 + math.sin(j*.3)*8) for j in range(12)]
        draw.line(points, fill=(222, 232, 224, 82), width=3)
    foliage = source(DAY_SOURCE).crop((1270,1340,1310,1360))
    for _ in range(22):
        leaf = foliage.resize((rng.randrange(15,27),rng.randrange(7,13))).convert("RGBA")
        mask = Image.new("L",leaf.size)
        ImageDraw.Draw(mask).ellipse((0,0,leaf.width-1,leaf.height-1),fill=180)
        leaf.putalpha(mask.filter(ImageFilter.GaussianBlur(.6)))
        leaf = leaf.rotate(rng.randrange(-35,25),expand=True)
        layer.alpha_composite(leaf,(rng.randrange(70,1460),rng.randrange(970,1840)))
    return Image.alpha_composite(image.convert("RGBA"), layer.filter(ImageFilter.GaussianBlur(1.2))).convert("RGB")


def sun(image, center, radius, color):
    x, y = (680, 830) if center[1] > 900 else center
    radius = round(radius * .65)
    mask = Image.new("L", SIZE)
    ImageDraw.Draw(mask).ellipse((x-radius,y-radius,x+radius,y+radius), fill=190)
    mask = mask.filter(ImageFilter.GaussianBlur(9))
    texture = source(DAY_SOURCE).crop((100,100,400,400)).resize(SIZE)
    texture = ImageEnhance.Color(texture).enhance(0)
    texture = Image.blend(texture, Image.new("RGB",SIZE,color), .78)
    return Image.composite(texture, image, mask)


def moon(image, center, radius):
    x, y = center
    radius = round(radius*.7)
    mask = Image.new("L", SIZE)
    ImageDraw.Draw(mask).ellipse((x-radius,y-radius,x+radius,y+radius), fill=220)
    texture = source(DAY_SOURCE).crop((100,100,400,400)).resize(SIZE)
    texture = ImageEnhance.Color(texture).enhance(0)
    texture = Image.blend(texture, Image.new("RGB",SIZE,(220,222,210)), .68)
    return Image.composite(texture,image,mask.filter(ImageFilter.GaussianBlur(1.8)))


def bind(root):
    render.ROOT = root
    render.QA_DIR = root / "qa"
    render.MASTER_DIR = root / "master"
    render.CITY = "Yilan"
    render.add_felt_texture = lambda image, opacity=14: image
    render.add_rain = rain
    render.add_clouds = clouds
    render.add_wind = wind
    render.add_sun = sun
    render.add_moon = moon


def sheet(weather=None):
    values = render.PERIODS if weather else render.ALL_DAY_WEATHERS
    cols = 3 if weather else 4
    thumb = (480, 860) if weather else (360, 645)
    label, gap = 44, 16
    rows = len(values)//cols
    size = (cols*(thumb[0]+gap)+gap, rows*(thumb[1]+label+gap)+gap)
    image = Image.new("RGB",size,"#171717")
    draw = ImageDraw.Draw(image)
    for index,value in enumerate(values):
        name = f"none_Yilan_person_{value}_{weather}.png" if weather else f"none_Yilan_person_all_day_{value}.png"
        with Image.open(STAGE/name) as tile:
            x,y = gap+(index%cols)*(thumb[0]+gap), gap+(index//cols)*(thumb[1]+label+gap)
            image.paste(tile.resize(thumb,Image.Resampling.LANCZOS),(x,y))
        draw.text((x+8,y+thumb[1]+8),value,fill="white",font=ImageFont.load_default(size=24))
    name = f"Yilan_{weather}_6grid.png" if weather else "Yilan_all_day_12grid.png"
    image.save(STAGE/"qa"/name,"PNG")


def regular(base, period, weather):
    image = render.period_variant(base, period, "sunny")
    if weather == "partly_cloudy":
        image = clouds(image, 5, 60 if period in {"night", "midnight"} else 116,
                       period in {"night", "midnight"})
    return image


def storm(indoor, weather):
    if weather == "heavy_rain":
        return indoor.copy()
    # Window aperture excludes the dry sill, frame, person and room.
    mask = Image.new("L", SIZE)
    ImageDraw.Draw(mask).polygon([(238,0),(1536,0),(1536,2184),(238,2098)], fill=255)
    exterior = render.adjust(indoor, .78, 1.08, .84)
    exterior = rain(exterior, 160, -70, 3)
    return Image.composite(exterior, indoor, mask.filter(ImageFilter.GaussianBlur(2)))


def build(refresh=False):
    bind(STAGE)
    if refresh:
        def save_stage(image, path, expected_size=SIZE):
            if not path.is_relative_to(STAGE):
                raise ValueError(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path,"PNG")
            if not render.valid_png(path,expected_size):
                raise ValueError(path)
        render.save_or_verify = save_stage
    master, indoor = source(DAY_SOURCE), source(STORM_SOURCE)
    render.save_or_verify(master, STAGE / "master/none_Yilan_person_master.png")
    render.save_or_verify(indoor, STAGE / "qa/Yilan_indoor_source.png")
    for weather in render.REGULAR_WEATHERS:
        for period in render.PERIODS:
            relative = Path(f"none_Yilan_person_{period}_{weather}.png")
            if render.valid_png(FORMAL / relative):
                shutil.copy2(FORMAL / relative, STAGE / relative)
            else:
                render.save_or_verify(regular(master, period, weather), STAGE / relative)
        sheet(weather)
    for weather in render.ALL_DAY_WEATHERS:
        relative = Path(f"none_Yilan_person_all_day_{weather}.png")
        if render.valid_png(FORMAL / relative):
            shutil.copy2(FORMAL / relative, STAGE / relative)
        else:
            image = storm(indoor, weather) if weather in {"heavy_rain", "typhoon"} else render.all_day_variant(master, indoor, weather)
            render.save_or_verify(image, STAGE / relative)
    sheet()
    print(json.dumps({"stage":str(STAGE), "wallpapers":25,"qa_sheets":3}))


def qualify():
    from audit_weather_assets import audit_city
    if not audit_city(STAGE, "Yilan")["complete"]:
        raise ValueError("Staged audit is incomplete")
    paths = [Path("master/none_Yilan_person_master.png")]
    paths += [Path(f"none_Yilan_person_{p}_{w}.png") for w in render.REGULAR_WEATHERS for p in render.PERIODS]
    paths += [Path(f"none_Yilan_person_all_day_{w}.png") for w in render.ALL_DAY_WEATHERS]
    paths += [Path("qa") / name for name in ("Yilan_sunny_6grid.png", "Yilan_partly_cloudy_6grid.png", "Yilan_all_day_12grid.png", "Yilan_indoor_source.png")]
    for relative in paths:
        target = FORMAL / relative
        if target.exists():
            if relative.parts[0] != "qa" and not render.valid_png(target):
                raise ValueError(f"Existing invalid file: {target}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STAGE / relative, target)
    manifest = FORMAL / "qa/qualified_assets.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    common = dict(city="Yilan", style="knitted", character="person", qualified_at=DATE,
                  master_file="master/none_Yilan_person_master.png")
    for weather in render.REGULAR_WEATHERS:
        entries = data.setdefault("qualified_groups", [])
        if any(e.get("city")=="Yilan" and e.get("weather")==weather for e in entries):
            continue
        entries.append(dict(common, weather=weather, periods=list(render.PERIODS),
            qa_file=f"Yilan_{weather}_6grid.png",
            source_method="Verified 1536x2752 Gemini Yilan original download plus local Pillow time/weather derivation",
            criteria="Six-period visual QA passed; exact PNG 1536x2752; Yilan rice paddies, mountains and Turtle Island retained; fine original wool-felt fibers; people on safe land paths; water clear; no text, logos, UI or watermark."))
    for weather in render.ALL_DAY_WEATHERS:
        entries = data.setdefault("qualified_all_day", [])
        if any(e.get("city")=="Yilan" and e.get("weather")==weather for e in entries):
            continue
        indoor = weather in {"heavy_rain", "typhoon"}
        method = "Verified 1536x2752 Gemini Yilan closed-glass indoor original download" if indoor else "Verified 1536x2752 Gemini Yilan original download plus local Pillow weather derivation"
        if weather == "typhoon":
            method += " plus local Pillow window-masked weather derivation"
        entries.append(dict(common, weather=weather, asset_file=f"none_Yilan_person_all_day_{weather}.png",
            qa_file="Yilan_all_day_12grid.png", source_method=method,
            criteria="Visual QA passed; exact PNG 1536x2752; Yilan landscape retained; original fine matte wool-felt texture; no text, logos, watermark or UI." +
            (" Closed glass window; person indoors only; dry interior; exterior clear of people, animals, bikes, cars, vendors, boats and silhouettes." if indoor else " People on safe land paths; water surfaces clear.")))
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    result = audit_city(FORMAL,"Yilan")
    if not result["complete"]:
        raise ValueError(result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualify", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    qualify() if args.qualify else build(args.refresh)
