"""Fail-closed Tainan base-weather re-QA and publication workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image

from build_all_day_contact_sheet import build_sheet as build_all_day_sheet


CITY = "Tainan"
SIZE = (1536, 2752)
ALL_DAY = (
    "cloudy", "overcast", "light_rain", "heavy_rain", "typhoon", "fog",
    "haze", "strong_wind", "thunder_shower", "thunderstorm", "heatwave",
    "cold_wave",
)
REPLACEMENTS = ALL_DAY[3:]
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
REGULAR = ("sunny", "partly_cloudy")
SCOPE = "Tainan base weather assets only; festivals forbidden"
CRITERIA = (
    "Every person and every animal is inside the same fully enclosed room behind "
    "closed glass; all outdoor roads, plazas, paths, waterfronts, roofs, arcades, "
    "balconies and landmark foregrounds contain no people, animals, vehicles, "
    "bicycles, vendors, flags or silhouettes; long-shot composition is at least "
    "75 percent scenery with multiple Tainan landmarks, multiple people, 2-4 "
    "natural safe animals, and fine natural matte needle-felt texture."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, path)


def atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    shutil.copy2(source, temporary)
    os.replace(temporary, destination)


def validate_png(path: Path, size: tuple[int, int] = SIZE) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != size:
            raise ValueError(f"Invalid PNG {path}: {image.format} {image.size}")


def manifest_scope(manifest: dict[str, object], include_tainan: bool) -> dict[str, object]:
    result: dict[str, object] = {}
    for key in ("qualified_groups", "qualified_all_day", "failed_batches"):
        rows = manifest.get(key, [])
        result[key] = [
            row for row in rows
            if (row.get("city") == CITY) == include_tainan
        ]
    return result


def paths(root: Path) -> dict[str, Path]:
    qa = root / "qa"
    return {
        "qa": qa,
        "stage": qa / "staging" / "Tainan_2026-10-19_closed_glass",
        "sources": qa / "sources" / "Tainan_2026-10-19_closed_glass",
        "rejected": qa / "rejected" / "Tainan_2026-10-19_closed_glass",
        "checkpoint": qa / "Tainan_weather_reqa_checkpoint.json",
        "manifest": qa / "qualified_assets.json",
    }


def read_checkpoint(root: Path) -> tuple[dict[str, object], dict[str, Path]]:
    p = paths(root)
    checkpoint = json.loads(p["checkpoint"].read_text(encoding="utf-8"))
    if checkpoint.get("scope") != SCOPE:
        raise ValueError("Checkpoint is not scoped to Tainan base weather")
    return checkpoint, p


def init(root: Path) -> None:
    p = paths(root)
    if p["checkpoint"].exists():
        checkpoint, _ = read_checkpoint(root)
        print(json.dumps(checkpoint, ensure_ascii=False, indent=2))
        return

    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))
    files: dict[str, str] = {}
    master = root / "master" / "none_Tainan_person_master.png"
    validate_png(master)
    files[str(master.relative_to(root)).replace("\\", "/")] = sha256(master)
    for weather in REGULAR:
        for period in PERIODS:
            asset = root / f"none_Tainan_person_{period}_{weather}.png"
            validate_png(asset)
            files[asset.name] = sha256(asset)
        sheet = p["qa"] / f"Tainan_{weather}_6grid.png"
        validate_png(sheet, (1620, 2074))
        files[f"qa/{sheet.name}"] = sha256(sheet)
    for weather in ALL_DAY:
        asset = root / f"none_Tainan_person_all_day_{weather}.png"
        validate_png(asset)
        files[asset.name] = sha256(asset)
        if weather in ALL_DAY[:3]:
            atomic_copy(asset, p["stage"] / asset.name)
        else:
            atomic_copy(asset, p["rejected"] / asset.name)

    checkpoint = {
        "city": CITY,
        "scope": SCOPE,
        "created_at": "2026-10-19",
        "status": "in_progress",
        "finalized": False,
        "matrix": {
            "regular": {weather: list(PERIODS) for weather in REGULAR},
            "all_day": list(ALL_DAY),
            "forbidden": ["torrential_rain"],
        },
        "permanent_pass": [
            *[f"none_Tainan_person_{period}_{weather}.png" for weather in REGULAR for period in PERIODS],
            *[f"none_Tainan_person_all_day_{weather}.png" for weather in ALL_DAY[:3]],
        ],
        "failed_quarantined": {
            weather: (
                "People and animals are split across different rooms/buildings"
                if weather in {"heavy_rain", "typhoon", "fog", "haze"}
                else "People, animals and/or bicycles are present outdoors"
            )
            for weather in REPLACEMENTS
        },
        "accepted_replacements": {},
        "rejected_candidates": [],
        "reviewed_sheets": {},
        "baseline_tainan_sha256": files,
        "baseline_non_tainan_manifest_sha256": canonical_hash(
            manifest_scope(manifest, include_tainan=False)
        ),
        "criteria": CRITERIA,
    }
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({
        "status": checkpoint["status"],
        "permanent_pass": len(checkpoint["permanent_pass"]),
        "replacement_gap": list(REPLACEMENTS),
        "checkpoint": str(p["checkpoint"]),
    }, ensure_ascii=False, indent=2))


def ingest(root: Path, source: Path, weather: str, note: str, prompt: str) -> None:
    checkpoint, p = read_checkpoint(root)
    if weather not in REPLACEMENTS:
        raise ValueError(f"Not an allowed replacement weather: {weather}")
    accepted = checkpoint["accepted_replacements"]
    if weather in accepted:
        raise FileExistsError(f"Replacement already accepted permanently: {weather}")
    with Image.open(source) as image:
        image.load()
        if image.format != "JPEG" or image.size != SIZE:
            raise ValueError(f"Expected native JPEG {SIZE}, got {image.format} {image.size}")
        pixels = image.convert("RGB").tobytes()
        output = p["stage"] / f"none_Tainan_person_all_day_{weather}.png"
        temporary = output.with_name(output.name + ".tmp")
        output.parent.mkdir(parents=True, exist_ok=True)
        image.convert("RGB").save(temporary, "PNG", optimize=True)
    validate_png(temporary)
    with Image.open(temporary) as converted:
        converted.load()
        if converted.tobytes() != pixels:
            temporary.unlink(missing_ok=True)
            raise RuntimeError("Source/output pixel mismatch")
    os.replace(temporary, output)
    original = p["sources"] / f"{weather}{source.suffix.lower()}"
    if original.exists():
        raise FileExistsError(original)
    atomic_copy(source, original)
    accepted[weather] = {
        "asset_file": output.name,
        "source_file": str(original.relative_to(root)).replace("\\", "/"),
        "source_sha256": sha256(original),
        "png_sha256": sha256(output),
        "source_pixel_equality": True,
        "download_count": 1,
        "visual_qa": "passed",
        "review_note": note,
        "prompt": prompt,
    }
    checkpoint["status"] = (
        "ready_for_sheet" if set(accepted) == set(REPLACEMENTS) else "in_progress"
    )
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"accepted": weather, "status": checkpoint["status"]}, ensure_ascii=False))


def reject(root: Path, source: Path, weather: str, reason: str) -> None:
    checkpoint, p = read_checkpoint(root)
    if weather not in REPLACEMENTS:
        raise ValueError(weather)
    with Image.open(source) as image:
        image.load()
        if image.size != SIZE or image.format != "JPEG":
            raise ValueError(f"Rejected candidate is not native JPEG {SIZE}")
    attempts = list(p["rejected"].glob(f"candidate_{weather}_attempt*{source.suffix.lower()}"))
    target = p["rejected"] / f"candidate_{weather}_attempt{len(attempts) + 1}{source.suffix.lower()}"
    atomic_copy(source, target)
    checkpoint["rejected_candidates"].append({
        "weather": weather,
        "file": str(target.relative_to(root)).replace("\\", "/"),
        "sha256": sha256(target),
        "reason": reason,
    })
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"rejected": weather, "file": str(target)}, ensure_ascii=False))


def preview_reject(root: Path, weather: str, reason: str) -> None:
    checkpoint, p = read_checkpoint(root)
    if weather not in REPLACEMENTS:
        raise ValueError(weather)
    checkpoint["rejected_candidates"].append({
        "weather": weather,
        "file": None,
        "download_count": 0,
        "reason": reason,
    })
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"preview_rejected": weather}, ensure_ascii=False))


def sheets(root: Path) -> None:
    checkpoint, p = read_checkpoint(root)
    if set(checkpoint["accepted_replacements"]) != set(REPLACEMENTS):
        raise ValueError("All nine replacements must be accepted before building the sheet")
    output = p["stage"] / "Tainan_all_day_12grid.png"
    build_all_day_sheet(p["stage"], CITY, output)
    checkpoint["status"] = "sheet_pending_review"
    checkpoint["sheet_sha256"] = sha256(output)
    atomic_json(p["checkpoint"], checkpoint)
    print(output)


def review_sheet(root: Path, note: str) -> None:
    checkpoint, p = read_checkpoint(root)
    sheet = p["stage"] / "Tainan_all_day_12grid.png"
    validate_png(sheet, (1632, 2390))
    if checkpoint.get("sheet_sha256") != sha256(sheet):
        raise ValueError("Sheet changed after construction")
    checkpoint["reviewed_sheets"] = {
        "Tainan_all_day_12grid.png": {
            "sha256": sha256(sheet), "visual_qa": "passed", "note": note
        }
    }
    checkpoint["status"] = "ready_to_publish"
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"status": checkpoint["status"]}, ensure_ascii=False))


def publish(root: Path) -> None:
    checkpoint, p = read_checkpoint(root)
    if checkpoint.get("status") != "ready_to_publish":
        raise ValueError(f"Not ready to publish: {checkpoint.get('status')}")
    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))
    non_tainan_before = canonical_hash(manifest_scope(manifest, include_tainan=False))
    if non_tainan_before != checkpoint["baseline_non_tainan_manifest_sha256"]:
        raise ValueError("Non-Tainan manifest changed since checkpoint creation")
    for rel, expected in checkpoint["baseline_tainan_sha256"].items():
        if rel.startswith("none_Tainan_person_all_day_") and any(
            rel.endswith(f"_{weather}.png") for weather in REPLACEMENTS
        ):
            continue
        if sha256(root / rel) != expected:
            raise ValueError(f"Permanent-pass Tainan file changed: {rel}")
    for weather, record in checkpoint["accepted_replacements"].items():
        stage = p["stage"] / record["asset_file"]
        source = root / record["source_file"]
        validate_png(stage)
        if sha256(stage) != record["png_sha256"] or sha256(source) != record["source_sha256"]:
            raise ValueError(f"Changed accepted replacement: {weather}")
        with Image.open(source) as original, Image.open(stage) as converted:
            original.load(); converted.load()
            if original.convert("RGB").tobytes() != converted.tobytes():
                raise ValueError(f"Source/output pixel mismatch: {weather}")
    sheet = p["stage"] / "Tainan_all_day_12grid.png"
    validate_png(sheet, (1632, 2390))
    review = checkpoint["reviewed_sheets"].get(sheet.name, {})
    if review.get("visual_qa") != "passed" or review.get("sha256") != sha256(sheet):
        raise ValueError("All-day sheet is unreviewed or changed")

    rows = [row for row in manifest.get("qualified_all_day", []) if not (
        row.get("city") == CITY and row.get("weather") in REPLACEMENTS
    )]
    for weather in REPLACEMENTS:
        record = checkpoint["accepted_replacements"][weather]
        rows.append({
            "city": CITY, "style": "knitted", "character": "person",
            "weather": weather,
            "asset_file": f"none_Tainan_person_all_day_{weather}.png",
            "master_file": "master/none_Tainan_person_master.png",
            "qa_file": "Tainan_all_day_12grid.png",
            "qualified_at": "2026-10-19",
            "source_method": "native Gemini 1536x2752 JPEG decoded to RGB PNG without resizing or overlays",
            "source_file": record["source_file"],
            "source_pixel_equality": True,
            "visual_qa": "passed",
            "criteria": CRITERIA,
        })
    manifest["qualified_all_day"] = rows
    tainan_all_day = [row for row in rows if row.get("city") == CITY]
    if len(tainan_all_day) != 12 or {row.get("weather") for row in tainan_all_day} != set(ALL_DAY):
        raise ValueError("Tainan all-day manifest is not the exact 12-weather matrix")
    groups = [row for row in manifest.get("qualified_groups", []) if row.get("city") == CITY]
    if len(groups) != 2 or {row.get("weather") for row in groups} != set(REGULAR):
        raise ValueError("Tainan regular qualification groups changed")

    for weather in REPLACEMENTS:
        atomic_copy(
            p["stage"] / f"none_Tainan_person_all_day_{weather}.png",
            root / f"none_Tainan_person_all_day_{weather}.png",
        )
    atomic_copy(sheet, p["qa"] / sheet.name)
    atomic_json(p["manifest"], manifest)
    if canonical_hash(manifest_scope(manifest, include_tainan=False)) != non_tainan_before:
        raise AssertionError("Non-Tainan manifest changed during publication")
    checkpoint["status"] = "complete"
    checkpoint["finalized"] = True
    checkpoint["publication"] = {
        "published_at": "2026-10-19",
        "replacement_count": len(REPLACEMENTS),
        "qualified_all_day_count": len(tainan_all_day),
        "qualified_regular_group_count": len(groups),
        "non_tainan_manifest_sha256": non_tainan_before,
        "formal_sheet": "qa/Tainan_all_day_12grid.png",
    }
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps(checkpoint["publication"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init")
    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument("source", type=Path)
    ingest_parser.add_argument("weather", choices=REPLACEMENTS)
    ingest_parser.add_argument("--note", required=True)
    ingest_parser.add_argument("--prompt", required=True)
    reject_parser = sub.add_parser("reject")
    reject_parser.add_argument("source", type=Path)
    reject_parser.add_argument("weather", choices=REPLACEMENTS)
    reject_parser.add_argument("--reason", required=True)
    preview_reject_parser = sub.add_parser("preview-reject")
    preview_reject_parser.add_argument("weather", choices=REPLACEMENTS)
    preview_reject_parser.add_argument("--reason", required=True)
    sub.add_parser("sheets")
    review_parser = sub.add_parser("review-sheet")
    review_parser.add_argument("--note", required=True)
    sub.add_parser("publish")
    sub.add_parser("status")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "init": init(root)
    elif args.action == "ingest": ingest(root, args.source.resolve(), args.weather, args.note, args.prompt)
    elif args.action == "reject": reject(root, args.source.resolve(), args.weather, args.reason)
    elif args.action == "preview-reject": preview_reject(root, args.weather, args.reason)
    elif args.action == "sheets": sheets(root)
    elif args.action == "review-sheet": review_sheet(root, args.note)
    elif args.action == "publish": publish(root)
    else:
        checkpoint, _ = read_checkpoint(root)
        print(json.dumps(checkpoint, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
