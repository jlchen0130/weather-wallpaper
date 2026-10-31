from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image


CITY = "Taichung"
EXPECTED_SIZE = (1536, 2752)
ALL_DAY_WEATHERS = (
    "cloudy", "overcast", "light_rain", "heavy_rain", "typhoon", "fog",
    "haze", "strong_wind", "thunder_shower", "thunderstorm", "heatwave",
    "cold_wave",
)
REPLACEMENTS = ALL_DAY_WEATHERS[3:]


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_png(path: Path, expected_size: tuple[int, int] = EXPECTED_SIZE) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != expected_size:
            raise ValueError(
                f"Invalid PNG {path}: format={image.format!r}, size={image.size!r}"
            )


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def non_taichung_manifest(manifest: dict[str, object]) -> dict[str, object]:
    return {
        key: [item for item in manifest.get(key, []) if item.get("city") != CITY]
        for key in ("qualified_groups", "qualified_all_day", "failed_batches")
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--date", default="2026-10-18")
    args = parser.parse_args()

    root = args.formal_root.resolve()
    qa_dir = root / "qa"
    stage = qa_dir / "staging" / "Taichung_2026-10-18_closed_glass"
    rejected = qa_dir / "rejected" / "Taichung_2026-10-18_closed_glass"
    manifest_path = qa_dir / "qualified_assets.json"
    sheet_name = "Taichung_all_day_12grid.png"
    stage_sheet = stage / sheet_name

    checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    if checkpoint.get("scope") != "Taichung base weather assets only; festivals forbidden":
        raise ValueError("Checkpoint scope is not Taichung base-weather only")
    if checkpoint.get("status") not in {"ready_to_publish", "complete"}:
        raise ValueError(f"Checkpoint is not publishable: {checkpoint.get('status')!r}")

    for weather in ALL_DAY_WEATHERS:
        validate_png(stage / f"none_{CITY}_person_all_day_{weather}.png")
    validate_png(stage_sheet, expected_size=(1632, 2390))

    for weather in REPLACEMENTS:
        filename = f"none_{CITY}_person_all_day_{weather}.png"
        backup = rejected / filename
        if not backup.is_file():
            raise FileNotFoundError(f"Missing preserved rejected formal asset: {backup}")
        validate_png(backup)

    rejected_candidate = Path(
        r"C:\Users\JL\Downloads\Gemini_Generated_Image_hf94gjhf94gjhf94.jfif"
    )
    if rejected_candidate.is_file():
        with Image.open(rejected_candidate) as image:
            image.load()
            if image.format != "JPEG" or image.size != EXPECTED_SIZE:
                raise ValueError("Rejected heatwave candidate is not the expected native JPEG")
        rejected_copy = rejected / (
            "candidate_heatwave_outdoor_people_"
            "Gemini_Generated_Image_hf94gjhf94gjhf94.jfif"
        )
        if not rejected_copy.exists():
            atomic_copy(rejected_candidate, rejected_copy)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    untouched_before = canonical_hash(non_taichung_manifest(manifest))

    existing_all_day = [
        item for item in manifest.get("qualified_all_day", [])
        if not (item.get("city") == CITY and item.get("weather") in REPLACEMENTS)
    ]
    for weather in REPLACEMENTS:
        existing_all_day.append(
            {
                "city": CITY,
                "style": "knitted",
                "character": "person",
                "weather": weather,
                "asset_file": f"none_{CITY}_person_all_day_{weather}.png",
                "master_file": "master/none_Taichung_person_master.png",
                "qa_file": sheet_name,
                "qualified_at": args.date,
                "source_method": "native Gemini 1536x2752 JPEG decoded to RGB PNG without resizing",
                "visual_qa": "passed",
                "criteria": (
                    "Taichung adverse-weather visual QA passed: every person and animal "
                    "is inside one fully enclosed room behind closed glass; the exterior "
                    "contains no people, animals, vehicles, bicycles, vendors, flags or "
                    "silhouettes; multiple Taichung landmarks and fine matte needle-felt "
                    "texture retained"
                ),
            }
        )
    manifest["qualified_all_day"] = existing_all_day

    taichung_all_day = [
        item for item in manifest["qualified_all_day"] if item.get("city") == CITY
    ]
    keys = [(item.get("city"), item.get("weather")) for item in taichung_all_day]
    if len(taichung_all_day) != 12 or set(keys) != {
        (CITY, weather) for weather in ALL_DAY_WEATHERS
    }:
        raise ValueError(f"Unexpected Taichung all-day manifest set: {keys}")

    if untouched_before != canonical_hash(non_taichung_manifest(manifest)):
        raise AssertionError("Non-Taichung manifest records changed before publication")

    for weather in REPLACEMENTS:
        filename = f"none_{CITY}_person_all_day_{weather}.png"
        atomic_copy(stage / filename, root / filename)
    atomic_copy(stage_sheet, qa_dir / sheet_name)
    atomic_json(manifest_path, manifest)

    published_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    untouched_after = canonical_hash(non_taichung_manifest(published_manifest))
    if untouched_after != untouched_before:
        raise AssertionError("Non-Taichung manifest records changed during publication")

    hashes: dict[str, str] = {}
    for weather in REPLACEMENTS:
        filename = f"none_{CITY}_person_all_day_{weather}.png"
        source = stage / filename
        destination = root / filename
        validate_png(destination)
        source_hash = file_hash(source)
        destination_hash = file_hash(destination)
        if source_hash != destination_hash:
            raise AssertionError(f"Published bytes differ for {filename}")
        hashes[weather] = destination_hash
    validate_png(qa_dir / sheet_name, expected_size=(1632, 2390))

    taichung_groups = [
        item for item in published_manifest.get("qualified_groups", [])
        if item.get("city") == CITY
    ]
    checkpoint["status"] = "complete"
    checkpoint["finalized"] = True
    checkpoint["publication"] = {
        "published_at": args.date,
        "replacement_count": len(REPLACEMENTS),
        "qualified_all_day_count": len(taichung_all_day),
        "qualified_regular_group_count": len(taichung_groups),
        "non_taichung_manifest_sha256": untouched_after,
        "staged_equals_formal_sha256": hashes,
        "formal_sheet": f"qa/{sheet_name}",
        "rejected_evidence": str(rejected.relative_to(root)).replace("\\", "/"),
    }
    atomic_json(args.checkpoint, checkpoint)
    atomic_copy(args.checkpoint, qa_dir / "Taichung_weather_reqa_checkpoint.json")

    print(json.dumps({
        "status": "complete",
        "published_replacements": len(REPLACEMENTS),
        "taichung_qualified_all_day": len(taichung_all_day),
        "taichung_qualified_groups": len(taichung_groups),
        "non_taichung_manifest_sha256": untouched_after,
        "formal_sheet": str(qa_dir / sheet_name),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
