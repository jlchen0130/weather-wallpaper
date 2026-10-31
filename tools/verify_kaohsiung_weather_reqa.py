"""Independent fail-closed verifier for finalized Kaohsiung base-weather re-QA."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

from reqa_kaohsiung_weather import (
    ALL_DAY, CITY, MASTER, PERIODS, REGULAR, TARGETS, formal_path,
    manifest_scope, paths, stage_path,
)


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
    p = paths(root)
    checkpoint = json.loads(p["checkpoint"].read_text(encoding="utf-8"))
    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))

    invalid = [name for name in TARGETS if not valid_png(formal_path(root, name), (1536, 2752))]
    stage_formal_mismatches = []
    source_pixel_mismatches = []
    for filename, record in checkpoint.get("accepted_replacements", {}).items():
        staged = stage_path(p["stage"], filename)
        formal = formal_path(root, filename)
        source = root / record["source_file"]
        if sha256(staged) != sha256(formal):
            stage_formal_mismatches.append(filename)
        with Image.open(source) as original, Image.open(formal) as output:
            original.load(); output.load()
            if original.size != (1536, 2752) or original.convert("RGB").tobytes() != output.tobytes():
                source_pixel_mismatches.append(filename)

    expected_sheets = {
        f"{CITY}_sunny_6grid.png": (1620, 2074),
        f"{CITY}_partly_cloudy_6grid.png": (1620, 2074),
        f"{CITY}_all_day_12grid.png": (1632, 2390),
    }
    invalid_sheets = [
        name for name, size in expected_sheets.items()
        if not valid_png(p["qa"] / name, size)
    ]
    sheet_mismatches = [
        name for name in expected_sheets
        if sha256(p["qa"] / name) != sha256(p["stage"] / name)
    ]
    city_groups = [row for row in manifest.get("qualified_groups", []) if row.get("city") == CITY]
    city_all_day = [row for row in manifest.get("qualified_all_day", []) if row.get("city") == CITY]
    rejected = p["rejected"]
    report = {
        "checkpoint_status": checkpoint.get("status"),
        "finalized": checkpoint.get("finalized"),
        "accepted_replacements": len(checkpoint.get("accepted_replacements", {})),
        "invalid_pngs": invalid,
        "stage_formal_mismatches": stage_formal_mismatches,
        "source_pixel_mismatches": source_pixel_mismatches,
        "invalid_sheets": invalid_sheets,
        "sheet_stage_formal_mismatches": sheet_mismatches,
        "qualified_groups": len(city_groups),
        "qualified_group_weathers": sorted(row.get("weather") for row in city_groups),
        "qualified_all_day": len(city_all_day),
        "qualified_all_day_weathers": sorted(row.get("weather") for row in city_all_day),
        "preserved_rejected_formal_assets": len([
            name for name in TARGETS if (rejected / (f"master/{name}" if name == MASTER else name)).is_file()
        ]),
        "preserved_rejected_sheets": len(list((rejected / "qa").glob(f"{CITY}_*.png"))),
        "non_kaohsiung_manifest_unchanged": canonical_hash(
            manifest_scope(manifest, include_city=False)
        ) == checkpoint.get("baseline_non_kaohsiung_manifest_sha256"),
        "torrential_rain_forbidden": not (root / f"none_{CITY}_person_all_day_torrential_rain.png").exists(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    expected = {
        "checkpoint_status": "complete", "finalized": True,
        "accepted_replacements": 25, "invalid_pngs": [],
        "stage_formal_mismatches": [], "source_pixel_mismatches": [],
        "invalid_sheets": [], "sheet_stage_formal_mismatches": [],
        "qualified_groups": 2, "qualified_group_weathers": sorted(REGULAR),
        "qualified_all_day": 12, "qualified_all_day_weathers": sorted(ALL_DAY),
        "preserved_rejected_formal_assets": 25,
        "preserved_rejected_sheets": 3,
        "non_kaohsiung_manifest_unchanged": True,
        "torrential_rain_forbidden": True,
    }
    if report != expected:
        raise SystemExit("Kaohsiung final verification failed")


if __name__ == "__main__":
    main()
