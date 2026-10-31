from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from PIL import Image, ImageChops

from audit_taipei_festival_assets import FESTIVALS, PERIODS, all_day_weathers, audit_festival


def qualify(checkpoint_path: Path) -> None:
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    festival = checkpoint["current_festival"]
    if checkpoint["city"] != "Taipei" or festival not in FESTIVALS:
        raise ValueError("Only exact Taipei festival checkpoints are supported")
    root = Path(checkpoint["asset_root"])
    expected_all_day = all_day_weathers(festival)
    if not audit_festival(root, festival)["complete"]:
        raise ValueError("Festival matrix or contact sheets incomplete")
    sheets = [f"qa/{festival}_Taipei_{kind}.png" for kind in (
        "sunny_6grid", "partly_cloudy_6grid", f"all_day_{len(expected_all_day)}grid"
    )]
    if not set(sheets).issubset(checkpoint["reviewed_contact_sheets"]):
        raise ValueError("Visual review of all three sheets must be recorded first")
    prefix = f"{festival}_Taipei_person_"
    accepted = {r["filename"]: r for r in checkpoint["accepted_individually"]
                if r["filename"].startswith(prefix)}
    expected = {f"{prefix}{p}_{w}.png" for p in PERIODS for w in ("sunny", "partly_cloudy")}
    expected.update(f"{prefix}all_day_{w}.png" for w in expected_all_day)
    if set(accepted) != expected:
        raise ValueError(
            "Accepted assets must exactly match the historically eligible festival matrix"
        )
    source_dir = checkpoint_path.parent / checkpoint["native_sources_directory"]
    provenance = []
    for name in sorted(expected):
        record = accepted[name]
        source = source_dir / record.get("source_file", name.replace(".png", ".jpg"))
        published = root / name
        with Image.open(source) as original, Image.open(published) as output:
            original.load()
            output.load()
            if original.size != (1536, 2752) or output.size != original.size:
                raise ValueError(f"Native dimensions failed: {name}")
            if ImageChops.difference(original.convert("RGB"), output.convert("RGB")).getbbox():
                raise ValueError(f"Source pixel equality failed: {name}")
        provenance.append({**record, "source_file": str(source.resolve()),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "png_sha256": hashlib.sha256(published.read_bytes()).hexdigest(),
            "source_pixel_equality": True})
    manifest_path = root / "qa/qualified_assets.json"
    original_text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(original_text)
    before = json.loads(original_text)
    for key in ("qualified_groups", "qualified_all_day"):
        if any(r.get("city") == "Taipei" and r.get("festival") == festival
               for r in manifest[key]):
            raise ValueError("Festival already qualified; refusing duplicate or overwrite")
    qa_record = f"{festival}_Taipei_provenance_and_visual_qa.json"
    common = {"city": "Taipei", "festival": festival, "style": "knitted",
        "character": "person", "qualified_at": date.today().isoformat(),
        "source_method": "Gemini web original native 1536x2752; decoded to PNG without resizing or overlays",
        "visual_qa_record": qa_record,
        "criteria": "Individual major-error review and all three contact sheets passed; native source pixel equality verified. Base assets unchanged."}
    for weather in ("sunny", "partly_cloudy"):
        manifest["qualified_groups"].append({**common, "weather": weather,
            "periods": list(PERIODS), "qa_file": f"{festival}_Taipei_{weather}_6grid.png"})
    for weather in expected_all_day:
        name = f"{prefix}all_day_{weather}.png"
        manifest["qualified_all_day"].append({**common, "weather": weather,
            "asset_file": name, "qa_file": f"{festival}_Taipei_all_day_{len(expected_all_day)}grid.png",
            "criteria": accepted[name]["qa"] + "; full all-day sheet reviewed; native source equality passed"})
    for key, rows in before.items():
        if manifest[key][:len(rows)] != rows:
            raise AssertionError("Existing qualification records changed")
    backup = manifest_path.with_name(f"qualified_assets.before_{festival}_Taipei.json")
    if not backup.exists():
        backup.write_text(original_text, encoding="utf-8")
    (root / "qa" / qa_record).write_text(json.dumps({"city": "Taipei",
        "festival": festival, "assets": provenance, "reviewed_sheets": sheets}, indent=2), encoding="utf-8")
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    reloaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if reloaded != manifest:
        raise AssertionError("Manifest readback failed")
    print(
        f"Qualified {festival}: {len(expected)} historically eligible sources, "
        f"3 reviewed sheets, {2 + len(expected_all_day)} appended records; "
        "existing records unchanged"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("checkpoint", type=Path)
    qualify(parser.parse_args().checkpoint.resolve())
