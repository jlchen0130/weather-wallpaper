from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageChops

from audit_festival_assets import (
    EXPECTED_SIZE,
    FESTIVALS,
    PERIODS,
    REGULAR_WEATHERS,
    all_day_weathers,
    audit_festival,
)


CITY = "Taichung"
SOURCE_METHOD = "Gemini web native 1536x2752 JPEG; decoded to PNG without resizing"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def pixel_equal(source: Path, png: Path) -> bool:
    with Image.open(source) as original, Image.open(png) as converted:
        original.load()
        converted.load()
        if original.format != "JPEG" or converted.format != "PNG":
            return False
        if original.size != EXPECTED_SIZE or converted.size != EXPECTED_SIZE:
            return False
        return ImageChops.difference(original.convert("RGB"), converted.convert("RGB")).getbbox() is None


def names(festival: str) -> list[str]:
    regular = [
        f"{festival}_{CITY}_person_{period}_{weather}.png"
        for weather in REGULAR_WEATHERS
        for period in PERIODS
    ]
    return regular + [
        f"{festival}_{CITY}_person_all_day_{weather}.png"
        for weather in all_day_weathers(CITY, festival)
    ]


def sheet_names(festival: str) -> list[str]:
    return [
        f"{festival}_{CITY}_sunny_6grid.png",
        f"{festival}_{CITY}_partly_cloudy_6grid.png",
        f"{festival}_{CITY}_all_day_{len(all_day_weathers(CITY, festival))}grid.png",
    ]


def write_json_atomic(path: Path, payload: object) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def copy_new_or_equal(source: Path, destination: Path) -> None:
    if destination.exists():
        if digest(source) != digest(destination):
            raise ValueError(f"Existing formal file differs; refusing overwrite: {destination}")
        return
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)


def preflight(staging: Path, checkpoint: Path, formal: Path) -> dict:
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    if state.get("city") != CITY or state.get("next_slot") is not None:
        raise ValueError("Taichung checkpoint still has an unfinished slot")

    manifest_path = formal / "qa" / "qualified_assets.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not all(isinstance(manifest.get(key), list) for key in ("qualified_groups", "qualified_all_day")):
        raise ValueError("Qualified manifest has an unexpected schema")

    assets: dict[str, list[dict]] = {}
    for festival in FESTIVALS:
        audit = audit_festival(staging, CITY, festival)
        if not audit["complete"]:
            raise ValueError(f"Incomplete staging matrix: {festival}: {audit}")
        section = state.get(festival)
        if not isinstance(section, dict) or section.get("staged_group_qa_complete") is not True:
            raise ValueError(f"Batch visual QA not recorded: {festival}")
        expected = names(festival)
        accepted = section.get("staged_individual_qa_passed")
        if isinstance(accepted, list) and set(accepted) != set(expected):
            raise ValueError(f"Individual QA list mismatch: {festival}")
        if not isinstance(accepted, list) and section.get("individual_qa_records") != len(expected):
            raise ValueError(f"Individual QA count mismatch: {festival}")
        if section.get("staged_valid_png_count", len(accepted) if isinstance(accepted, list) else None) != len(expected):
            raise ValueError(f"Checkpoint count mismatch: {festival}")

        rows = []
        for filename in expected:
            staged = staging / filename
            qa_path = staging / "qa" / f"{Path(filename).stem}.json"
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
            source = staging / qa["source_file"]
            if qa.get("filename") != filename or qa.get("festival") != festival or qa.get("city") != CITY:
                raise ValueError(f"Individual QA identity mismatch: {filename}")
            if qa.get("status") != "staged_individual_qa_passed_not_batch_qualified":
                raise ValueError(f"Individual QA status mismatch: {filename}")
            if qa.get("source_pixel_equality") is not True or not pixel_equal(source, staged):
                raise ValueError(f"Native JPEG / PNG pixel mismatch: {filename}")
            if digest(source) != qa.get("source_sha256") or digest(staged) != qa.get("png_sha256"):
                raise ValueError(f"Provenance hash mismatch: {filename}")
            destination = formal / filename
            if destination.exists() and digest(destination) != digest(staged):
                raise ValueError(f"Existing formal asset differs: {filename}")
            rows.append(qa)
        for sheet in sheet_names(festival):
            source = staging / "qa" / sheet
            if not source.is_file():
                raise ValueError(f"Missing contact sheet: {source}")
            destination = formal / "qa" / sheet
            if destination.exists() and digest(destination) != digest(source):
                raise ValueError(f"Existing formal contact sheet differs: {sheet}")
        assets[festival] = rows

    for key in ("qualified_groups", "qualified_all_day"):
        old = [
            row for row in manifest[key]
            if row.get("city") == CITY and row.get("festival") in FESTIVALS
        ]
        if old:
            raise ValueError(f"Taichung festival manifest already has {len(old)} records in {key}")
    return {"manifest": manifest, "manifest_path": manifest_path, "assets": assets}


