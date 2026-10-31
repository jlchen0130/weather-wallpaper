from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageChops

from audit_taipei_festival_assets import PERIODS, all_day_weathers


def record(args: argparse.Namespace) -> None:
    checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    festival = checkpoint["current_festival"]
    prefix = f"{festival}_Taipei_person_"
    eligible = {f"{prefix}{p}_{w}.png" for p in PERIODS for w in ("sunny", "partly_cloudy")}
    eligible.update(f"{prefix}all_day_{w}.png" for w in all_day_weathers(festival))
    if checkpoint["city"] != "Taipei" or checkpoint.get("paused"):
        raise ValueError("Checkpoint must be active and exact Taipei")
    if args.filename not in eligible or (args.next and args.next not in eligible):
        raise ValueError("Filename is outside the historically eligible current festival matrix")
    if any(r["filename"] == args.filename for r in checkpoint["accepted_individually"]):
        raise ValueError("Already accepted; refusing duplicate or overwrite")
    published = Path(checkpoint["asset_root"]) / args.filename
    with Image.open(args.source) as source, Image.open(published) as output:
        if source.format not in {"JPEG", "PNG"} or source.size != (1536, 2752):
            raise ValueError("Source is not a native original-size image")
        if output.format != "PNG" or output.size != source.size:
            raise ValueError("Published PNG is invalid")
        if ImageChops.difference(source.convert("RGB"), output.convert("RGB")).getbbox():
            raise ValueError("Source/published pixels differ")
        extension = ".jpg" if source.format == "JPEG" else ".png"
    native = args.checkpoint.parent / checkpoint["native_sources_directory"] / (Path(args.filename).stem + extension)
    if native.exists() and native.read_bytes() != args.source.read_bytes():
        raise FileExistsError("Native source already exists with different bytes")
    item = {"filename": args.filename, "source_cache": args.source.name,
            "source_file": native.name, "size": [1536, 2752], "qa": args.qa,
            "download_count": 1, "source_pixel_equality": True,
            "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest()}
    if args.dry_run:
        print("Verified without writes: " + args.filename)
        return
    if not native.exists():
        shutil.copyfile(args.source, native)
    checkpoint["accepted_individually"].append(item)
    checkpoint["pending_generation"] = args.next
    checkpoint["new_run_consecutive_major_failures"] = 0
    if args.conversation:
        checkpoint["gemini_conversation"] = args.conversation
    temporary = args.checkpoint.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.checkpoint)
    assert json.loads(args.checkpoint.read_text(encoding="utf-8")) == checkpoint
    print("Recorded eligible native candidate with pixel equality: " + args.filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("filename")
    parser.add_argument("--checkpoint", type=Path, default=Path("taipei_festival_checkpoint.json"))
    parser.add_argument("--qa", required=True)
    parser.add_argument("--next")
    parser.add_argument("--conversation")
    parser.add_argument("--dry-run", action="store_true")
    record(parser.parse_args())
