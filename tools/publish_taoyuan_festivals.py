from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date, datetime
from pathlib import Path

from PIL import Image, ImageChops

from audit_taoyuan_festival_assets import (
    CITY,
    EXPECTED_SIZE,
    FESTIVALS,
    PERIODS,
    REGULAR_WEATHERS,
    all_day_weathers,
    audit_festival,
)


SOURCE_METHOD = "Gemini web original native 1536x2752; decoded to PNG without resizing or overlays"
VISUAL_CRITERIA = (
    "Existing individual and contact-sheet visual QA passed: long-shot scenery-dominant composition, "
    "multiple Taoyuan landmarks, 3-5 people and 2-4 animals; adverse weather keeps every person and "
    "animal indoors behind closed glass with the outdoor scene empty except one distant Airport MRT train."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_equal(left: Path, right: Path) -> bool:
    with Image.open(left) as a_image, Image.open(right) as b_image:
        a = a_image.convert("RGB")
        b = b_image.convert("RGB")
        return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


def asset_specs(festival: str) -> list[tuple[str, str]]:
    specs = [
        (f"{period}_{weather}", f"{festival}_{CITY}_person_{period}_{weather}.png")
        for weather in REGULAR_WEATHERS
        for period in PERIODS
    ]
    specs.extend(
        (f"all_day_{weather}", f"{festival}_{CITY}_person_all_day_{weather}.png")
        for weather in all_day_weathers(festival)
    )
    return specs


def qa_names(festival: str) -> list[str]:
    return [
        f"{festival}_{CITY}_sunny_6grid.png",
        f"{festival}_{CITY}_partly_cloudy_6grid.png",
        f"{festival}_{CITY}_all_day_{len(all_day_weathers(festival))}grid.png",
    ]


def manifest_records(festival: str) -> list[dict[str, object]]:
    common = {
        "city": CITY,
        "festival": festival,
        "style": "knitted",
        "character": "person",
        "qualified_at": date.today().isoformat(),
        "source_method": SOURCE_METHOD,
        "visual_qa_record": f"{festival}_{CITY}_provenance_and_visual_qa.json",
        "criteria": VISUAL_CRITERIA,
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
    all_day = all_day_weathers(festival)
    all_day_qa = f"{festival}_{CITY}_all_day_{len(all_day)}grid.png"
    for weather in all_day:
        record = common | {
            "weather": weather,
            "asset_file": f"{festival}_{CITY}_person_all_day_{weather}.png",
            "qa_file": all_day_qa,
        }
        if weather not in {"cloudy", "overcast", "light_rain"}:
            record["historical_weather_policy"] = "adverse weather retained only with CWA historical evidence"
        records.append(record)
    return records


def write_json_atomic(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("staging", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()

    checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    accepted = {row["filename"]: row for row in checkpoint["accepted_individually"]}
    expected_names = {filename for festival in FESTIVALS for _, filename in asset_specs(festival)}
    if set(accepted) != expected_names:
        missing = sorted(expected_names - set(accepted))
        unexpected = sorted(set(accepted) - expected_names)
        raise SystemExit(f"Checkpoint mismatch: missing={missing}, unexpected={unexpected}")

    for festival in FESTIVALS:
        audit = audit_festival(args.staging, festival)
        if not audit["complete"]:
            raise SystemExit(f"Refusing incomplete festival {festival}: {json.dumps(audit)}")

    provenance_by_festival: dict[str, list[dict[str, object]]] = {}
    for festival in FESTIVALS:
        provenance: list[dict[str, object]] = []
        for _, filename in asset_specs(festival):
            row = accepted[filename]
            source = args.source_root / str(row["source_file"])
            staged = args.staging / filename
            if not source.is_file():
                raise SystemExit(f"Missing native source: {source}")
            with Image.open(staged) as image:
                image.load()
                if image.format != "PNG" or image.size != EXPECTED_SIZE:
                    raise SystemExit(f"Invalid staged PNG: {filename}")
            if not pixel_equal(source, staged):
                raise SystemExit(f"Source/staged pixel mismatch: {filename}")
            provenance.append(
                {
                    "filename": filename,
                    "source_file": str(source),
                    "source_sha256": sha256(source),
                    "png_sha256": sha256(staged),
                    "size": list(EXPECTED_SIZE),
                    "source_pixel_equality": True,
                    "qa": row["qa"],
                }
            )
        provenance_by_festival[festival] = provenance

    qa_dir = args.formal_root / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = qa_dir / "qualified_assets.json"
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    manifest_backup = qa_dir / f"qualified_assets.before_{CITY}_festivals_{stamp}.json"
    shutil.copy2(manifest_path, manifest_backup)

    for festival in FESTIVALS:
        for _, filename in asset_specs(festival):
            shutil.copy2(args.staging / filename, args.formal_root / filename)
        names = qa_names(festival)
        for filename in names:
            shutil.copy2(args.staging / "qa" / filename, qa_dir / filename)
        qa_record = {
            "city": CITY,
            "festival": festival,
            "source_method": SOURCE_METHOD,
            "assets": provenance_by_festival[festival],
            "contact_sheets": names,
            "major_error_qa": "passed from existing per-image and contact-sheet review",
            "visual_criteria": VISUAL_CRITERIA,
            "source_pixel_equality": True,
        }
        write_json_atomic(qa_dir / f"{festival}_{CITY}_provenance_and_visual_qa.json", qa_record)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    groups = manifest["qualified_groups"]
    preserved = [
        record
        for record in groups
        if not (record.get("city") == CITY and record.get("festival") in FESTIVALS)
    ]
    added = [record for festival in FESTIVALS for record in manifest_records(festival)]
    manifest["qualified_groups"] = preserved + added
    write_json_atomic(manifest_path, manifest)

    published_counts: dict[str, int] = {}
    verified = 0
    for festival in FESTIVALS:
        audit = audit_festival(args.formal_root, festival)
        if not audit["complete"]:
            raise SystemExit(f"Published audit failed for {festival}: {json.dumps(audit)}")
        published_counts[festival] = int(audit["valid_png_count"])
        for _, filename in asset_specs(festival):
            source = args.source_root / str(accepted[filename]["source_file"])
            published = args.formal_root / filename
            if not pixel_equal(source, published):
                raise SystemExit(f"Source/published pixel mismatch: {filename}")
            verified += 1

    rejected_published = [path.name for path in args.formal_root.glob("*Taoyuan*rejected*.png")]
    torrential = [path.name for path in args.formal_root.glob("*Taoyuan*torrential_rain*.png")]
    if rejected_published or torrential:
        raise SystemExit(f"Forbidden published files: rejected={rejected_published}, torrential={torrential}")

    print(
        json.dumps(
            {
                "formal_root": str(args.formal_root),
                "published_counts": published_counts,
                "published_total": sum(published_counts.values()),
                "source_published_pixel_equal": verified,
                "manifest_backup": str(manifest_backup),
                "manifest_records_added": len(added),
                "rejected_published": rejected_published,
                "torrential_rain_published": torrential,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
