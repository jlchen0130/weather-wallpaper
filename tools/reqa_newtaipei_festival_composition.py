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
    FESTIVALS,
    PERIODS,
    REGULAR_WEATHERS,
    all_day_weathers,
    audit_festival,
)
from build_newtaipei_festival_contact_sheets import (
    build_all_day_sheet,
    build_regular_sheet,
)


ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
MANIFEST = ROOT / "qa" / "qualified_assets.json"
BACKUP = ROOT / "qa" / "qualified_assets.before_NewTaipei_festival_composition_reqa_20261016.json"
REJECTED = ROOT / "qa" / "rejected" / "NewTaipei_festival_composition_reqa_2026-10-16"
SOURCE_DIR = Path(__file__).resolve().parent.parent / "newtaipei_festival_sources"
CHECKPOINT = Path(__file__).resolve().parent.parent / "newtaipei_festival_composition_reqa_checkpoint.json"
EXPECTED_SIZE = (1536, 2752)
RULE = (
    "2026-10-16 single-pass composition QA: distant long shot; scenery about 75% or more; "
    "multiple representative NewTaipei landmarks; multiple people; 2-4 clearly recognizable "
    "animals; festival clothing/activity/decor correct; adverse-weather people and animals all "
    "inside one enclosed room behind closed glass, with zero outdoor people, humanoids, animals, "
    "bicycles, vehicles, vendors, or silhouettes"
)


def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_assets() -> list[dict[str, str]]:
    assets: list[dict[str, str]] = []
    for festival in FESTIVALS:
        for weather in REGULAR_WEATHERS:
            for period in PERIODS:
                assets.append(
                    {
                        "festival": festival,
                        "period": period,
                        "weather": weather,
                        "filename": f"{festival}_{CITY}_person_{period}_{weather}.png",
                    }
                )
        for weather in all_day_weathers(festival):
            assets.append(
                {
                    "festival": festival,
                    "period": "all_day",
                    "weather": weather,
                    "filename": f"{festival}_{CITY}_person_all_day_{weather}.png",
                }
            )
    return assets


def validate_png(path: Path) -> None:
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.size != EXPECTED_SIZE:
            raise ValueError(f"Invalid native PNG: {path}: {image.format} {image.size}")


def load_checkpoint() -> dict[str, object]:
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    if checkpoint.get("city") != CITY or checkpoint.get("rule") != RULE:
        raise ValueError("Checkpoint scope or rule mismatch")
    return checkpoint


def initialize() -> None:
    if CHECKPOINT.exists():
        raise FileExistsError(f"Checkpoint already exists: {CHECKPOINT}")
    if BACKUP.exists() or REJECTED.exists():
        raise FileExistsError("NewTaipei re-QA backup or rejected batch already exists")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    inventory = []
    for item in expected_assets():
        asset = ROOT / item["filename"]
        source = SOURCE_DIR / item["filename"]
        validate_png(asset)
        validate_png(source)
        inventory.append(
            item
            | {
                "asset_sha256_before": sha256(asset),
                "source_sha256_before": sha256(source),
                "status": "pending",
            }
        )
    if len(inventory) != 84 or len({item["filename"] for item in inventory}) != 84:
        raise ValueError("Expected exactly 84 unique NewTaipei festival assets")

    shutil.copy2(MANIFEST, BACKUP)
    if json.loads(BACKUP.read_text(encoding="utf-8")) != manifest:
        raise AssertionError("Manifest backup verification failed")
    (REJECTED / "assets").mkdir(parents=True)
    (REJECTED / "sources").mkdir()
    batch_record = {
        "city": CITY,
        "status": "composition_reqa_in_progress",
        "qa_record": str((REJECTED / "failed_visual_qa.json").relative_to(ROOT)).replace("\\", "/"),
        "reason": RULE,
        "rejected_count": 0,
    }
    manifest.setdefault("failed_batches", []).append(batch_record)
    write_json_atomic(MANIFEST, manifest)
    checkpoint = {
        "city": CITY,
        "date": date.today().isoformat(),
        "rule": RULE,
        "manifest_backup": str(BACKUP),
        "rejected_batch": str(REJECTED),
        "assets": inventory,
        "reviewed_count": 0,
        "passed_count": 0,
        "failed_count": 0,
        "affected_contact_sheets": [],
        "finalized": False,
    }
    write_json_atomic(CHECKPOINT, checkpoint)
    write_json_atomic(
        REJECTED / "failed_visual_qa.json",
        {"city": CITY, "rule": RULE, "records": []},
    )
    print(
        json.dumps(
            {
                "checkpoint": str(CHECKPOINT),
                "manifest_backup": str(BACKUP),
                "inventory": len(inventory),
            },
            indent=2,
        )
    )


