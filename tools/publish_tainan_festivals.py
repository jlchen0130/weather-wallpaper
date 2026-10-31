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
    full_screen_gpt_size,
)


CITY = "Tainan"
SOURCE_METHOD = "Gemini native JPEG or OpenAI built-in native PNG; see per-image provenance"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def names(festival: str) -> list[str]:
    return [
        f"{festival}_{CITY}_person_{period}_{weather}.png"
        for weather in REGULAR_WEATHERS for period in PERIODS
    ] + [
        f"{festival}_{CITY}_person_all_day_{weather}.png"
        for weather in all_day_weathers(CITY, festival)
    ]


def sheets(festival: str) -> list[str]:
    return [
        f"{festival}_{CITY}_sunny_6grid.png",
        f"{festival}_{CITY}_partly_cloudy_6grid.png",
        f"{festival}_{CITY}_all_day_{len(all_day_weathers(CITY, festival))}grid.png",
    ]


def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def copy_new_or_equal(source: Path, destination: Path) -> None:
    if destination.exists():
        if digest(source) != digest(destination):
            raise ValueError(f"Existing formal file differs: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)


def validate_source(source: Path, png: Path, record: dict) -> None:
    with Image.open(source) as original, Image.open(png) as output:
        original.load()
        output.load()
        if output.format != "PNG" or output.size != tuple(record["size"]):
            raise ValueError(f"Staged image format or size mismatch: {png.name}")
        if record["source_method"] == "OpenAI built-in image generation":
            if (original.format != "PNG" or not full_screen_gpt_size(original.size)
                    or original.size != output.size or record.get("no_resize") is not True
                    or record.get("native_source_size") != list(original.size)
                    or digest(source) != digest(png)):
                raise ValueError(f"GPT original is not an unresized phone wallpaper: {png.name}")
        elif record["source_method"].startswith("Gemini web native JPEG"):
            if (original.format != "JPEG" or original.size != EXPECTED_SIZE
                    or output.size != EXPECTED_SIZE
                    or ImageChops.difference(original.convert("RGB"), output.convert("RGB")).getbbox()):
                raise ValueError(f"Gemini native JPEG pixels differ: {png.name}")
        else:
            raise ValueError(f"Unknown source method: {png.name}")


def preflight(staging: Path, checkpoint: Path, formal: Path) -> dict:
    state = json.loads(checkpoint.read_text(encoding="utf-8"))
    if (state.get("city") != CITY or state.get("next_slot") is not None
            or state.get("staged_valid_png_count") != 75):
        raise ValueError(f"{CITY} festival checkpoint is not finished")
    manifest_path = formal / "qa" / "qualified_assets.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in ("qualified_groups", "qualified_all_day"):
        if not isinstance(manifest.get(key), list):
            raise ValueError(f"Unexpected manifest schema: {key}")
        if any(row.get("city") == CITY and row.get("festival") in FESTIVALS
               for row in manifest[key]):
            raise ValueError(f"{CITY} festival records already exist; refusing duplicate publication")

    assets = {}
    for festival in FESTIVALS:
        audit = audit_festival(staging, CITY, festival)
        if not audit["complete"] or audit["valid_png_count"] != 15:
            raise ValueError(f"Incomplete staging: {festival}: {audit}")
        for weather in (*REGULAR_WEATHERS, "all_day"):
            batch = state.get("completed_batch_qa", {}).get(f"{festival}_{weather}")
            if (not isinstance(batch, dict)
                    or batch.get("status") != "passed_no_major_error_not_formally_qualified"):
                raise ValueError(f"Missing batch visual QA: {festival}/{weather}")
        rows = []
        for filename in names(festival):
            png = staging / filename
            qa_path = staging / "qa" / f"{Path(filename).stem}.json"
            record = json.loads(qa_path.read_text(encoding="utf-8"))
            if (record.get("filename") != filename or record.get("city") != CITY
                    or record.get("festival") != festival
                    or record.get("status") != "staged_individual_qa_passed_not_batch_qualified"
                    or not record.get("qa")):
                raise ValueError(f"Individual QA identity/status mismatch: {filename}")
            source = staging / record["source_file"]
            if (digest(png) != record.get("png_sha256")
                    or digest(source) != record.get("source_sha256")):
                raise ValueError(f"Source or PNG hash mismatch: {filename}")
            validate_source(source, png, record)
            for src, dst in ((png, formal / filename),
                             (source, formal / record["source_file"])):
                if dst.exists() and digest(src) != digest(dst):
                    raise ValueError(f"Formal collision: {dst}")
            formal_qa = formal / "qa" / qa_path.name
            if formal_qa.exists():
                existing = json.loads(formal_qa.read_text(encoding="utf-8"))
                if existing != record:
                    raise ValueError(f"Existing QA record differs: {formal_qa}")
            rows.append(record)
        for sheet in sheets(festival):
            src, dst = staging / "qa" / sheet, formal / "qa" / sheet
            if not src.is_file() or (dst.exists() and digest(src) != digest(dst)):
                raise ValueError(f"Contact sheet missing or different: {sheet}")
        assets[festival] = rows
    return {"manifest": manifest, "manifest_path": manifest_path, "assets": assets}


def publish(staging: Path, formal: Path, data: dict) -> dict:
    qa_dir = formal / "qa"
    backup = qa_dir / f"qualified_assets.before_{CITY}_festivals_{datetime.now():%Y%m%dT%H%M%S}.json"
    shutil.copy2(data["manifest_path"], backup)
    groups, all_day = [], []
    for festival, rows in data["assets"].items():
        for record in rows:
            filename = record["filename"]
            copy_new_or_equal(staging / filename, formal / filename)
            copy_new_or_equal(staging / record["source_file"], formal / record["source_file"])
            write_json_atomic(qa_dir / f"{Path(filename).stem}.json",
                              record | {"status": "published_qualified"})
        for sheet in sheets(festival):
            copy_new_or_equal(staging / "qa" / sheet, qa_dir / sheet)
        provenance_name = f"{festival}_{CITY}_provenance_and_visual_qa.json"
        write_json_atomic(qa_dir / provenance_name, {
            "city": CITY, "festival": festival, "source_method": SOURCE_METHOD,
            "assets": [row | {"status": "published_qualified"} for row in rows],
            "contact_sheets": sheets(festival),
            "individual_native_visual_qa": "passed",
            "contact_sheet_visual_qa": "passed",
        })
        common = {
            "city": CITY, "festival": festival, "style": "knitted", "character": "person",
            "qualified_at": date.today().isoformat(), "source_method": SOURCE_METHOD,
            "visual_qa_record": provenance_name,
            "criteria": "Native-source visual QA and three festival contact sheets passed; source hashes and published PNGs verified.",
        }
        for weather in REGULAR_WEATHERS:
            groups.append(common | {"weather": weather, "periods": list(PERIODS),
                                    "qa_file": f"{festival}_{CITY}_{weather}_6grid.png"})
        for weather in all_day_weathers(CITY, festival):
            all_day.append(common | {
                "weather": weather,
                "asset_file": f"{festival}_{CITY}_person_all_day_{weather}.png",
                "qa_file": f"{festival}_{CITY}_all_day_{len(all_day_weathers(CITY, festival))}grid.png",
                "historical_weather_policy": "ordinary all-day weather",
            })
    manifest = data["manifest"]
    manifest["qualified_groups"].extend(groups)
    manifest["qualified_all_day"].extend(all_day)
    write_json_atomic(data["manifest_path"], manifest)
    return {"backup": str(backup), "groups_added": len(groups), "all_day_added": len(all_day)}


def verify(staging: Path, formal: Path, original: dict) -> dict:
    manifest = json.loads((formal / "qa" / "qualified_assets.json").read_text(encoding="utf-8"))
    counts = {}
    for festival in FESTIVALS:
        audit = audit_festival(formal, CITY, festival)
        if not audit["complete"]:
            raise ValueError(f"Formal festival audit failed: {festival}: {audit}")
        for filename in names(festival):
            if digest(staging / filename) != digest(formal / filename):
                raise ValueError(f"Published PNG differs from staging: {filename}")
            record = json.loads((formal / "qa" / f"{Path(filename).stem}.json").read_text(encoding="utf-8"))
            if record.get("status") != "published_qualified":
                raise ValueError(f"Formal QA not qualified: {filename}")
        counts[festival] = audit["valid_png_count"]
    for key, added in (("qualified_groups", 10), ("qualified_all_day", 15)):
        if (manifest[key][:len(original[key])] != original[key]
                or len(manifest[key]) != len(original[key]) + added):
            raise ValueError(f"Unrelated manifest records changed: {key}")
    if manifest.get("failed_batches") != original.get("failed_batches"):
        raise ValueError("Unrelated failed-batch records changed")
    return {"formal_counts": counts, "formal_total": sum(counts.values())}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("staging", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("formal", type=Path)
    parser.add_argument("--city", choices=("Tainan", "Kaohsiung", "Keelung"), default="Tainan")
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    global CITY
    CITY = args.city
    data = preflight(args.staging, args.checkpoint, args.formal)
    result = {"preflight": "passed", "assets": sum(map(len, data["assets"].values()))}
    if args.publish:
        original = json.loads(json.dumps(data["manifest"]))
        result.update(publish(args.staging, args.formal, data))
        result.update(verify(args.staging, args.formal, original))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
