from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image


FESTIVALS = (
    "new_year", "valentines_day", "national_day", "halloween", "constitution_day"
)
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
REGULAR_WEATHERS = ("sunny", "partly_cloudy")
ORDINARY_ALL_DAY_WEATHERS = ("cloudy", "overcast", "light_rain")
EXPECTED_SIZE = (1536, 2752)
MIN_GPT_SIZE = (900, 1600)


def full_screen_gpt_size(size: tuple[int, int]) -> bool:
    width, height = size
    return (width >= MIN_GPT_SIZE[0] and height >= MIN_GPT_SIZE[1]
            and abs(width / height - EXPECTED_SIZE[0] / EXPECTED_SIZE[1]) <= 0.01)


def load_eligibility() -> dict:
    path = Path(__file__).with_name("festival_weather_eligibility.json")
    return json.loads(path.read_text(encoding="utf-8"))


def all_day_weathers(city: str, festival: str, matrix: dict | None = None) -> tuple[str, ...]:
    matrix = matrix if matrix is not None else load_eligibility()
    city_policy = matrix.get("cities", {}).get(city)
    if not isinstance(city_policy, dict):
        raise ValueError(f"City eligibility is not verified: {city}")
    policy = city_policy.get("festivals", {}).get(festival)
    if not isinstance(policy, dict):
        raise ValueError(f"Festival eligibility is not verified: {city}/{festival}")

    allowed = set(matrix["policy"]["adverse_requires_historical_evidence"])
    adverse = policy.get("eligible_adverse")
    excluded = policy.get("excluded_adverse")
    if not isinstance(adverse, list) or not isinstance(excluded, list):
        raise ValueError(f"Adverse whitelist is incomplete: {city}/{festival}")
    if len(adverse) != len(set(adverse)) or len(excluded) != len(set(excluded)):
        raise ValueError(f"Duplicate adverse weather: {city}/{festival}")
    if set(adverse) & set(excluded) or set(adverse) | set(excluded) != allowed:
        raise ValueError(f"Adverse whitelist is incomplete: {city}/{festival}")

    evidence = policy.get("evidence", {})
    if not isinstance(evidence, dict) or set(evidence) - set(adverse):
        raise ValueError(f"Unapproved adverse evidence: {city}/{festival}")
    for weather in adverse:
        records = evidence.get(weather)
        if not isinstance(records, list) or not records:
            raise ValueError(f"Adverse weather lacks historical evidence: {city}/{festival}/{weather}")
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"Invalid historical evidence: {city}/{festival}/{weather}")
            try:
                record_date = date.fromisoformat(record["date"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Evidence lacks valid date: {city}/{festival}/{weather}") from exc
            if record_date.strftime("%m-%d") != policy.get("month_day"):
                raise ValueError(f"Evidence date does not match festival: {city}/{festival}/{weather}")
            parsed = urlparse(record.get("source_url", ""))
            if parsed.scheme != "https" or parsed.hostname not in {
                "codis.cwa.gov.tw", "rdc28.cwa.gov.tw"
            }:
                raise ValueError(f"Evidence lacks official CWA source: {city}/{festival}/{weather}")
            station = all(record.get(key) for key in ("station_id", "station_name", "measurement"))
            if not station and not record.get("official_event"):
                raise ValueError(f"Evidence lacks measurement or event: {city}/{festival}/{weather}")
        if weather == "typhoon":
            if not any(record.get("official_event") for record in records) or not any(
                record.get("station_id") and record.get("measurement") for record in records
            ):
                raise ValueError(f"Typhoon lacks event or local observation: {city}/{festival}")
    return ORDINARY_ALL_DAY_WEATHERS + tuple(adverse)


def valid_png(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG":
                return False
            if image.size == EXPECTED_SIZE:
                return True
            if not full_screen_gpt_size(image.size):
                return False
            size = image.size
        record = json.loads((path.parent / "qa" / f"{path.stem}.json").read_text(encoding="utf-8"))
        return (record.get("filename") == path.name
                and record.get("source_method") == "OpenAI built-in image generation"
                and record.get("native_source_size") == list(size)
                and record.get("no_resize") is True
                and record.get("status") in {
                    "staged_individual_qa_passed_not_batch_qualified", "published_qualified"
                }
                and record.get("png_sha256") == hashlib.sha256(path.read_bytes()).hexdigest()
                and bool(record.get("qa")))
    except (OSError, ValueError, KeyError):
        return False


def audit_festival(root: Path, city: str, festival: str) -> dict:
    all_day = all_day_weathers(city, festival)
    missing_regular = {
        weather: [
            period for period in PERIODS
            if not valid_png(root / f"{festival}_{city}_person_{period}_{weather}.png")
        ]
        for weather in REGULAR_WEATHERS
    }
    missing_regular = {weather: periods for weather, periods in missing_regular.items() if periods}
    missing_all_day = [
        weather for weather in all_day
        if not valid_png(root / f"{festival}_{city}_person_all_day_{weather}.png")
    ]
    qa_dir = root / "qa"
    missing_qa = [
        f"{weather}_6grid" for weather in REGULAR_WEATHERS
        if not (qa_dir / f"{festival}_{city}_{weather}_6grid.png").is_file()
    ]
    if not (qa_dir / f"{festival}_{city}_all_day_{len(all_day)}grid.png").is_file():
        missing_qa.append(f"all_day_{len(all_day)}grid")
    expected = len(REGULAR_WEATHERS) * len(PERIODS) + len(all_day)
    valid = expected - sum(map(len, missing_regular.values())) - len(missing_all_day)
    return {
        "city": city,
        "festival": festival,
        "expected_png_count": expected,
        "valid_png_count": valid,
        "missing_regular": missing_regular,
        "missing_all_day": missing_all_day,
        "missing_qa": missing_qa,
        "complete": valid == expected and not missing_qa,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("city")
    parser.add_argument("--festival", choices=FESTIVALS)
    args = parser.parse_args()
    festivals = (args.festival,) if args.festival else FESTIVALS
    print(json.dumps(
        {festival: audit_festival(args.root, args.city, festival) for festival in festivals},
        indent=2,
    ))


if __name__ == "__main__":
    main()