def find_pending(checkpoint: dict[str, object], filename: str) -> dict[str, object]:
    matches = [item for item in checkpoint["assets"] if item["filename"] == filename]
    if len(matches) != 1:
        raise ValueError(f"Out-of-scope asset: {filename}")
    item = matches[0]
    if item["status"] != "pending":
        raise ValueError(f"Asset already reviewed and permanently skipped: {filename}")
    return item


def affected_sheet(item: dict[str, object]) -> str:
    if item["period"] == "all_day":
        count = len(all_day_weathers(str(item["festival"])))
        return f"{item['festival']}_{CITY}_all_day_{count}grid.png"
    return f"{item['festival']}_{CITY}_{item['weather']}_6grid.png"


def record_pass(filename: str, note: str) -> None:
    checkpoint = load_checkpoint()
    item = find_pending(checkpoint, filename)
    asset = ROOT / filename
    validate_png(asset)
    if sha256(asset) != item["asset_sha256_before"]:
        raise ValueError(f"Asset changed since checkpoint initialization: {filename}")
    item["status"] = "passed"
    item["qa_note"] = note
    item["reviewed_at"] = date.today().isoformat()
    checkpoint["reviewed_count"] += 1
    checkpoint["passed_count"] += 1
    write_json_atomic(CHECKPOINT, checkpoint)
    print(json.dumps({"passed": filename, "reviewed": checkpoint["reviewed_count"]}, indent=2))


def remove_manifest_qualification(
    manifest: dict[str, object], item: dict[str, object]
) -> list[dict[str, object]]:
    removed: list[dict[str, object]] = []
    kept: list[dict[str, object]] = []
    for record in manifest["qualified_groups"]:
        same_scope = (
            record.get("city") == CITY
            and record.get("festival") == item["festival"]
            and record.get("weather") == item["weather"]
        )
        if same_scope:
            removed.append(record)
        else:
            kept.append(record)
    manifest["qualified_groups"] = kept
    return removed


def record_fail(filename: str, reason: str) -> None:
    checkpoint = load_checkpoint()
    item = find_pending(checkpoint, filename)
    asset = ROOT / filename
    source = SOURCE_DIR / filename
    validate_png(asset)
    validate_png(source)
    if sha256(asset) != item["asset_sha256_before"] or sha256(source) != item["source_sha256_before"]:
        raise ValueError(f"Asset or source changed since checkpoint initialization: {filename}")

    rejected_asset = REJECTED / "assets" / filename
    rejected_source = REJECTED / "sources" / filename
    if rejected_asset.exists() or rejected_source.exists():
        raise FileExistsError(f"Rejected evidence already exists: {filename}")
    shutil.move(asset, rejected_asset)
    shutil.move(source, rejected_source)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    removed = remove_manifest_qualification(manifest, item)
    batches = [
        row
        for row in manifest.get("failed_batches", [])
        if row.get("city") == CITY and row.get("qa_record")
        == str((REJECTED / "failed_visual_qa.json").relative_to(ROOT)).replace("\\", "/")
    ]
    if len(batches) != 1:
        raise ValueError("Expected exactly one active NewTaipei re-QA batch")
    batches[0]["rejected_count"] += 1
    write_json_atomic(MANIFEST, manifest)

    failed_qa_path = REJECTED / "failed_visual_qa.json"
    failed_qa = json.loads(failed_qa_path.read_text(encoding="utf-8"))
    failed_qa["records"].append(
        {
            "filename": filename,
            "asset_sha256": item["asset_sha256_before"],
            "source_sha256": item["source_sha256_before"],
            "reason": reason,
            "manifest_records_removed": removed,
        }
    )
    write_json_atomic(failed_qa_path, failed_qa)

    item["status"] = "failed_quarantined"
    item["qa_note"] = reason
    item["reviewed_at"] = date.today().isoformat()
    checkpoint["reviewed_count"] += 1
    checkpoint["failed_count"] += 1
    sheets = set(checkpoint["affected_contact_sheets"])
    sheets.add(affected_sheet(item))
    checkpoint["affected_contact_sheets"] = sorted(sheets)
    write_json_atomic(CHECKPOINT, checkpoint)
    print(
        json.dumps(
            {
                "failed_quarantined": filename,
                "manifest_records_removed": len(removed),
                "reviewed": checkpoint["reviewed_count"],
            },
            indent=2,
        )
    )


