from __future__ import annotations

import argparse
import os
from pathlib import Path

from PIL import Image


ALLOWED_WEATHERS = {
    "heavy_rain",
    "typhoon",
    "fog",
    "haze",
    "strong_wind",
    "thunder_shower",
    "thunderstorm",
    "heatwave",
    "cold_wave",
}
EXPECTED_SIZE = (1536, 2752)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("staging_dir", type=Path)
    parser.add_argument("weather", choices=sorted(ALLOWED_WEATHERS))
    args = parser.parse_args()

    if not args.source.is_file():
        raise FileNotFoundError(args.source)

    with Image.open(args.source) as image:
        if image.format != "JPEG" or image.size != EXPECTED_SIZE:
            raise ValueError(
                f"Expected native JPEG {EXPECTED_SIZE}, got {image.format} {image.size}"
            )
        converted = image.convert("RGB")

    args.staging_dir.mkdir(parents=True, exist_ok=True)
    destination = (
        args.staging_dir / f"none_Taichung_person_all_day_{args.weather}.png"
    )
    temporary = destination.with_suffix(".png.tmp")
    converted.save(temporary, "PNG", optimize=True)

    with Image.open(temporary) as staged:
        staged.load()
        if staged.format != "PNG" or staged.size != EXPECTED_SIZE:
            raise ValueError(
                f"Staged validation failed: {staged.format} {staged.size}"
            )

    os.replace(temporary, destination)
    print(destination)


if __name__ == "__main__":
    main()
