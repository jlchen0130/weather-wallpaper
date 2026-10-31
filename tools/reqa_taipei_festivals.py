from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops

from audit_taipei_festival_assets import FESTIVALS, all_day_weathers, audit_festival


CITY = "Taipei"
EXPECTED_SIZE = (1536, 2752)
ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
MANIFEST = ROOT / "qa" / "qualified_assets.json"
BACKUP = ROOT / "qa" / "qualified_assets.before_Taipei_festival_reqa_20261015.json"
REJECTED = ROOT / "qa" / "rejected" / "Taipei_festival_reqa_2026-10-15"
SOURCE_DIR = Path(__file__).resolve().parent.parent / "taipei_festival_sources"
CHECKPOINT = Path(__file__).resolve().parent.parent / "taipei_festival_reqa_checkpoint.json"

FAILURES = {
    "new_year": ("cloudy", "overcast", "light_rain", "cold_wave"),
    "valentines_day": ("cloudy", "overcast", "light_rain", "cold_wave"),
    "national_day": (
        "cloudy", "overcast", "light_rain", "heavy_rain", "typhoon", "strong_wind"
    ),
    "halloween": (
        "cloudy", "overcast", "light_rain", "heavy_rain", "typhoon", "strong_wind"
    ),
    "constitution_day": ("cloudy", "overcast", "light_rain", "cold_wave"),
}


def filename(festival: str, weather: str) -> str:
    return f"{festival}_{CITY}_person_all_day_{weather}.png"