def record_candidate_rejection(download: Path, filename: str, reason: str) -> None:
    checkpoint = load_checkpoint()
    matches = [item for item in checkpoint["assets"] if item["filename"] == filename]
    if len(matches) != 1 or matches[0]["status"] != "failed_quarantined":
        raise ValueError(f"Candidate is not for a quarantined scoped asset: {filename}")
    with Image.open(download) as image:
        image.load()
        if image.format not in {"JPEG", "PNG"}:
            raise ValueError(f"Unsupported candidate evidence: {image.format}")
        observed_size = list(image.size)
        observed_format = image.format
    candidates = REJECTED / "candidates"
    candidates.mkdir(exist_ok=True)
    attempt = 1 + len(list(candidates.glob(Path(filename).stem + "_attempt*.*")))
    extension = ".jpg" if observed_format == "JPEG" else ".png"
    target = candidates / f"{Path(filename).stem}_attempt{attempt}{extension}"
    shutil.copy2(download, target)
    rejection = {
        "filename": filename,
        "candidate_file": target.name,
        "candidate_sha256": sha256(target),
        "format": observed_format,
        "size": observed_size,
        "native_1536x2752": observed_size == list(EXPECTED_SIZE),
        "reason": reason,
    }
    checkpoint.setdefault("rejected_candidates", []).append(rejection)
    write_json_atomic(CHECKPOINT, checkpoint)
    failed_qa_path = REJECTED / "failed_visual_qa.json"
    failed_qa = json.loads(failed_qa_path.read_text(encoding="utf-8"))
    failed_qa.setdefault("replacement_candidate_rejections", []).append(rejection)
    write_json_atomic(failed_qa_path, failed_qa)
    print(json.dumps({"candidate_rejected": filename, "evidence": str(target)}, indent=2))


def record_candidate_failure(filename: str, reason: str) -> None:
    """Record a generation attempt that returned no downloadable image."""
    checkpoint = load_checkpoint()
    matches = [item for item in checkpoint["assets"] if item["filename"] == filename]
    if len(matches) != 1 or matches[0]["status"] != "failed_quarantined":
        raise ValueError(f"Candidate is not for a quarantined scoped asset: {filename}")
    failure = {
        "filename": filename,
        "candidate_file": None,
        "candidate_sha256": None,
        "format": None,
        "size": None,
        "native_1536x2752": False,
        "reason": reason,
    }
    checkpoint.setdefault("failed_candidate_attempts", []).append(failure)
    write_json_atomic(CHECKPOINT, checkpoint)
    failed_qa_path = REJECTED / "failed_visual_qa.json"
    failed_qa = json.loads(failed_qa_path.read_text(encoding="utf-8"))
    failed_qa.setdefault("replacement_candidate_failures", []).append(failure)
    write_json_atomic(failed_qa_path, failed_qa)
    print(json.dumps({"candidate_failed": filename, "reason": reason}, indent=2))


