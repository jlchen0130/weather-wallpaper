from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops

from audit_newtaipei_festival_assets import (
    CITY,
    PERIODS,
    REGULAR_WEATHERS,
    all_day_weathers,
    audit_festival,
)


SOURCE_METHOD = (
    "Gemini web original native 1536x2752; decoded to PNG without resizing or overlays"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_equal(source: Path, png: Path) -> bool:
    with Image.open(source) as original, Image.open(png) as converted:
        a = original.convert("RGB")
        b = converted.convert("RGB")
        return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


def asset_specs(festival: str) -> list[tuple[str, str]]:
    specs: list[tuple[str, str]] = []
    for weather in REGULAR_WEATHERS:
        for period in PERIODS:
            specs.append((f"{period}_{weather}", f"{festival}_{CITY}_person_{period}_{weather}.png"))
    for weather in all_day_weathers(festival):
        specs.append((f"all_day_{weather}", f"{festival}_{CITY}_person_all_day_{weather}.png"))
    return specs


def manifest_records(festival: str) -> list[dict[str, object]]:
    all_day = all_day_weathers(festival)
    qa_all_day = f"{festival}_{CITY}_all_day_{len(all_day)}grid.png"
    common = {
        "city": CITY,
        "festival": festival,
        "style": "knitted",
        "character": "person",
        "qualified_at": date.today().isoformat(),
        "source_method": SOURCE_METHOD,
        "visual_qa_record": f"{festival}_{CITY}_provenance_and_visual_qa.json",
        "criteria": (
            "Individual major-error review and all three contact sheets passed; "
            "native source pixel equality verified; NewTaipei only."
        ),
    }
    records: list[dict[str, object]] = []
    for weather in REGULAR_WEATHERS:
        records.append(
            common
            | {
                "weather": weather,
                "periods": list(PERIODS),
                "qa_file": f"{festival}_{CITY}_{weather}_6grid.png",
            }
        )
    for weather in all_day:
        record = common | {
            "weather": weather,
            "asset_file": f"{festival}_{CITY}_person_all_day_{weather}.png",
            "qa_file": qa_all_day,
        }
        if weather not in {"cloudy", "overcast", "light_rain"}:
            record["historical_weather_policy"] = (
                "adverse weather retained only with CWA historical evidence"
            )
        records.append(record)
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("staging", type=Path)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("festival")
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()

    audit = audit_festival(args.staging, args.festival)
    if not audit["complete"]:
        raise SystemExit(f"Refusing incomplete festival: {json.dumps(audit)}")

    source_map_path = args.staging / "qa" / f"{args.festival}_source_map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    provenance: list[dict[str, object]] = []
    specs = asset_specs(args.festival)
    if set(source_map) != {key for key, _ in specs}:
        raise SystemExit("Source map does not exactly match the expected asset set")

    for key, filename in specs:
        source = args.cache / source_map[key]
        png = args.staging / filename
        if not pixel_equal(source, png):
            raise SystemExit(f"Source pixel equality failed: {filename}")
        provenance.append(
            {
                "filename": filename,
                "source_cache": source.name,
                "source_file": str(source),
                "size": [1536, 2752],
                "source_sha256": sha256(source),
                "png_sha256": sha256(png),
                "source_pixel_equality": True,
                "qa": "individual major-error review passed; group contact sheet reviewed",
            }
        )

    qa_dir = args.formal_root / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    for _, filename in specs:
        shutil.copy2(args.staging / filename, args.formal_root / filename)
    qa_names = [
        f"{args.festival}_{CITY}_sunny_6grid.png",
        f"{args.festival}_{CITY}_partly_cloudy_6grid.png",
        f"{args.festival}_{CITY}_all_day_{len(all_day_weathers(args.festival))}grid.png",
    ]
    for filename in qa_names:
        shutil.copy2(args.staging / "qa" / filename, qa_dir / filename)

    qa_record = {
        "city": CITY,
        "festival": args.festival,
        "source_method": SOURCE_METHOD,
        "assets": provenance,
        "contact_sheets": qa_names,
        "major_error_qa": "passed",
        "source_pixel_equality": True,
    }
    qa_record_name = f"{args.festival}_{CITY}_provenance_and_visual_qa.json"
    (qa_dir / qa_record_name).write_text(
        json.dumps(qa_record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    manifest_path = qa_dir / "qualified_assets.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    groups = manifest["qualified_groups"]
    groups[:] = [
        record
        for record in groups
        if not (record.get("city") == CITY and record.get("festival") == args.festival)
    ]
    groups.extend(manifest_records(args.festival))
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    published = audit_festival(args.formal_root, args.festival)
    if not published["complete"]:
        raise SystemExit(f"Published audit failed: {json.dumps(published)}")
    print(json.dumps({"published": published, "manifest_records": len(manifest_records(args.festival))}, indent=2))


if __name__ == "__main__":
    main()