def expected_names() -> list[str]:
    return [filename(festival, weather) for festival, weathers in FAILURES.items() for weather in weathers]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def source_for(name: str) -> Path:
    stem = Path(name).stem
    matches = [path for path in SOURCE_DIR.glob(stem + ".*") if path.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if len(matches) == 1:
        return matches[0]
    festival = name.split("_Taipei_person_", 1)[0]
    provenance_path = ROOT / "qa" / f"{festival}_{CITY}_provenance_and_visual_qa.json"
    if provenance_path.is_file():
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        records = [row for row in provenance.get("assets", []) if row.get("filename") == name]
        if len(records) == 1:
            recorded = SOURCE_DIR / Path(records[0]["source_file"]).name
            if recorded.is_file():
                return recorded
    raise ValueError(f"Expected one native source for {name}, found {matches}")


def isolate() -> None:
    if not BACKUP.is_file():
        raise FileNotFoundError(f"Required manifest backup missing: {BACKUP}")
    if CHECKPOINT.exists():
        raise FileExistsError(f"Re-QA checkpoint already exists: {CHECKPOINT}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    before = json.loads(BACKUP.read_text(encoding="utf-8"))
    if manifest != before:
        raise ValueError("Current manifest differs from the required pre-re-QA backup")

    REJECTED.mkdir(parents=True, exist_ok=False)
    (REJECTED / "assets").mkdir()
    (REJECTED / "sources").mkdir()
    rejected = []
    for name in expected_names():
        asset = ROOT / name
        source = source_for(name)
        if not asset.is_file():
            raise FileNotFoundError(asset)
        shutil.copy2(asset, REJECTED / "assets" / asset.name)
        shutil.copy2(source, REJECTED / "sources" / source.name)
        rejected.append({
            "filename": name,
            "asset_sha256": digest(asset),
            "source_file": source.name,
            "source_sha256": digest(source),
            "reason": "Fails 2026-10-15 composition re-QA: fewer than 2 clearly recognizable animals, or adverse-weather enclosure/window-scene safety rule",
        })
        asset.unlink()
        source.unlink()

    failed = set(expected_names())
    removed = []
    kept = []
    for record in manifest["qualified_all_day"]:
        if record.get("city") == CITY and record.get("asset_file") in failed:
            removed.append(record)
        else:
            kept.append(record)
    if {row.get("asset_file") for row in removed} != failed:
        raise ValueError("Manifest did not contain exactly the 24 failed Taipei festival records")
    manifest["qualified_all_day"] = kept
    batch_record = {
        "city": CITY,
        "status": "requiring_regeneration",
        "qa_record": str((REJECTED / "failed_visual_qa.json").relative_to(ROOT)).replace("\\", "/"),
        "reason": "24 all-day festival assets failed the 2026-10-15 composition and adverse-weather re-QA",
    }
    manifest.setdefault("failed_batches", []).append(batch_record)
    write_json_atomic(MANIFEST, manifest)
    write_json_atomic(REJECTED / "failed_visual_qa.json", {
        "city": CITY,
        "reviewed_count": 84,
        "retained_count": 60,
        "rejected_count": len(rejected),
        "records": rejected,
        "manifest_records_removed": removed,
    })
    write_json_atomic(CHECKPOINT, {
        "city": CITY,
        "date": date.today().isoformat(),
        "expected": expected_names(),
        "accepted": [],
        "pending": expected_names()[0],
        "rejected_batch": str(REJECTED),
        "manifest_backup": str(BACKUP),
    })
    print(json.dumps({"isolated": len(rejected), "retained": 60, "checkpoint": str(CHECKPOINT)}, indent=2))


def accept(download: Path, name: str, qa: str) -> None:
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if name not in checkpoint["expected"]:
        raise ValueError(f"Out-of-scope filename: {name}")
    if name in {row["filename"] for row in checkpoint["accepted"]}:
        raise ValueError(f"Already accepted: {name}")
    if checkpoint["pending"] != name:
        raise ValueError(f"Expected pending {checkpoint['pending']}, not {name}")

    with Image.open(download) as original:
        original.load()
        if original.format not in {"JPEG", "PNG"} or original.size != EXPECTED_SIZE:
            raise ValueError(f"Not a native Gemini original: {original.format} {original.size}")
        extension = ".jpg" if original.format == "JPEG" else ".png"
        source = SOURCE_DIR / (Path(name).stem + extension)
        output = ROOT / name
        original.convert("RGB").save(output, "PNG")
        shutil.copy2(download, source)
        with Image.open(output) as published:
            published.load()
            if published.format != "PNG" or published.size != EXPECTED_SIZE:
                raise ValueError("Published PNG validation failed")
            if ImageChops.difference(original.convert("RGB"), published.convert("RGB")).getbbox():
                raise ValueError("Native source and published PNG pixels differ")

    row = {
        "filename": name,
        "source_file": source.name,
        "source_sha256": digest(source),
        "png_sha256": digest(ROOT / name),
        "size": list(EXPECTED_SIZE),
        "source_pixel_equality": True,
        "qa": qa,
    }
    checkpoint["accepted"].append(row)
    remaining = [item for item in checkpoint["expected"] if item not in {r["filename"] for r in checkpoint["accepted"]}]
    checkpoint["pending"] = remaining[0] if remaining else None
    write_json_atomic(CHECKPOINT, checkpoint)
    print(json.dumps({"accepted": name, "remaining": len(remaining), "next": checkpoint["pending"]}, indent=2))


def reject(download: Path, name: str, reason: str) -> None:
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if name not in checkpoint["expected"] or checkpoint["pending"] != name:
        raise ValueError(f"Rejected candidate is not the pending scoped asset: {name}")
    with Image.open(download) as image:
        image.load()
        if image.format not in {"JPEG", "PNG"} or image.size != EXPECTED_SIZE:
            raise ValueError(f"Rejected evidence is not a native original: {image.format} {image.size}")
    candidates = REJECTED / "candidates"
    candidates.mkdir(exist_ok=True)
    existing = list(candidates.glob(Path(name).stem + "_attempt*" + download.suffix.lower()))
    target = candidates / f"{Path(name).stem}_attempt{len(existing) + 1}{download.suffix.lower()}"
    shutil.copy2(download, target)
    checkpoint.setdefault("rejected_candidates", []).append({
        "filename": name,
        "source_file": target.name,
        "source_sha256": digest(target),
        "reason": reason,
    })
    write_json_atomic(CHECKPOINT, checkpoint)
    print(json.dumps({"rejected": name, "preserved": str(target), "reason": reason}, indent=2))


def finalize() -> None:
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    accepted = {row["filename"]: row for row in checkpoint["accepted"]}
    if set(accepted) != set(expected_names()) or checkpoint["pending"] is not None:
        raise ValueError("All 24 replacements must be individually accepted before finalization")

    builder = Path(__file__).with_name("build_taipei_festival_contact_sheets.py")
    for festival in FESTIVALS:
        subprocess.run([sys.executable, str(builder), str(ROOT), festival], check=True)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    before_non_taipei = {
        key: [row for row in manifest[key] if row.get("city") != CITY]
        for key in ("qualified_groups", "qualified_all_day")
    }
    for festival, weathers in FAILURES.items():
        qa_file = f"{festival}_{CITY}_all_day_{len(all_day_weathers(festival))}grid.png"
        for weather in weathers:
            name = filename(festival, weather)
            manifest["qualified_all_day"].append({
                "city": CITY,
                "festival": festival,
                "style": "knitted",
                "character": "person",
                "weather": weather,
                "asset_file": name,
                "qualified_at": date.today().isoformat(),
                "source_method": "Gemini web original native 1536x2752; decoded to PNG without resizing or overlays",
                "visual_qa_record": f"{festival}_{CITY}_provenance_and_visual_qa.json",
                "qa_file": qa_file,
                "criteria": accepted[name]["qa"] + "; 2026-10-15 composition re-QA; native source pixel equality passed",
                "historical_weather_policy": "adverse weather retained only with authoritative CWA historical evidence" if weather not in {"cloudy", "overcast", "light_rain"} else "ordinary all-day weather",
            })
    manifest["failed_batches"][-1]["status"] = "replaced_and_requalified"
    write_json_atomic(MANIFEST, manifest)

    for festival in FESTIVALS:
        prefix = f"{festival}_{CITY}_person_"
        source_records = []
        for name in sorted(path.name for path in ROOT.glob(prefix + "*.png")):
            source = source_for(name)
            with Image.open(source) as original, Image.open(ROOT / name) as published:
                original.load(); published.load()
                if original.size != EXPECTED_SIZE or published.size != EXPECTED_SIZE:
                    raise ValueError(f"Native dimensions failed: {name}")
                if ImageChops.difference(original.convert("RGB"), published.convert("RGB")).getbbox():
                    raise ValueError(f"Source pixel equality failed: {name}")
            source_records.append({
                "filename": name,
                "source_file": str(source.resolve()),
                "source_sha256": digest(source),
                "png_sha256": digest(ROOT / name),
                "source_pixel_equality": True,
                "qa": accepted.get(name, {}).get("qa", "Retained after 2026-10-15 full visual re-QA"),
            })
        write_json_atomic(ROOT / "qa" / f"{festival}_{CITY}_provenance_and_visual_qa.json", {
            "city": CITY,
            "festival": festival,
            "reviewed_at": date.today().isoformat(),
            "assets": source_records,
            "reviewed_sheets": [
                f"qa/{festival}_{CITY}_sunny_6grid.png",
                f"qa/{festival}_{CITY}_partly_cloudy_6grid.png",
                f"qa/{festival}_{CITY}_all_day_{len(all_day_weathers(festival))}grid.png",
            ],
        })

    final = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key, rows in before_non_taipei.items():
        if [row for row in final[key] if row.get("city") != CITY] != rows:
            raise AssertionError(f"Non-Taipei manifest records changed in {key}")
    audits = {festival: audit_festival(ROOT, festival) for festival in FESTIVALS}
    if not all(result["complete"] for result in audits.values()):
        raise ValueError(f"Final festival audit failed: {audits}")
    checkpoint["finalized"] = True
    checkpoint["audit"] = audits
    checkpoint["manifest_replacements"] = len(expected_names())
    write_json_atomic(CHECKPOINT, checkpoint)
    print(json.dumps({"finalized": True, "replacements": 24, "audits": audits}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("isolate")
    accept_parser = sub.add_parser("accept")
    accept_parser.add_argument("download", type=Path)
    accept_parser.add_argument("filename")
    accept_parser.add_argument("--qa", required=True)
    reject_parser = sub.add_parser("reject")
    reject_parser.add_argument("download", type=Path)
    reject_parser.add_argument("filename")
    reject_parser.add_argument("--reason", required=True)
    sub.add_parser("finalize")
    args = parser.parse_args()
    if args.command == "isolate":
        isolate()
    elif args.command == "accept":
        accept(args.download.resolve(), args.filename, args.qa)
    elif args.command == "reject":
        reject(args.download.resolve(), args.filename, args.reason)
    else:
        finalize()


if __name__ == "__main__":
    main()