def source_map_key(item: dict[str, object]) -> str:
    return f"{item['period']}_{item['weather']}"


def accept_candidate(download: Path, filename: str, note: str) -> None:
    checkpoint = load_checkpoint()
    matches = [item for item in checkpoint["assets"] if item["filename"] == filename]
    if len(matches) != 1 or matches[0]["status"] != "failed_quarantined":
        raise ValueError(f"Candidate is not for a quarantined scoped asset: {filename}")
    item = matches[0]
    with Image.open(download) as original:
        original.load()
        if original.format not in {"JPEG", "PNG"} or original.size != EXPECTED_SIZE:
            raise ValueError(
                f"Not a native Gemini original: {original.format} {original.size}"
            )
        extension = ".jpg" if original.format == "JPEG" else ".png"
        source = SOURCE_DIR / (Path(filename).stem + extension)
        output = ROOT / filename
        if source.exists() or output.exists():
            if not source.is_file() or not output.is_file() or sha256(source) != sha256(download):
                raise FileExistsError(f"Conflicting replacement target exists: {filename}")
        else:
            shutil.copy2(download, source)
            original.convert("RGB").save(output, "PNG")
    with Image.open(source) as original, Image.open(ROOT / filename) as published:
        original.load()
        published.load()
        if published.format != "PNG" or published.size != EXPECTED_SIZE:
            raise ValueError("Published PNG validation failed")
        if ImageChops.difference(original.convert("RGB"), published.convert("RGB")).getbbox():
            raise ValueError("Native source and published PNG pixels differ")

    source_map_path = SOURCE_DIR / "qa" / f"{item['festival']}_source_map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    source_map[source_map_key(item)] = source.name
    write_json_atomic(source_map_path, source_map)

    backup_manifest = json.loads(BACKUP.read_text(encoding="utf-8"))
    restored = [
        record
        for record in backup_manifest["qualified_groups"]
        if record.get("city") == CITY
        and record.get("festival") == item["festival"]
        and record.get("weather") == item["weather"]
    ]
    if len(restored) != 1:
        raise ValueError("Could not find exactly one qualification record in backup")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing = [
        record
        for record in manifest["qualified_groups"]
        if
        record.get("city") == CITY
        and record.get("festival") == item["festival"]
        and record.get("weather") == item["weather"]
    ]
    if item["period"] == "all_day":
        group_ready = True
    else:
        group_items = [
            row
            for row in checkpoint["assets"]
            if row["festival"] == item["festival"]
            and row["weather"] == item["weather"]
            and row["period"] != "all_day"
        ]
        group_ready = all(
            row["status"] == "replacement_accepted" or row["filename"] == filename
            for row in group_items
        )
    manifest["qualified_groups"] = [
        record for record in manifest["qualified_groups"] if record not in existing
    ]
    if group_ready:
        restored_record = restored[0] | {
            "qualified_at": date.today().isoformat(),
            "criteria": note + "; native source pixel equality passed",
        }
        manifest["qualified_groups"].append(restored_record)
    write_json_atomic(MANIFEST, manifest)

    item["status"] = "replacement_accepted"
    item["replacement_source_file"] = source.name
    item["replacement_source_sha256"] = sha256(source)
    item["replacement_png_sha256"] = sha256(ROOT / filename)
    item["source_pixel_equality"] = True
    item["replacement_qa_note"] = note
    checkpoint.setdefault("accepted_replacements", []).append(filename)
    write_json_atomic(CHECKPOINT, checkpoint)
    print(
        json.dumps(
            {
                "candidate_accepted": filename,
                "source": str(source),
                "published": str(ROOT / filename),
                "source_pixel_equality": True,
            },
            indent=2,
        )
    )


