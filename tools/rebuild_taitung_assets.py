"""Stage native-size Gemini Taitung assets; publish only after recorded visual QA."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image

from build_all_day_contact_sheet import WEATHERS, build_sheet as all_day_sheet
from build_weather_contact_sheet import PERIODS, build_sheet as regular_sheet

ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
STAGE = Path(__file__).resolve().parents[1] / "output" / "taitung_repair"
SIZE = (1536, 2752)
MASTER = "master/none_Taitung_person_master.png"
REQUIRED = [MASTER]
REQUIRED += [f"none_Taitung_person_{period}_{weather}.png" for weather in ("sunny", "partly_cloudy") for period in PERIODS]
REQUIRED += [f"none_Taitung_person_all_day_{weather}.png" for weather in WEATHERS]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(path: Path) -> None:
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != SIZE:
            raise ValueError(f"Invalid formal image: {path.name}: {image.format} {image.size}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("ingest", "sheets", "review-sheet", "publish", "status"))
    parser.add_argument("--source", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--note")
    parser.add_argument("--prompt")
    args = parser.parse_args()
    STAGE.mkdir(parents=True, exist_ok=True)
    log = STAGE / "provenance_and_visual_qa.json"
    data = json.loads(log.read_text(encoding="utf-8")) if log.exists() else {"city": "Taitung", "date": "2026-10-10", "assets": {}, "sheets": {}}

    if args.action == "ingest":
        if args.name not in REQUIRED or not args.source or not args.note or not args.prompt:
            raise ValueError("Supply canonical Taitung name, source, visual review note and prompt")
        target = STAGE / args.name
        if target.exists():
            raise FileExistsError(target)
        with Image.open(args.source) as image:
            image.load()
            if image.size != SIZE:
                raise ValueError(f"Native resolution required, got {image.size}; no resizing allowed")
            original_format = image.format
            pixels = image.convert("RGB").tobytes()
            target.parent.mkdir(parents=True, exist_ok=True)
            image.convert("RGB").save(target, "PNG")
        original = STAGE / "originals" / (Path(args.name).stem + args.source.suffix)
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.source, original)
        validate(target)
        with Image.open(target) as output:
            output.load()
            if output.tobytes() != pixels:
                raise RuntimeError("Source/output pixel mismatch")
        data["assets"][args.name] = {
            "source_method": "Gemini web generated original, native 1536x2752; decoded and saved as PNG without resizing or drawing overlays",
            "original_format": original_format,
            "original_file": str(original.relative_to(STAGE)),
            "original_sha256": digest(original),
            "sha256": digest(target),
            "visual_qa": "passed",
            "review_note": args.note,
            "prompt": args.prompt,
        }
    elif args.action == "sheets":
        for weather in ("sunny", "partly_cloudy"):
            if all((STAGE / f"none_Taitung_person_{period}_{weather}.png").exists() for period in PERIODS):
                regular_sheet(STAGE, "Taitung", weather, STAGE / "qa" / f"Taitung_{weather}_6grid.png")
        if all((STAGE / f"none_Taitung_person_all_day_{weather}.png").exists() for weather in WEATHERS):
            all_day_sheet(STAGE, "Taitung", STAGE / "qa" / "Taitung_all_day_12grid.png")
    elif args.action == "review-sheet":
        allowed = ["Taitung_sunny_6grid.png", "Taitung_partly_cloudy_6grid.png", "Taitung_all_day_12grid.png"]
        if args.name not in allowed or not args.note:
            raise ValueError("Explicit review of an existing Taitung QA sheet required")
        data["sheets"][args.name] = {"sha256": digest(STAGE / "qa" / args.name), "visual_qa": "passed", "note": args.note}
    elif args.action == "publish":
        for name in REQUIRED:
            validate(STAGE / name)
            record = data["assets"].get(name, {})
            if record.get("visual_qa") != "passed" or record.get("sha256") != digest(STAGE / name):
                raise ValueError(f"Unreviewed or changed asset: {name}")
            original = STAGE / record["original_file"]
            if digest(original) != record["original_sha256"]:
                raise ValueError(f"Changed original source: {name}")
            with Image.open(original) as source, Image.open(STAGE / name) as output:
                source.load()
                output.load()
                if source.size != SIZE or source.convert("RGB").tobytes() != output.tobytes():
                    raise ValueError(f"Source/output pixel mismatch: {name}")
        sheet_names = ["Taitung_sunny_6grid.png", "Taitung_partly_cloudy_6grid.png", "Taitung_all_day_12grid.png"]
        for name in sheet_names:
            if data["sheets"].get(name, {}).get("visual_qa") != "passed" or data["sheets"].get(name, {}).get("sha256") != digest(STAGE / "qa" / name):
                raise ValueError(f"Unreviewed or changed QA sheet: {name}")
        manifest = ROOT / "qa" / "qualified_assets.json"
        qualified = json.loads(manifest.read_text(encoding="utf-8"))
        if any(e.get("city") == "Taitung" for key in ("qualified_groups", "qualified_all_day") for e in qualified.get(key, [])):
            raise RuntimeError("Unexpected existing Taitung qualification")
        for name in REQUIRED + [f"qa/{name}" for name in sheet_names]:
            destination = ROOT / name
            destination.resolve().relative_to(ROOT.resolve())
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite formal file: {destination}")
        for name in REQUIRED + [f"qa/{name}" for name in sheet_names]:
            destination = ROOT / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(STAGE / name, destination)
            if digest(destination) != digest(STAGE / name):
                raise RuntimeError(f"Publication hash mismatch: {name}")
        common = {
            "city": "Taitung", "style": "knitted", "character": "person", "qualified_at": "2026-10-11",
            "master_file": MASTER, "source_method": data["assets"][MASTER]["source_method"],
            "visual_qa_record": "Taitung_provenance_and_visual_qa.json",
        }
        for weather in ("sunny", "partly_cloudy"):
            qualified["qualified_groups"].append({**common, "weather": weather, "periods": list(PERIODS), "qa_file": f"Taitung_{weather}_6grid.png", "criteria": "Every native Gemini source and six-period sheet visually reviewed for fine matte dimensional needle-felt, grounded person, Taitung identity, correct celestial/time cues and prohibited-content absence; PNGs fully decoded at 1536x2752."})
        for weather in WEATHERS:
            qualified["qualified_all_day"].append({**common, "weather": weather, "asset_file": f"none_Taitung_person_all_day_{weather}.png", "qa_file": "Taitung_all_day_12grid.png", "criteria": data["assets"][f"none_Taitung_person_all_day_{weather}.png"]["review_note"]})
        shutil.copy2(log, ROOT / "qa" / "Taitung_provenance_and_visual_qa.json")
        manifest.write_text(json.dumps(qualified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"staged_reviewed_assets": len(data["assets"]), "reviewed_sheets": len(data["sheets"]), "missing": [name for name in REQUIRED if name not in data["assets"]]}))


if __name__ == "__main__":
    main()
