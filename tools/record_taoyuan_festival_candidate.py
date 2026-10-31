from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageChops

from audit_taoyuan_festival_assets import CITY, EXPECTED_SIZE, PERIODS, all_day_weathers


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible_names(festival: str) -> set[str]:
    prefix = f"{festival}_{CITY}_person_"
    names = {
        f"{prefix}{period}_{weather}.png"
        for period in PERIODS
        for weather in ("sunny", "partly_cloudy")
    }
    names.update(f"{prefix}all_day_{weather}.png" for weather in all_day_weathers(festival))
    return names


def record(args: argparse.Namespace) -> None:
    checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    festival = checkpoint["current_festival"]
    if checkpoint.get("city") != CITY:
        raise ValueError(f"Checkpoint must be exact {CITY}")
    if args.filename not in eligible_names(festival):
        raise ValueError("Filename is outside the eligible current-festival matrix")
    if Path(args.filename).name != args.filename:
        raise ValueError("Filename must not contain a path")
    if any(item["filename"] == args.filename for item in checkpoint["accepted_individually"]):
        raise ValueError("Already accepted; refusing duplicate")

    png = args.staging / args.filename
    if not png.is_file() or not args.source.is_file():
        raise FileNotFoundError("Source or staged PNG is missing")
    with Image.open(args.source) as source, Image.open(png) as output:
        source.load()
        output.load()
        if source.format not in {"JPEG", "PNG"} or source.size != EXPECTED_SIZE:
            raise ValueError("Source is not a native original-size image")
        if output.format != "PNG" or output.size != EXPECTED_SIZE:
            raise ValueError("Staged PNG is invalid")
        if ImageChops.difference(source.convert("RGB"), output.convert("RGB")).getbbox():
            raise ValueError("Source and staged PNG pixels differ")
        extension = ".jpg" if source.format == "JPEG" else ".png"

    native_dir = args.checkpoint.parent / checkpoint["native_sources_directory"]
    native = native_dir / (Path(args.filename).stem + extension)
    if native.exists() and native.read_bytes() != args.source.read_bytes():
        raise FileExistsError("Native source already exists with different bytes")

    item = {
        "filename": args.filename,
        "source_file": native.name,
        "source_sha256": sha256(args.source),
        "png_sha256": sha256(png),
        "source_pixel_equality": True,
        "size": list(EXPECTED_SIZE),
        "qa": args.qa,
    }
    if args.dry_run:
        print(json.dumps(item, indent=2))
        return

    native_dir.mkdir(parents=True, exist_ok=True)
    if not native.exists():
        shutil.copyfile(args.source, native)
    checkpoint["accepted_individually"].append(item)
    checkpoint["status"] = args.next_status
    temporary = args.checkpoint.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.checkpoint)
    if json.loads(args.checkpoint.read_text(encoding="utf-8")) != checkpoint:
        raise RuntimeError("Checkpoint readback differs after atomic write")
    print(json.dumps(item, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("filename")
    parser.add_argument("--checkpoint", type=Path, default=Path("taoyuan_festival_checkpoint.json"))
    parser.add_argument("--staging", type=Path, default=Path("taoyuan_festival_staging"))
    parser.add_argument("--qa", required=True)
    parser.add_argument("--next-status", required=True)
    parser.add_argument("--dry-run", action="store_true")
    record(parser.parse_args())
