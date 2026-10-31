from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


CITIES = (
    # Northern Taiwan
    "Taipei",
    "NewTaipei",
    "Keelung",
    "Taoyuan",
    "HsinchuCity",
    "HsinchuCounty",
    # Central Taiwan
    "Miaoli",
    "Taichung",
    "Changhua",
    "Nantou",
    "Yunlin",
    # Southern Taiwan
    "ChiayiCity",
    "ChiayiCounty",
    "Tainan",
    "Kaohsiung",
    "Pingtung",
    # Eastern Taiwan
    "Yilan",
    "Hualien",
    "Taitung",
    # Outlying islands
    "Penghu",
    "Kinmen",
    "Lienchiang",
)
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
MASTER_DIR = "master"
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


def valid_png(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            return image.format == "PNG" and image.size == (1536, 2752)
    except (OSError, ValueError):
        return False


def audit_city(root: Path, city: str) -> dict[str, object]:
    master_path = root / MASTER_DIR / f"none_{city}_person_master.png"
    missing_master = not valid_png(master_path)

    missing_regular: dict[str, list[str]] = {}
    for weather in REGULAR_WEATHERS:
        missing = [
            period
            for period in PERIODS
            if not valid_png(root / f"none_{city}_person_{period}_{weather}.png")
        ]
        if missing:
            missing_regular[weather] = missing

    missing_all_day = []
    for weather in ALL_DAY_WEATHERS:
        path = root / f"none_{city}_person_all_day_{weather}.png"
        if not valid_png(path):
            missing_all_day.append(weather)

    qa_dir = root / "qa"
    missing_qa = [
        weather
        for weather in REGULAR_WEATHERS
        if not (qa_dir / f"{city}_{weather}_6grid.png").is_file()
    ]
    return {
        "missing_master": missing_master,
        "missing_regular": missing_regular,
        "missing_all_day": missing_all_day,
        "missing_qa": missing_qa,
        "complete": not missing_master and not missing_regular and not missing_all_day and not missing_qa,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(json.dumps({city: audit_city(args.root, city) for city in CITIES}, indent=2))


if __name__ == "__main__":
    main()
