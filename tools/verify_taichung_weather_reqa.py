from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
WEATHERS = (
    "cloudy", "overcast", "light_rain", "heavy_rain", "typhoon", "fog",
    "haze", "strong_wind", "thunder_shower", "thunderstorm", "heatwave",
    "cold_wave",
)
REPLACEMENTS = WEATHERS[3:]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    qa = ROOT / "qa"
    stage = qa / "staging" / "Taichung_2026-10-18_closed_glass"
    checkpoint = json.loads(
        (qa / "Taichung_weather_reqa_checkpoint.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (qa / "qualified_assets.json").read_text(encoding="utf-8")
    )

    invalid_pngs: list[str] = []
    for weather in WEATHERS:
        path = ROOT / f"none_Taichung_person_all_day_{weather}.png"
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG" or image.size != (1536, 2752):
                invalid_pngs.append(path.name)

    stage_formal_mismatches = [
        weather
        for weather in REPLACEMENTS
        if sha256(stage / f"none_Taichung_person_all_day_{weather}.png")
        != sha256(ROOT / f"none_Taichung_person_all_day_{weather}.png")
    ]
    taichung_all_day = [
        item
        for item in manifest.get("qualified_all_day", [])
        if item.get("city") == "Taichung"
    ]
    taichung_groups = [
        item
        for item in manifest.get("qualified_groups", [])
        if item.get("city") == "Taichung"
    ]
    rejected_files = list(
        (qa / "rejected" / "Taichung_2026-10-18_closed_glass").glob("*")
    )
    sheet = qa / "Taichung_all_day_12grid.png"
    with Image.open(sheet) as image:
        image.load()
        sheet_valid = image.format == "PNG" and image.size == (1632, 2390)
    sheet_matches_stage = sha256(sheet) == sha256(
        stage / "Taichung_all_day_12grid.png"
    )

    report = {
        "checkpoint_status": checkpoint.get("status"),
        "finalized": checkpoint.get("finalized"),
        "formal_pngs": len(WEATHERS),
        "invalid_pngs": invalid_pngs,
        "stage_formal_mismatches": stage_formal_mismatches,
        "formal_sheet_valid": sheet_valid,
        "formal_sheet_matches_stage": sheet_matches_stage,
        "qualified_all_day": len(taichung_all_day),
        "qualified_weathers": sorted(
            item.get("weather") for item in taichung_all_day
        ),
        "qualified_groups": len(taichung_groups),
        "rejected_evidence_files": len(rejected_files),
        "festival_named_files_at_formal_root": len(
            list(ROOT.glob("*Taichung*festival*"))
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report != {
        "checkpoint_status": "complete",
        "finalized": True,
        "formal_pngs": 12,
        "invalid_pngs": [],
        "stage_formal_mismatches": [],
        "formal_sheet_valid": True,
        "formal_sheet_matches_stage": True,
        "qualified_all_day": 12,
        "qualified_weathers": sorted(WEATHERS),
        "qualified_groups": 2,
        "rejected_evidence_files": 10,
        "festival_named_files_at_formal_root": 0,
    }:
        raise SystemExit("Taichung final verification failed")


if __name__ == "__main__":
    main()