def records(assets: dict[str, list[dict]]) -> tuple[list[dict], list[dict]]:
    groups, all_day = [], []
    for festival, rows in assets.items():
        provenance = f"{festival}_{CITY}_provenance_and_visual_qa.json"
        common = {
            "city": CITY,
            "festival": festival,
            "style": "knitted",
            "character": "person",
            "qualified_at": date.today().isoformat(),
            "source_method": SOURCE_METHOD,
            "visual_qa_record": provenance,
            "criteria": "Individual native-size visual QA and the three festival contact sheets passed; source pixels match the published PNG.",
        }
        for weather in REGULAR_WEATHERS:
            groups.append(common | {
                "weather": weather,
                "periods": list(PERIODS),
                "qa_file": f"{festival}_{CITY}_{weather}_6grid.png",
            })
        for weather in all_day_weathers(CITY, festival):
            all_day.append(common | {
                "weather": weather,
                "asset_file": f"{festival}_{CITY}_person_all_day_{weather}.png",
                "qa_file": f"{festival}_{CITY}_all_day_{len(all_day_weathers(CITY, festival))}grid.png",
                "historical_weather_policy": "ordinary all-day weather",
            })
        if len(rows) != 15:
            raise ValueError(f"Unexpected Taichung matrix size: {festival}")
    return groups, all_day


def publish(staging: Path, formal: Path, data: dict) -> dict:
    qa_dir = formal / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = data["manifest_path"]
    backup = qa_dir / f"qualified_assets.before_Taichung_festivals_{datetime.now():%Y%m%dT%H%M%S}.json"
    shutil.copy2(manifest_path, backup)

    for festival, rows in data["assets"].items():
        for qa in rows:
            filename = qa["filename"]
            copy_new_or_equal(staging / filename, formal / filename)
        for sheet in sheet_names(festival):
            copy_new_or_equal(staging / "qa" / sheet, qa_dir / sheet)
        provenance = {
            "city": CITY,
            "festival": festival,
            "source_method": SOURCE_METHOD,
            "assets": rows,
            "contact_sheets": sheet_names(festival),
            "individual_native_visual_qa": "passed",
            "contact_sheet_visual_qa": "passed",
            "source_pixel_equality": True,
        }
        path = qa_dir / f"{festival}_{CITY}_provenance_and_visual_qa.json"
        if path.exists():
            raise ValueError(f"Existing provenance record: {path}")
        write_json_atomic(path, provenance)

    groups, all_day = records(data["assets"])
    manifest = data["manifest"]
    manifest["qualified_groups"].extend(groups)
    manifest["qualified_all_day"].extend(all_day)
    write_json_atomic(manifest_path, manifest)
    return {"backup": str(backup), "groups_added": len(groups), "all_day_added": len(all_day)}


def verify(staging: Path, formal: Path, original_manifest: dict) -> dict:
    manifest = json.loads((formal / "qa" / "qualified_assets.json").read_text(encoding="utf-8"))
    counts = {}
    for festival in FESTIVALS:
        audit = audit_festival(formal, CITY, festival)
        if not audit["complete"]:
            raise ValueError(f"Formal audit failed: {festival}: {audit}")
        for filename in names(festival):
            if digest(staging / filename) != digest(formal / filename):
                raise ValueError(f"Staging/formal mismatch: {filename}")
        counts[festival] = audit["valid_png_count"]
    for key, expected_added in (("qualified_groups", 10), ("qualified_all_day", 15)):
        old = original_manifest[key]
        new = manifest[key]
        if new[:len(old)] != old or len(new) != len(old) + expected_added:
            raise ValueError(f"Unrelated qualified records changed: {key}")
    if manifest.get("failed_batches") != original_manifest.get("failed_batches"):
        raise ValueError("Unrelated failed-batch records changed")
    return {"formal_counts": counts, "formal_total": sum(counts.values()), "manifest_groups_added": 10, "manifest_all_day_added": 15}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("staging", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("formal", type=Path)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    data = preflight(args.staging, args.checkpoint, args.formal)
    result = {"preflight": "passed", "assets": sum(map(len, data["assets"].values()))}
    if args.publish:
        original_manifest = json.loads(json.dumps(data["manifest"]))
        result.update(publish(args.staging, args.formal, data))
        result.update(verify(args.staging, args.formal, original_manifest))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
