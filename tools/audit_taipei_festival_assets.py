from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


CITY = "Taipei"
FESTIVALS = (
    "new_year",
    "valentines_day",
    "national_day",
    "halloween",
    "constitution_day",
)
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
REGULAR_WEATHERS = ("sunny", "partly_cloudy")
ORDINARY_ALL_DAY_WEATHERS = ("cloudy", "overcast", "light_rain")
EXPECTED_SIZE = (1536, 2752)


def load_eligibility() -> dict[str, object]:
    path = Path(__file__).with_name("festival_weather_eligibility.json")
    return json.loads(path.read_text(encoding="utf-8"))


def all_day_weathers(festival: str) -> tuple[str, ...]:
    matrix = load_eligibility()
    city = matrix["cities"].get(CITY)
    if city is None or festival not in city["festivals"]:
        raise ValueError(f"Historical weather eligibility is not verified: {CITY}/{festival}")
    festival_policy = city["festivals"][festival]
    adverse = tuple(festival_policy["eligible_adverse"])
    allowed = set(matrix["policy"]["adverse_requires_historical_evidence"])
    unsupported = set(adverse) - allowed
    if unsupported:
        raise ValueError(
            f"Unknown adverse weather in eligibility matrix: {CITY}/{festival}: "
            f"{sorted(unsupported)}"
        )
    evidence = festival_policy.get("evidence", {})
    missing_evidence = [weather for weather in adverse if not evidence.get(weather)]
    if missing_evidence:
        raise ValueError(
            f"Adverse weather lacks historical evidence: {CITY}/{festival}: "
            f"{missing_evidence}"
        )
    if adverse and not festival_policy.get("references"):
        raise ValueError(
            f"Adverse weather lacks authoritative references: {CITY}/{festival}"
        )
    return ORDINARY_ALL_DAY_WEATHERS + adverse


def valid_png(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.load()
            return image.format == "PNG" and image.size == EXPECTED_SIZE
    except (OSError, ValueError):
        return False


def audit_festival(root: Path, festival: str) -> dict[str, object]:
    expected_all_day = all_day_weathers(festival)
    missing_regular: dict[str, list[str]] = {}
    for weather in REGULAR_WEATHERS:
        missing = [
            period
            for period in PERIODS
            if not valid_png(root / f"{festival}_{CITY}_person_{period}_{weather}.png")
        ]
        if missing:
            missing_regular[weather] = missing

    missing_all_day = [
        weather
        for weather in expected_all_day
        if not valid_png(root / f"{festival}_{CITY}_person_all_day_{weather}.png")
    ]

    qa_dir = root / "qa"
    missing_qa = [
        f"{weather}_6grid"
        for weather in REGULAR_WEATHERS
        if not (qa_dir / f"{festival}_{CITY}_{weather}_6grid.png").is_file()
    ]
    all_day_qa = f"{festival}_{CITY}_all_day_{len(expected_all_day)}grid.png"
    if not (qa_dir / all_day_qa).is_file():
        missing_qa.append(f"all_day_{len(expected_all_day)}grid")

    expected_count = len(REGULAR_WEATHERS) * len(PERIODS) + len(expected_all_day)
    present_valid = 0
    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            if valid_png(root / f"{festival}_{CITY}_person_{period}_{weather}.png"):
                present_valid += 1
    for weather in expected_all_day:
        if valid_png(root / f"{festival}_{CITY}_person_all_day_{weather}.png"):
            present_valid += 1

    return {
        "missing_regular": missing_regular,
        "missing_all_day": missing_all_day,
        "missing_qa": missing_qa,
        "valid_png_count": present_valid,
        "expected_png_count": expected_count,
        "expected_all_day_weathers": list(expected_all_day),
        "historical_evidence_policy": "adverse weather requires city/festival evidence",
        "complete": present_valid == expected_count and not missing_qa,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--festival", choices=FESTIVALS)
    args = parser.parse_args()

    festivals = (args.festival,) if args.festival else FESTIVALS
    print(
        json.dumps(
            {festival: audit_festival(args.root, festival) for festival in festivals},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