def record_limited_recheck_pass(filename: str, note: str) -> None:
    """Record the one permitted post-relaxation adverse-weather recheck."""
    checkpoint = load_checkpoint()
    matches = [item for item in checkpoint["assets"] if item["filename"] == filename]
    if len(matches) != 1 or matches[0]["status"] != "replacement_accepted":
        raise ValueError(f"Accepted replacement not found for recheck: {filename}")
    item = matches[0]
    if item["weather"] not in {"heavy_rain", "typhoon", "strong_wind", "cold_wave"}:
        raise ValueError(f"Limited recheck is adverse-weather only: {filename}")
    asset = ROOT / filename
    validate_png(asset)
    if sha256(asset) != item["replacement_png_sha256"]:
        raise ValueError(f"Accepted replacement changed before recheck: {filename}")
    records = checkpoint.setdefault("limited_adverse_rechecks", [])
    existing = [record for record in records if record["filename"] == filename]
    if existing:
        if len(existing) != 1 or existing[0].get("result") != "passed":
            raise ValueError(f"Conflicting limited recheck exists: {filename}")
        print(json.dumps({"limited_recheck_already_passed": filename}, indent=2))
        return
    records.append(
        {
            "filename": filename,
            "result": "passed",
            "asset_sha256": sha256(asset),
            "note": note,
            "reviewed_at": date.today().isoformat(),
        }
    )
    write_json_atomic(CHECKPOINT, checkpoint)
    print(json.dumps({"limited_recheck_passed": filename}, indent=2))


def invalidate_accepted_candidate(filename: str, reason: str) -> None:
    """Undo an accepted replacement that fails the permitted limited recheck."""
    checkpoint = load_checkpoint()
    matches = [item for item in checkpoint["assets"] if item["filename"] == filename]
    if len(matches) != 1 or matches[0]["status"] != "replacement_accepted":
        raise ValueError(f"Accepted replacement not found for invalidation: {filename}")
    item = matches[0]
    if item["weather"] not in {"heavy_rain", "typhoon", "strong_wind", "cold_wave"}:
        raise ValueError(f"Limited invalidation is adverse-weather only: {filename}")
    asset = ROOT / filename
    source = SOURCE_DIR / str(item["replacement_source_file"])
    validate_png(asset)
    if sha256(asset) != item["replacement_png_sha256"]:
        raise ValueError(f"Accepted replacement PNG changed before invalidation: {filename}")
    if sha256(source) != item["replacement_source_sha256"]:
        raise ValueError(f"Accepted replacement source changed before invalidation: {filename}")

    candidates = REJECTED / "candidates"
    candidates.mkdir(exist_ok=True)
    attempt = 1 + len(list(candidates.glob(Path(filename).stem + "_attempt*.*")))
    rejected_source = candidates / f"{Path(filename).stem}_attempt{attempt}{source.suffix.lower()}"
    rejected_png = candidates / f"{Path(filename).stem}_attempt{attempt}_published.png"
    if rejected_source.exists() or rejected_png.exists():
        raise FileExistsError(f"Limited-recheck evidence already exists: {filename}")

    source_map_path = SOURCE_DIR / "qa" / f"{item['festival']}_source_map.json"
    source_map = json.loads(source_map_path.read_text(encoding="utf-8"))
    key = source_map_key(item)
    if source_map.get(key) != item["replacement_source_file"]:
        raise ValueError(f"Source-map entry changed before invalidation: {filename}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    matching_qualifications = [
        record
        for record in manifest["qualified_groups"]
        if record.get("city") == CITY
        and record.get("festival") == item["festival"]
        and record.get("weather") == item["weather"]
    ]
    if len(matching_qualifications) != 1:
        raise ValueError(f"Expected one current qualification before invalidation: {filename}")

    shutil.move(source, rejected_source)
    shutil.move(asset, rejected_png)
    del source_map[key]
    write_json_atomic(source_map_path, source_map)

    removed = remove_manifest_qualification(manifest, item)
    write_json_atomic(MANIFEST, manifest)

    rejection = {
        "filename": filename,
        "result": "failed",
        "candidate_file": rejected_source.name,
        "published_evidence_file": rejected_png.name,
        "candidate_sha256": sha256(rejected_source),
        "published_sha256": sha256(rejected_png),
        "reason": reason,
        "manifest_records_removed": removed,
        "reviewed_at": date.today().isoformat(),
    }
    checkpoint.setdefault("limited_adverse_rechecks", []).append(rejection)
    checkpoint.setdefault("rejected_candidates", []).append(rejection)
    checkpoint["accepted_replacements"] = [
        accepted for accepted in checkpoint.get("accepted_replacements", []) if accepted != filename
    ]
    for field in (
        "replacement_source_file",
        "replacement_source_sha256",
        "replacement_png_sha256",
        "source_pixel_equality",
        "replacement_qa_note",
    ):
        item.pop(field, None)
    item["status"] = "failed_quarantined"
    item["recheck_failure_reason"] = reason
    write_json_atomic(CHECKPOINT, checkpoint)

    failed_qa_path = REJECTED / "failed_visual_qa.json"
    failed_qa = json.loads(failed_qa_path.read_text(encoding="utf-8"))
    failed_qa.setdefault("limited_adverse_recheck_failures", []).append(rejection)
    write_json_atomic(failed_qa_path, failed_qa)
    print(
        json.dumps(
            {
                "accepted_candidate_invalidated": filename,
                "manifest_records_removed": len(removed),
                "evidence": [str(rejected_source), str(rejected_png)],
            },
            indent=2,
        )
    )


