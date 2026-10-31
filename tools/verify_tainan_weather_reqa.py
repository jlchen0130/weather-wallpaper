"""Independent fail-closed verifier for the finalized Tainan base-weather re-QA."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from reqa_tainan_weather import ALL_DAY, CITY, PERIODS, REGULAR, REPLACEMENTS, manifest_scope


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def valid_png(path: Path, size: tuple[int, int]) -> bool:
    try:
        with Image.open(path) as image:
            image.load()
            return image.format == "PNG" and image.size == size
    except (OSError, ValueError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    qa = root / "qa"
    stage = qa / "staging" / "Tainan_2026-10-19_closed_glass"
    checkpoint = json.loads((qa / "Tainan_weather_reqa_checkpoint.json").read_text(encoding="utf-8"))
    manifest = json.loads((qa / "qualified_assets.json").read_text(encoding="utf-8"))

    invalid: list[str] = []
    for weather in REGULAR:
        for period in PERIODS:
            path = root / f"none_Tainan_person_{period}_{weather}.png"
            if not valid_png(path, (1536, 2752)): invalid.append(path.name)
    for weather in ALL_DAY:
        path = root / f"none_Tainan_person_all_day_{weather}.png"
        if not valid_png(path, (1536, 2752)): invalid.append(path.name)
    source_pixel_mismatches: list[str] = []
    stage_formal_mismatches: list[str] = []
    for weather in REPLACEMENTS:
        record = checkpoint["accepted_replacements"][weather]
        source = root / record["source_file"]
        staged = stage / record["asset_file"]
        formal = root / record["asset_file"]
        if sha256(staged) != sha256(formal): stage_formal_mismatches.append(weather)
        with Image.open(source) as original, Image.open(formal) as output:
            original.load(); output.load()
            if original.size != (1536, 2752) or original.convert("RGB").tobytes() != output.tobytes():
                source_pixel_mismatches.append(weather)
    tainan_all_day = [row for row in manifest.get("qualified_all_day", []) if row.get("city") == CITY]
    tainan_groups = [row for row in manifest.get("qualified_groups", []) if row.get("city") == CITY]
    report = {
        "checkpoint_status": checkpoint.get("status"),
        "finalized": checkpoint.get("finalized"),
        "invalid_pngs": invalid,
        "stage_formal_mismatches": stage_formal_mismatches,
        "source_pixel_mismatches": source_pixel_mismatches,
        "qualified_all_day": len(tainan_all_day),
        "qualified_weathers": sorted(row.get("weather") for row in tainan_all_day),
        "qualified_groups": len(tainan_groups),
        "all_day_sheet_valid": valid_png(qa / "Tainan_all_day_12grid.png", (1632, 2390)),
        "all_day_sheet_matches_stage": sha256(qa / "Tainan_all_day_12grid.png") == sha256(stage / "Tainan_all_day_12grid.png"),
        "rejected_formal_backups": len(list((qa / "rejected" / "Tainan_2026-10-19_closed_glass").glob("none_Tainan_person_all_day_*.png"))),
        "non_tainan_manifest_unchanged": canonical_hash(manifest_scope(manifest, include_tainan=False)) == checkpoint["baseline_non_tainan_manifest_sha256"],
        "torrential_rain_forbidden": not (root / "none_Tainan_person_all_day_torrential_rain.png").exists(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    expected = {
        "checkpoint_status": "complete", "finalized": True, "invalid_pngs": [],
        "stage_formal_mismatches": [], "source_pixel_mismatches": [],
        "qualified_all_day": 12, "qualified_weathers": sorted(ALL_DAY),
        "qualified_groups": 2, "all_day_sheet_valid": True,
        "all_day_sheet_matches_stage": True, "rejected_formal_backups": 9,
        "non_tainan_manifest_unchanged": True, "torrential_rain_forbidden": True,
    }
    if report != expected:
        raise SystemExit("Tainan final verification failed")


if __name__ == "__main__":
    main()
