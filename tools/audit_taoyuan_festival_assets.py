from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


CITY = "Taoyuan"
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
OFFICIAL_SOURCE_PREFIXES = (
    "https://codis.cwa.gov.tw/",
    "https://rdc28.cwa.gov.tw/TDB/",
)


def load_eligibility() -> dict[str, object]:
    path = Path(__file__).with_name("festival_weather_eligibility.json")
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_evidence(weather: str, records: object) -> None:
    if not isinstance(records, list) or not records:
        raise ValueError(f"Adverse weather lacks historical evidence: {CITY}/{weather}")
    for record in records:
        if not isinstance(record, dict) or not record.get("date"):
            raise ValueError(f"Evidence lacks date: {CITY}/{weather}")
        source_url = record.get("source_url", "")
        if not any(source_url.startswith(prefix) for prefix in OFFICIAL_SOURCE_PREFIXES):
            raise ValueError(f"Evidence lacks official CWA source URL: {CITY}/{weather}")
        is_station = all(record.get(key) for key in ("station_id", "station_name", "measurement"))
        is_event = bool(record.get("official_event"))
        if not (is_station or is_event):
            raise ValueError(f"Evidence lacks station measurement or official event: {CITY}/{weather}")
    if weather == "typhoon":
        if not any(record.get("official_event") for record in records):
            raise ValueError(f"Typhoon lacks official event: {CITY}/{weather}")
        if not any(record.get("station_id") and record.get("measurement") for record in records):
            raise ValueError(f"Typhoon lacks local observation: {CITY}/{weather}")


def all_day_weathers(festival: str) -> tuple[str, ...]:
    matrix = load_eligibility()
    city = matrix["cities"].get(CITY)
    if city is None or festival not in city["festivals"]:
        raise ValueError(f"Historical weather eligibility is not verified: {CITY}/{festival}")
    festival_policy = city["festivals"][festival]
    adverse = tuple(festival_policy["eligible_adverse"])
    allowed = set(matrix["policy"]["adverse_requires_historical_evidence"])
    if unsupported := set(adverse) - allowed:
        raise ValueError(f"Unknown adverse weather in eligibility matrix: {CITY}/{festival}: {sorted(unsupported)}")
    evidence = festival_policy.get("evidence", {})
    for weather in adverse:
        _validate_evidence(weather, evidence.get(weather))
    references = festival_policy.get("references", [])
    if adverse and not references:
        raise ValueError(f"Adverse weather lacks authoritative references: {CITY}/{festival}")
    if set(adverse) | set(festival_policy.get("excluded_adverse", [])) != allowed:
        raise ValueError(f"Adverse whitelist is incomplete: {CITY}/{festival}")
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
    missing_regular = {
        weather: [
            period for period in PERIODS
            if not valid_png(root / f"{festival}_{CITY}_person_{period}_{weather}.png")
        ]
        for weather in REGULAR_WEATHERS
    }
    missing_regular = {weather: periods for weather, periods in missing_regular.items() if periods}
    missing_all_day = [
        weather for weather in expected_all_day
        if not valid_png(root / f"{festival}_{CITY}_person_all_day_{weather}.png")
    ]
    qa_dir = root / "qa"
    missing_qa = [
        f"{weather}_6grid" for weather in REGULAR_WEATHERS
        if not (qa_dir / f"{festival}_{CITY}_{weather}_6grid.png").is_file()
    ]
    all_day_qa = f"{festival}_{CITY}_all_day_{len(expected_all_day)}grid.png"
    if not (qa_dir / all_day_qa).is_file():
        missing_qa.append(f"all_day_{len(expected_all_day)}grid")
    expected_count = len(REGULAR_WEATHERS) * len(PERIODS) + len(expected_all_day)
    valid_count = expected_count - sum(map(len, missing_regular.values())) - len(missing_all_day)
    return {
        "missing_regular": missing_regular,
        "missing_all_day": missing_all_day,
        "missing_qa": missing_qa,
        "valid_png_count": valid_count,
        "expected_png_count": expected_count,
        "expected_all_day_weathers": list(expected_all_day),
        "historical_evidence_policy": "adverse weather requires structured CWA evidence and a complete fail-closed whitelist",
        "complete": valid_count == expected_count and not missing_qa,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--festival", choices=FESTIVALS)
    args = parser.parse_args()
    festivals = (args.festival,) if args.festival else FESTIVALS
    print(json.dumps({festival: audit_festival(args.root, festival) for festival in festivals}, indent=2))


if __name__ == "__main__":
    main()