def finalize() -> None:
    checkpoint = load_checkpoint()
    if checkpoint.get("finalized"):
        raise ValueError("Checkpoint is already finalized")

    assets = checkpoint["assets"]
    expected = expected_assets()
    expected_names = {item["filename"] for item in expected}
    observed_names = {item["filename"] for item in assets}
    allowed_statuses = {"passed", "replacement_accepted"}
    if len(assets) != 84 or observed_names != expected_names:
        raise ValueError("Finalization requires exactly the 84 scoped NewTaipei assets")
    incomplete = [
        item["filename"] for item in assets if item.get("status") not in allowed_statuses
    ]
    if incomplete:
        raise ValueError(f"Unfinished assets prevent finalization: {incomplete}")
    accepted = [
        item["filename"] for item in assets if item["status"] == "replacement_accepted"
    ]
    if len(accepted) != 69 or set(accepted) != set(checkpoint.get("accepted_replacements", [])):
        raise ValueError("Expected exactly 69 tracked replacement assets")

    source_maps: dict[str, dict[str, str]] = {}
    previous_sources: dict[str, Path] = {}
    provenance: dict[str, list[dict[str, object]]] = {festival: [] for festival in FESTIVALS}
    for festival in FESTIVALS:
        source_map_path = SOURCE_DIR / "qa" / f"{festival}_source_map.json"
        source_maps[festival] = json.loads(source_map_path.read_text(encoding="utf-8"))
        previous_record_path = ROOT / "qa" / f"{festival}_{CITY}_provenance_and_visual_qa.json"
        previous_record = json.loads(previous_record_path.read_text(encoding="utf-8"))
        for row in previous_record.get("assets", []):
            if row.get("filename") and row.get("source_file"):
                previous_sources[str(row["filename"])] = Path(str(row["source_file"]))

    for item in assets:
        filename = str(item["filename"])
        festival = str(item["festival"])
        key = source_map_key(item)
        source_name = source_maps[festival].get(key)
        if not source_name:
            raise ValueError(f"Missing source-map entry: {festival}/{key}")
        source = SOURCE_DIR / source_name
        if not source.is_file():
            source = SOURCE_DIR / filename
        if not source.is_file():
            source = previous_sources.get(filename, source)
        if not source.is_file():
            raise FileNotFoundError(f"Native source file is unavailable: {filename}: {source}")
        published = ROOT / filename
        validate_png(published)
        with Image.open(source) as original, Image.open(published) as png:
            original.load()
            png.load()
            if original.size != EXPECTED_SIZE:
                raise ValueError(f"Native source dimensions failed: {filename}")
            if ImageChops.difference(original.convert("RGB"), png.convert("RGB")).getbbox():
                raise ValueError(f"Source pixel equality failed: {filename}")
        provenance[festival].append(
            {
                "filename": filename,
                "source_file": str(source.resolve()),
                "source_sha256": sha256(source),
                "png_sha256": sha256(published),
                "source_pixel_equality": True,
                "qa": item.get("replacement_qa_note", item.get("qa_note")),
            }
        )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    backup_manifest = json.loads(BACKUP.read_text(encoding="utf-8"))
    non_newtaipei_before = {
        key: [row for row in backup_manifest[key] if row.get("city") != CITY]
        for key in ("qualified_groups", "qualified_all_day")
    }
    qa_record = str((REJECTED / "failed_visual_qa.json").relative_to(ROOT)).replace("\\", "/")
    batches = [
        row
        for row in manifest.get("failed_batches", [])
        if row.get("city") == CITY and row.get("qa_record") == qa_record
    ]
    if len(batches) != 1 or batches[0].get("status") not in {
        "composition_reqa_in_progress",
        "replaced_and_requalified",
    }:
        raise ValueError("Expected one active or materialized NewTaipei composition re-QA batch")
    if batches[0].get("rejected_count") != 69:
        raise ValueError("Active NewTaipei batch must contain exactly 69 quarantined originals")
    materialized = batches[0].get("status") == "replaced_and_requalified"

    expected_qualifications = {
        (item["festival"], item["weather"])
        for item in expected
    }
    current_qualifications = [
        row
        for row in manifest["qualified_groups"]
        if row.get("city") == CITY and row.get("festival") in FESTIVALS
    ]
    current_keys = [(row.get("festival"), row.get("weather")) for row in current_qualifications]
    if len(current_keys) != len(expected_qualifications) or set(current_keys) != expected_qualifications:
        raise ValueError("NewTaipei manifest qualifications are incomplete or duplicated")

    affected_sheets = list(checkpoint.get("affected_contact_sheets", []))
    if len(affected_sheets) != len(set(affected_sheets)) or len(affected_sheets) != 13:
        raise ValueError("Expected exactly 13 unique affected contact sheets")
    qa_dir = ROOT / "qa"
    if not materialized:
        for sheet_name in affected_sheets:
            matches = [festival for festival in FESTIVALS if sheet_name.startswith(f"{festival}_{CITY}_")]
            if len(matches) != 1:
                raise ValueError(f"Out-of-scope contact sheet: {sheet_name}")
            festival = matches[0]
            output = qa_dir / sheet_name
            if sheet_name.endswith("_sunny_6grid.png"):
                build_regular_sheet(ROOT, festival, "sunny", output)
            elif sheet_name.endswith("_partly_cloudy_6grid.png"):
                build_regular_sheet(ROOT, festival, "partly_cloudy", output)
            elif sheet_name == f"{festival}_{CITY}_all_day_{len(all_day_weathers(festival))}grid.png":
                build_all_day_sheet(ROOT, festival, output)
            else:
                raise ValueError(f"Unexpected affected contact sheet: {sheet_name}")

        for festival in FESTIVALS:
            records = sorted(provenance[festival], key=lambda row: str(row["filename"]))
            write_json_atomic(
                qa_dir / f"{festival}_{CITY}_provenance_and_visual_qa.json",
                {
                    "city": CITY,
                    "festival": festival,
                    "reviewed_at": date.today().isoformat(),
                    "assets": records,
                    "reviewed_sheets": [
                        f"qa/{festival}_{CITY}_sunny_6grid.png",
                        f"qa/{festival}_{CITY}_partly_cloudy_6grid.png",
                        f"qa/{festival}_{CITY}_all_day_{len(all_day_weathers(festival))}grid.png",
                    ],
                    "source_pixel_equality": True,
                    "major_error_qa": "passed",
                },
            )

        batches[0]["status"] = "replaced_and_requalified"
        batches[0]["finalized_at"] = date.today().isoformat()
        write_json_atomic(MANIFEST, manifest)

    final_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for key, rows in non_newtaipei_before.items():
        if [row for row in final_manifest[key] if row.get("city") != CITY] != rows:
            raise AssertionError(f"Non-NewTaipei manifest records changed in {key}")
    audits = {festival: audit_festival(ROOT, festival) for festival in FESTIVALS}
    if not all(result["complete"] for result in audits.values()):
        raise ValueError(f"Final NewTaipei festival audit failed: {audits}")

    checkpoint["finalized"] = True
    checkpoint["finalized_at"] = date.today().isoformat()
    checkpoint["rebuilt_contact_sheets"] = affected_sheets
    checkpoint["provenance_asset_count"] = sum(len(rows) for rows in provenance.values())
    checkpoint["manifest_qualification_count"] = len(current_qualifications)
    checkpoint["audit"] = audits
    write_json_atomic(CHECKPOINT, checkpoint)
    print(
        json.dumps(
            {
                "finalized": True,
                "assets": len(assets),
                "replacement_accepted": len(accepted),
                "retained_passed": len(assets) - len(accepted),
                "rebuilt_contact_sheets": affected_sheets,
                "manifest_qualifications": len(current_qualifications),
                "audits": audits,
            },
            indent=2,
        )
    )


