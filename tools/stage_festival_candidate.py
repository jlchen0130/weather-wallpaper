from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from audit_festival_assets import (
    EXPECTED_SIZE, FESTIVALS, PERIODS, REGULAR_WEATHERS, all_day_weathers,
    full_screen_gpt_size,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def eligible_names(city: str, festival: str) -> set[str]:
    prefix = f"{festival}_{city}_person_"
    regular = {
        f"{prefix}{period}_{weather}.png"
        for period in PERIODS for weather in REGULAR_WEATHERS
    }
    return regular | {
        f"{prefix}all_day_{weather}.png"
        for weather in all_day_weathers(city, festival)
    }


def preview_native_mae(preview: Path, pixels: Image.Image) -> float:
    with Image.open(preview) as image:
        image.load()
        if image.format not in {"PNG", "JPEG"} or min(image.size) < 300:
            raise ValueError("Preview must be a full portrait image crop")
        native_ratio = pixels.width / pixels.height
        preview_ratio = image.width / image.height
        if abs(native_ratio - preview_ratio) > 0.01:
            raise ValueError("Preview crop does not match the native image aspect ratio")
        scaled = pixels.resize(image.size, Image.Resampling.LANCZOS)
        difference = ImageChops.difference(image.convert("RGB"), scaled)
        return sum(ImageStat.Stat(difference).mean) / 3


def stage(source: Path, preview: Path, filename: str, staging: Path, qa: str,
          gemini_url: str, attempt_id: str, native_qa: str = "") -> dict:
    if Path(filename).name != filename or not filename.endswith(".png"):
        raise ValueError("Filename must be a plain PNG basename")
    parts = filename.split("_person_", 1)
    if len(parts) != 2:
        raise ValueError("Invalid festival filename")
    festival, city = parts[0].rsplit("_", 1)
    if festival not in FESTIVALS or filename not in eligible_names(city, festival):
        raise ValueError("Filename is outside the verified festival matrix")
    if not qa.strip() or not preview.is_file() or not gemini_url.startswith("https://gemini.google.com/app/"):
        raise ValueError("Preview, QA rationale, and Gemini URL are required")

    with Image.open(source) as image:
        image.load()
        if image.format != "JPEG" or image.size != EXPECTED_SIZE:
            raise ValueError("Source is not a native 1536x2752 JPEG")
        pixels = image.convert("RGB")
    native_preview_mae = preview_native_mae(preview, pixels)
    if native_preview_mae > 20 and not native_qa.strip():
        raise ValueError(
            f"Native JPEG differs from the QA-passed preview (MAE {native_preview_mae:.2f}); "
            "independent native visual QA is required"
        )

    staging.mkdir(parents=True, exist_ok=True)
    png = staging / filename
    native = staging / "sources" / f"{Path(filename).stem}.jpg"
    record_path = staging / "qa" / f"{Path(filename).stem}.json"
    if any(path.exists() for path in (png, native, record_path)):
        raise FileExistsError("Candidate already staged; refusing overwrite")
    native.parent.mkdir(parents=True, exist_ok=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(dir=staging, suffix=".png", delete=False) as temporary:
        temp_png = Path(temporary.name)
    try:
        pixels.save(temp_png, format="PNG")
        with Image.open(temp_png) as output:
            output.load()
            if output.format != "PNG" or output.size != EXPECTED_SIZE:
                raise ValueError("Staged PNG failed format or size validation")
            if ImageChops.difference(pixels, output.convert("RGB")).getbbox():
                raise ValueError("Staged PNG pixels differ from source")
        shutil.copyfile(source, native)
        record = {
            "filename": filename,
            "city": city,
            "festival": festival,
            "attempt_id": attempt_id,
            "source_method": "Gemini web native JPEG, converted to PNG without resize",
            "gemini_url": gemini_url,
            "source_file": str(native.relative_to(staging)),
            "source_sha256": sha256(native),
            "png_sha256": sha256(temp_png),
            "source_pixel_equality": True,
            "native_preview_mean_absolute_error": round(native_preview_mae, 2),
            "native_preview_variation_accepted": native_preview_mae > 20,
            "independent_native_visual_qa": native_qa.strip() or None,
            "size": list(EXPECTED_SIZE),
            "qa": qa.strip(),
            "preview_file": str(preview),
            "status": "staged_individual_qa_passed_not_batch_qualified",
        }
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=record_path.parent,
                                     suffix=".json", delete=False) as temporary:
            json.dump(record, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temp_record = Path(temporary.name)
        os.replace(temp_png, png)
        os.replace(temp_record, record_path)
        return record
    finally:
        if temp_png.exists():
            temp_png.unlink()


def stage_gpt(source: Path, filename: str, staging: Path, qa: str, attempt_id: str) -> dict:
    if Path(filename).name != filename or not filename.endswith(".png"):
        raise ValueError("Filename must be a plain PNG basename")
    parts = filename.split("_person_", 1)
    if len(parts) != 2:
        raise ValueError("Invalid festival filename")
    festival, city = parts[0].rsplit("_", 1)
    if festival not in FESTIVALS or filename not in eligible_names(city, festival):
        raise ValueError("Filename is outside the verified festival matrix")
    if not qa.strip() or not attempt_id.strip():
        raise ValueError("QA rationale and attempt ID are required")
    with Image.open(source) as image:
        image.load()
        if image.format != "PNG" or not full_screen_gpt_size(image.size):
            raise ValueError("GPT source must be a native full-screen portrait PNG")
        size = image.size

    destination = staging / filename
    native = staging / "sources" / filename
    record_path = staging / "qa" / f"{Path(filename).stem}.json"
    if any(path.exists() for path in (destination, native, record_path)):
        raise FileExistsError("Candidate already staged; refusing overwrite")
    native.parent.mkdir(parents=True, exist_ok=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=staging, suffix=".png", delete=False) as temporary:
        temp_png = Path(temporary.name)
    try:
        shutil.copyfile(source, temp_png)
        if sha256(source) != sha256(temp_png):
            raise ValueError("Staged PNG differs from GPT native source")
        record = {
            "filename": filename, "city": city, "festival": festival,
            "attempt_id": attempt_id,
            "source_method": "OpenAI built-in image generation",
            "source_file": str(native.relative_to(staging)),
            "source_sha256": sha256(source), "png_sha256": sha256(temp_png),
            "native_source_size": list(size), "size": list(size), "no_resize": True,
            "qa": qa.strip(), "status": "staged_individual_qa_passed_not_batch_qualified",
        }
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=record_path.parent,
                                     suffix=".json", delete=False) as temporary:
            json.dump(record, temporary, ensure_ascii=False, indent=2)
            temporary.write("\n")
            temp_record = Path(temporary.name)
        shutil.copyfile(source, native)
        os.replace(temp_png, destination)
        os.replace(temp_record, record_path)
        return record
    finally:
        if temp_png.exists():
            temp_png.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("preview", type=Path)
    parser.add_argument("filename")
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--qa", required=True)
    parser.add_argument("--gemini-url", default="")
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--native-qa", default="", help="Independent full-size visual QA when Gemini's native rendering differs from its preview")
    parser.add_argument("--gpt-native", action="store_true", help="Stage an unresized, full-screen built-in GPT PNG")
    args = parser.parse_args()
    if args.gpt_native:
        record = stage_gpt(args.source, args.filename, args.staging, args.qa, args.attempt_id)
    else:
        record = stage(args.source, args.preview, args.filename, args.staging,
                       args.qa, args.gemini_url, args.attempt_id, args.native_qa)
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