def status() -> None:
    checkpoint = load_checkpoint()
    pending = [item["filename"] for item in checkpoint["assets"] if item["status"] == "pending"]
    print(
        json.dumps(
            {
                "reviewed_count": checkpoint["reviewed_count"],
                "passed_count": checkpoint["passed_count"],
                "failed_count": checkpoint["failed_count"],
                "pending_count": len(pending),
                "next_pending": pending[0] if pending else None,
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    pass_parser = subparsers.add_parser("pass")
    pass_parser.add_argument("filename")
    pass_parser.add_argument("--note", required=True)
    fail_parser = subparsers.add_parser("fail")
    fail_parser.add_argument("filename")
    fail_parser.add_argument("--reason", required=True)
    candidate_reject_parser = subparsers.add_parser("candidate-reject")
    candidate_reject_parser.add_argument("download", type=Path)
    candidate_reject_parser.add_argument("filename")
    candidate_reject_parser.add_argument("--reason", required=True)
    candidate_failure_parser = subparsers.add_parser("candidate-failure")
    candidate_failure_parser.add_argument("filename")
    candidate_failure_parser.add_argument("--reason", required=True)
    candidate_accept_parser = subparsers.add_parser("candidate-accept")
    candidate_accept_parser.add_argument("download", type=Path)
    candidate_accept_parser.add_argument("filename")
    candidate_accept_parser.add_argument("--note", required=True)
    recheck_pass_parser = subparsers.add_parser("recheck-pass")
    recheck_pass_parser.add_argument("filename")
    recheck_pass_parser.add_argument("--note", required=True)
    recheck_fail_parser = subparsers.add_parser("recheck-fail")
    recheck_fail_parser.add_argument("filename")
    recheck_fail_parser.add_argument("--reason", required=True)
    subparsers.add_parser("finalize")
    subparsers.add_parser("status")
    args = parser.parse_args()
    if args.command == "init":
        initialize()
    elif args.command == "pass":
        record_pass(args.filename, args.note)
    elif args.command == "fail":
        record_fail(args.filename, args.reason)
    elif args.command == "candidate-reject":
        record_candidate_rejection(args.download.resolve(), args.filename, args.reason)
    elif args.command == "candidate-failure":
        record_candidate_failure(args.filename, args.reason)
    elif args.command == "candidate-accept":
        accept_candidate(args.download.resolve(), args.filename, args.note)
    elif args.command == "recheck-pass":
        record_limited_recheck_pass(args.filename, args.note)
    elif args.command == "recheck-fail":
        invalidate_accepted_candidate(args.filename, args.reason)
    elif args.command == "finalize":
        finalize()
    else:
        status()


if __name__ == "__main__":
    main()
