"""Fail-closed Kaohsiung base-weather re-QA and publication workflow."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image

from build_all_day_contact_sheet import build_sheet as build_all_day_sheet
from build_weather_contact_sheet import build_sheet as build_regular_sheet


CITY = "Kaohsiung"
SIZE = (1536, 2752)
PREVIEW_RATIO_TOLERANCE = 0.02
# A browser can expose Gemini's complete 572x1024 blob only as an element crop.
# The crop remains valid QA evidence, but can never be ingested as a formal asset.
MIN_PREVIEW_SIZE = (250, 450)
PERIODS = ("morning", "afternoon", "sunset", "night", "midnight", "sunrise")
REGULAR = ("sunny", "partly_cloudy")
ALL_DAY = (
    "cloudy", "overcast", "light_rain", "heavy_rain", "typhoon", "fog",
    "haze", "strong_wind", "thunder_shower", "thunderstorm", "heatwave",
    "cold_wave",
)
ADVERSE = ALL_DAY[3:]
SCOPE = "Kaohsiung base weather assets only; festivals forbidden"
STANDARD_CRITERIA = (
    "Long-shot composition with at least 75 percent scenery, multiple Kaohsiung "
    "landmarks, multiple people, exactly 2-4 natural safe animals, and fine natural "
    "matte needle-felt texture; no yarn loops, crochet, plastic look, text, watermark "
    "or phone UI."
)
ADVERSE_CRITERIA = (
    STANDARD_CRITERIA + " Every person and every animal is inside the same fully "
    "enclosed room behind closed glass; all outdoor roads, plazas, paths, waterfronts, "
    "harbor areas, bridges, roofs, arcades, balconies and landmark foregrounds contain "
    "no people, animals, vehicles, bicycles, boats, vendors, flags or silhouettes."
)


def regular_name(weather: str, period: str) -> str:
    return f"none_{CITY}_person_{period}_{weather}.png"


def all_day_name(weather: str) -> str:
    return f"none_{CITY}_person_all_day_{weather}.png"


MASTER = f"none_{CITY}_person_master.png"
TARGETS = (
    MASTER,
    *[regular_name(weather, period) for weather in REGULAR for period in PERIODS],
    *[all_day_name(weather) for weather in ALL_DAY],
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


def validate_preview(path: Path) -> tuple[str, tuple[int, int]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with Image.open(path) as image:
        image.load()
        width, height = image.size
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError(f"Unsupported preview format: {image.format}")
        expected_ratio = SIZE[0] / SIZE[1]
        if abs((width / height) - expected_ratio) > PREVIEW_RATIO_TOLERANCE:
            raise ValueError(
                f"Preview is not a full portrait candidate: {image.size}; "
                "browser viewport screenshots are forbidden"
            )
        if width < MIN_PREVIEW_SIZE[0] or height < MIN_PREVIEW_SIZE[1]:
            raise ValueError(f"Preview is too small: {image.size}")
        return image.format, image.size


def manifest_scope(manifest: dict[str, object], include_city: bool) -> dict[str, object]:
    result: dict[str, object] = {}
    for key in ("qualified_groups", "qualified_all_day", "failed_batches"):
        result[key] = [
            row for row in manifest.get(key, [])
            if (row.get("city") == CITY) == include_city
        ]
    return result


def paths(root: Path) -> dict[str, Path]:
    qa = root / "qa"
    batch = f"{CITY}_2026-10-19_full_composition_reqa"
    return {
        "qa": qa,
        "stage": qa / "staging" / batch,
        "sources": qa / "sources" / batch,
        "rejected": qa / "rejected" / batch,
        "checkpoint": qa / f"{CITY}_weather_reqa_checkpoint.json",
        "manifest": qa / "qualified_assets.json",
    }


def formal_path(root: Path, filename: str) -> Path:
    return root / "master" / filename if filename == MASTER else root / filename


def stage_path(stage: Path, filename: str) -> Path:
    return stage / "master" / filename if filename == MASTER else stage / filename


def read_checkpoint(root: Path) -> tuple[dict[str, object], dict[str, Path]]:
    p = paths(root)
    checkpoint = json.loads(p["checkpoint"].read_text(encoding="utf-8"))
    if checkpoint.get("scope") != SCOPE:
        raise ValueError("Checkpoint is not scoped to Kaohsiung base weather")
    return checkpoint, p


def attempt_record(checkpoint: dict[str, object], attempt_id: str) -> dict[str, object]:
    attempts = checkpoint.setdefault("candidate_attempts", {})
    if attempt_id not in attempts:
        raise ValueError(f"Unknown candidate attempt: {attempt_id}")
    return attempts[attempt_id]


def begin_attempt(root: Path, attempt_id: str, filename: str, prompt: str) -> None:
    checkpoint, p = read_checkpoint(root)
    if filename not in TARGETS:
        raise ValueError(filename)
    if filename in checkpoint["accepted_replacements"]:
        raise FileExistsError(f"Replacement already accepted permanently: {filename}")
    attempts = checkpoint.setdefault("candidate_attempts", {})
    if attempt_id in attempts:
        raise FileExistsError(f"Attempt ID already exists: {attempt_id}")
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    for existing_id, record in attempts.items():
        if record.get("prompt_sha256") == prompt_hash:
            raise FileExistsError(f"Prompt already submitted as attempt {existing_id}")
        if record.get("target") == filename and record.get("status") in {
            "started", "preview_passed"
        }:
            raise RuntimeError(
                f"Target already has unresolved attempt {existing_id}: {record.get('status')}"
            )
    attempts[attempt_id] = {
        "target": filename,
        "prompt": prompt,
        "prompt_sha256": prompt_hash,
        "status": "started",
    }
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"attempt_started": attempt_id, "target": filename}, ensure_ascii=False))


def store_preview(root: Path, source: Path, attempt_id: str) -> dict[str, object]:
    checkpoint, p = read_checkpoint(root)
    record = attempt_record(checkpoint, attempt_id)
    if record.get("status") != "started":
        raise RuntimeError(f"Attempt is not awaiting preview: {record.get('status')}")
    image_format, image_size = validate_preview(source)
    suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[image_format]
    evidence = p["rejected"] / "preview_evidence" / f"{attempt_id}{suffix}"
    if evidence.exists():
        raise FileExistsError(evidence)
    atomic_copy(source, evidence)
    preview = {
        "file": str(evidence.relative_to(root)).replace("\\", "/"),
        "sha256": sha256(evidence),
        "format": image_format,
        "size": list(image_size),
    }
    record["preview"] = preview
    return checkpoint, p, record, preview


def preview_pass(root: Path, source: Path, attempt_id: str, note: str) -> None:
    checkpoint, p, record, preview = store_preview(root, source, attempt_id)
    record["status"] = "preview_passed"
    record["preview_note"] = note
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"preview_passed": attempt_id, "preview": preview}, ensure_ascii=False))

def dedup_rejections(root: Path) -> None:
    checkpoint, p = read_checkpoint(root)
    seen = {}; kept = []; removed = 0
    for record in checkpoint.get("rejected_candidates", []):
        key = (record.get("target"), record.get("file"), record.get("download_count"))
        if key in seen:
            prior = seen[key]
            prior["reason"] = prior.get("reason", "") + " | Duplicate evidence: " + record.get("reason", "")
            removed += 1
        else:
            seen[key] = record; kept.append(record)
    checkpoint["rejected_candidates"] = kept
    p["checkpoint"].write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"removed_exact_duplicates": removed, "remaining": len(kept)}, ensure_ascii=False))


def init(root: Path) -> None:
    p = paths(root)
    if p["checkpoint"].exists():
        checkpoint, _ = read_checkpoint(root)
        print(json.dumps(checkpoint, ensure_ascii=False, indent=2))
        return

    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))
    baseline: dict[str, str] = {}
    for filename in TARGETS:
        asset = formal_path(root, filename)
        validate_png(asset)
        relative = str(asset.relative_to(root)).replace("\\", "/")
        baseline[relative] = sha256(asset)
        atomic_copy(asset, p["rejected"] / relative)
    for sheet_name, size in (
        (f"{CITY}_sunny_6grid.png", (1620, 2074)),
        (f"{CITY}_partly_cloudy_6grid.png", (1620, 2074)),
        (f"{CITY}_all_day_12grid.png", (1632, 2390)),
    ):
        sheet = p["qa"] / sheet_name
        validate_png(sheet, size)
        baseline[f"qa/{sheet_name}"] = sha256(sheet)
        atomic_copy(sheet, p["rejected"] / "qa" / sheet_name)

    failure_reason = (
        "Existing image contains more than four natural animals and therefore lacks "
        "current-rule evidence."
    )
    failed = {filename: failure_reason for filename in TARGETS}
    for weather in ADVERSE:
        filename = all_day_name(weather)
        if weather in {"heavy_rain", "typhoon"}:
            failed[filename] = (
                "Closed-glass room contains more than four animals; current 2-4 animal "
                "limit is not met."
            )
        else:
            failed[filename] = (
                "People, animals and/or vehicles are outdoors; strict single enclosed "
                "closed-glass-room rule is not met."
            )
    checkpoint = {
        "city": CITY,
        "scope": SCOPE,
        "created_at": "2026-10-19",
        "status": "in_progress",
        "finalized": False,
        "matrix": {
            "master": MASTER,
            "regular": {weather: list(PERIODS) for weather in REGULAR},
            "all_day": list(ALL_DAY),
            "forbidden": ["torrential_rain"],
        },
        "permanent_pass": [],
        "failed_quarantined": failed,
        "accepted_replacements": {},
        "rejected_candidates": [],
        "reviewed_sheets": {},
        "baseline_kaohsiung_sha256": baseline,
        "baseline_non_kaohsiung_manifest_sha256": canonical_hash(
            manifest_scope(manifest, include_city=False)
        ),
        "standard_criteria": STANDARD_CRITERIA,
        "adverse_criteria": ADVERSE_CRITERIA,
    }
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({
        "status": "in_progress",
        "replacement_count": len(TARGETS),
        "targets": list(TARGETS),
        "checkpoint": str(p["checkpoint"]),
    }, ensure_ascii=False, indent=2))


def ingest(
    root: Path, source: Path, filename: str, note: str, prompt: str, attempt_id: str
) -> None:
    checkpoint, p = read_checkpoint(root)
    if filename not in TARGETS:
        raise ValueError(f"Not a Kaohsiung base-weather target: {filename}")
    accepted = checkpoint["accepted_replacements"]
    if filename in accepted:
        raise FileExistsError(f"Replacement already accepted permanently: {filename}")
    attempt = attempt_record(checkpoint, attempt_id)
    if attempt.get("target") != filename or attempt.get("status") != "preview_passed":
        raise RuntimeError("Ingest requires the matching preview-passed attempt")
    if attempt.get("prompt") != prompt:
        raise ValueError("Ingest prompt does not match the registered attempt")
    with Image.open(source) as image:
        image.load()
        if image.format != "JPEG" or image.size != SIZE:
            raise ValueError(f"Expected native JPEG {SIZE}, got {image.format} {image.size}")
        pixels = image.convert("RGB").tobytes()
        output = stage_path(p["stage"], filename)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + ".tmp")
        image.convert("RGB").save(temporary, "PNG", optimize=True)
    validate_png(temporary)
    with Image.open(temporary) as converted:
        converted.load()
        if converted.tobytes() != pixels:
            temporary.unlink(missing_ok=True)
            raise RuntimeError("Source/output pixel mismatch")
    os.replace(temporary, output)
    original = p["sources"] / f"{Path(filename).stem}{source.suffix.lower()}"
    if original.exists():
        raise FileExistsError(original)
    atomic_copy(source, original)
    accepted[filename] = {
        "asset_file": str(output.relative_to(p["stage"])).replace("\\", "/"),
        "source_file": str(original.relative_to(root)).replace("\\", "/"),
        "source_sha256": sha256(original),
        "png_sha256": sha256(output),
        "source_pixel_equality": True,
        "download_count": 1,
        "visual_qa": "passed",
        "review_note": note,
        "prompt": prompt,
        "attempt_id": attempt_id,
        "preview_evidence": attempt["preview"],
    }
    attempt["status"] = "accepted"
    checkpoint["status"] = (
        "ready_for_sheets" if set(accepted) == set(TARGETS) else "in_progress"
    )
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"accepted": filename, "status": checkpoint["status"]}, ensure_ascii=False))


def reject(root: Path, source: Path, filename: str, reason: str, attempt_id: str) -> None:
    checkpoint, p = read_checkpoint(root)
    if filename not in TARGETS:
        raise ValueError(filename)
    attempt = attempt_record(checkpoint, attempt_id)
    if attempt.get("target") != filename or attempt.get("status") != "preview_passed":
        raise RuntimeError("Native rejection requires the matching preview-passed attempt")
    with Image.open(source) as image:
        image.load()
        if image.size != SIZE or image.format != "JPEG":
            raise ValueError(f"Rejected candidate is not native JPEG {SIZE}")
    stem = Path(filename).stem
    attempts = list(p["rejected"].glob(f"candidate_{stem}_attempt*{source.suffix.lower()}"))
    target = p["rejected"] / f"candidate_{stem}_attempt{len(attempts) + 1}{source.suffix.lower()}"
    atomic_copy(source, target)
    checkpoint["rejected_candidates"].append({
        "target": filename,
        "attempt_id": attempt_id,
        "file": str(target.relative_to(root)).replace("\\", "/"),
        "sha256": sha256(target),
        "reason": reason,
    })
    attempt["status"] = "native_rejected"
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"rejected": filename, "file": str(target)}, ensure_ascii=False))


def preview_reject(root: Path, source: Path, attempt_id: str, reason: str) -> None:
    checkpoint, p, record, preview = store_preview(root, source, attempt_id)
    checkpoint["rejected_candidates"].append({
        "target": record["target"],
        "attempt_id": attempt_id,
        "file": preview["file"],
        "sha256": preview["sha256"],
        "download_count": 0,
        "reason": reason,
    })
    record["status"] = "preview_rejected"
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"preview_rejected": attempt_id}, ensure_ascii=False))


def quota_blocked(root: Path, attempt_id: str, reason: str) -> None:
    checkpoint, p = read_checkpoint(root)
    record = attempt_record(checkpoint, attempt_id)
    if record.get("status") != "started":
        raise RuntimeError(f"Attempt cannot be quota-blocked from {record.get('status')}")
    record["status"] = "quota_blocked"
    record["block_reason"] = reason
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"quota_blocked": attempt_id}, ensure_ascii=False))


def generation_failed(root: Path, attempt_id: str, reason: str, evidence: Path) -> None:
    checkpoint, p = read_checkpoint(root)
    record = attempt_record(checkpoint, attempt_id)
    if record.get("status") != "started":
        raise RuntimeError(f"Attempt cannot fail generation from {record.get('status')}")
    if not reason.strip():
        raise ValueError("Generation failure requires a reason")
    with Image.open(evidence) as image:
        image.load()
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError(f"Unsupported failure evidence: {image.format}")
        image_format, image_size = image.format, image.size
    suffix = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[image_format]
    destination = p["rejected"] / "generation_failures" / f"{attempt_id}{suffix}"
    if destination.exists():
        raise FileExistsError(destination)
    atomic_copy(evidence, destination)
    record["status"] = "generation_failed"
    record["generation_failure"] = {
        "reason": reason,
        "evidence_file": str(destination.relative_to(root)).replace("\\", "/"),
        "evidence_sha256": sha256(destination),
        "evidence_format": image_format,
        "evidence_size": list(image_size),
    }
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"generation_failed": attempt_id}, ensure_ascii=False))


def workflow_status(root: Path) -> None:
    checkpoint, _ = read_checkpoint(root)
    accepted = set(checkpoint.get("accepted_replacements", {}))
    attempts = checkpoint.get("candidate_attempts", {})
    print(json.dumps({
        "checkpoint_status": checkpoint.get("status"),
        "accepted_count": len(accepted),
        "target_count": len(TARGETS),
        "missing_targets": [name for name in TARGETS if name not in accepted],
        "active_attempts": {
            key: value for key, value in attempts.items()
            if value.get("status") in {"started", "preview_passed"}
        },
        "quota_blocked_attempts": [
            key for key, value in attempts.items() if value.get("status") == "quota_blocked"
        ],
    }, ensure_ascii=False, indent=2))


def sheets(root: Path) -> None:
    checkpoint, p = read_checkpoint(root)
    if set(checkpoint["accepted_replacements"]) != set(TARGETS):
        raise ValueError("All 25 replacements must be accepted before building sheets")
    outputs = {
        f"{CITY}_sunny_6grid.png": (1620, 2074),
        f"{CITY}_partly_cloudy_6grid.png": (1620, 2074),
        f"{CITY}_all_day_12grid.png": (1632, 2390),
    }
    build_regular_sheet(p["stage"], CITY, "sunny", p["stage"] / f"{CITY}_sunny_6grid.png")
    build_regular_sheet(p["stage"], CITY, "partly_cloudy", p["stage"] / f"{CITY}_partly_cloudy_6grid.png")
    build_all_day_sheet(p["stage"], CITY, p["stage"] / f"{CITY}_all_day_12grid.png")
    checkpoint["status"] = "sheets_pending_review"
    checkpoint["sheet_sha256"] = {}
    for name, size in outputs.items():
        validate_png(p["stage"] / name, size)
        checkpoint["sheet_sha256"][name] = sha256(p["stage"] / name)
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps(checkpoint["sheet_sha256"], ensure_ascii=False, indent=2))


def review_sheets(root: Path, note: str) -> None:
    checkpoint, p = read_checkpoint(root)
    expected = checkpoint.get("sheet_sha256", {})
    if set(expected) != {
        f"{CITY}_sunny_6grid.png", f"{CITY}_partly_cloudy_6grid.png",
        f"{CITY}_all_day_12grid.png",
    }:
        raise ValueError("Expected sheets were not built")
    reviews = {}
    for name, expected_hash in expected.items():
        actual = sha256(p["stage"] / name)
        if actual != expected_hash:
            raise ValueError(f"Sheet changed after construction: {name}")
        reviews[name] = {"sha256": actual, "visual_qa": "passed", "note": note}
    checkpoint["reviewed_sheets"] = reviews
    checkpoint["status"] = "ready_to_publish"
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps({"status": checkpoint["status"]}, ensure_ascii=False))


def publish(root: Path) -> None:
    checkpoint, p = read_checkpoint(root)
    if checkpoint.get("status") != "ready_to_publish":
        raise ValueError(f"Not ready to publish: {checkpoint.get('status')}")
    if set(checkpoint["accepted_replacements"]) != set(TARGETS):
        raise ValueError("Accepted replacement set is incomplete")
    manifest = json.loads(p["manifest"].read_text(encoding="utf-8"))
    non_city = canonical_hash(manifest_scope(manifest, include_city=False))
    if non_city != checkpoint["baseline_non_kaohsiung_manifest_sha256"]:
        raise ValueError("Non-Kaohsiung manifest changed since checkpoint creation")
    for filename, record in checkpoint["accepted_replacements"].items():
        staged = stage_path(p["stage"], filename)
        source = root / record["source_file"]
        validate_png(staged)
        if sha256(staged) != record["png_sha256"] or sha256(source) != record["source_sha256"]:
            raise ValueError(f"Changed accepted replacement: {filename}")
        with Image.open(source) as original, Image.open(staged) as converted:
            original.load(); converted.load()
            if original.convert("RGB").tobytes() != converted.tobytes():
                raise ValueError(f"Source/output pixel mismatch: {filename}")
    for name, review in checkpoint["reviewed_sheets"].items():
        if review.get("visual_qa") != "passed" or review.get("sha256") != sha256(p["stage"] / name):
            raise ValueError(f"Sheet unreviewed or changed: {name}")

    groups = [row for row in manifest.get("qualified_groups", []) if row.get("city") != CITY]
    for weather in REGULAR:
        groups.append({
            "city": CITY, "style": "knitted", "character": "person",
            "weather": weather, "periods": list(PERIODS),
            "qa_file": f"{CITY}_{weather}_6grid.png", "qualified_at": "2026-10-19",
            "source_method": "native Gemini 1536x2752 JPEG decoded to RGB PNG without resizing or overlays",
            "visual_qa": "passed", "criteria": STANDARD_CRITERIA,
        })
    all_day = [row for row in manifest.get("qualified_all_day", []) if row.get("city") != CITY]
    for weather in ALL_DAY:
        record = checkpoint["accepted_replacements"][all_day_name(weather)]
        all_day.append({
            "city": CITY, "style": "knitted", "character": "person",
            "weather": weather, "asset_file": all_day_name(weather),
            "master_file": f"master/{MASTER}", "qa_file": f"{CITY}_all_day_12grid.png",
            "qualified_at": "2026-10-19",
            "source_method": "native Gemini 1536x2752 JPEG decoded to RGB PNG without resizing or overlays",
            "source_file": record["source_file"], "source_pixel_equality": True,
            "visual_qa": "passed",
            "criteria": ADVERSE_CRITERIA if weather in ADVERSE else STANDARD_CRITERIA,
        })
    manifest["qualified_groups"] = groups
    manifest["qualified_all_day"] = all_day

    for filename in TARGETS:
        atomic_copy(stage_path(p["stage"], filename), formal_path(root, filename))
    for name in checkpoint["reviewed_sheets"]:
        atomic_copy(p["stage"] / name, p["qa"] / name)
    atomic_json(p["manifest"], manifest)
    if canonical_hash(manifest_scope(manifest, include_city=False)) != non_city:
        raise AssertionError("Non-Kaohsiung manifest changed during publication")
    checkpoint["status"] = "complete"
    checkpoint["finalized"] = True
    checkpoint["publication"] = {
        "published_at": "2026-10-19",
        "replacement_count": len(TARGETS),
        "qualified_all_day_count": len(ALL_DAY),
        "qualified_regular_group_count": len(REGULAR),
        "non_kaohsiung_manifest_sha256": non_city,
        "formal_sheets": [f"qa/{name}" for name in checkpoint["reviewed_sheets"]],
    }
    atomic_json(p["checkpoint"], checkpoint)
    print(json.dumps(checkpoint["publication"], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("init")
    begin_parser = sub.add_parser("begin-attempt")
    begin_parser.add_argument("attempt_id")
    begin_parser.add_argument("filename", choices=TARGETS)
    begin_parser.add_argument("--prompt", required=True)
    preview_pass_parser = sub.add_parser("preview-pass")
    preview_pass_parser.add_argument("source", type=Path)
    preview_pass_parser.add_argument("attempt_id")
    preview_pass_parser.add_argument("--note", required=True)
    ingest_parser = sub.add_parser("ingest")
    ingest_parser.add_argument("source", type=Path)
    ingest_parser.add_argument("filename", choices=TARGETS)
    ingest_parser.add_argument("--note", required=True)
    ingest_parser.add_argument("--prompt", required=True)
    ingest_parser.add_argument("--attempt-id", required=True)
    reject_parser = sub.add_parser("reject")
    reject_parser.add_argument("source", type=Path)
    reject_parser.add_argument("filename", choices=TARGETS)
    reject_parser.add_argument("--reason", required=True)
    reject_parser.add_argument("--attempt-id", required=True)
    preview_parser = sub.add_parser("preview-reject")
    preview_parser.add_argument("source", type=Path)
    preview_parser.add_argument("attempt_id")
    preview_parser.add_argument("--reason", required=True)
    quota_parser = sub.add_parser("quota-blocked")
    quota_parser.add_argument("attempt_id")
    quota_parser.add_argument("--reason", required=True)
    failure_parser = sub.add_parser("generation-failed")
    failure_parser.add_argument("attempt_id")
    failure_parser.add_argument("--reason", required=True)
    failure_parser.add_argument("--evidence", required=True, type=Path)
    sub.add_parser("sheets")
    review_parser = sub.add_parser("review-sheets")
    review_parser.add_argument("--note", required=True)
    sub.add_parser("publish")
    sub.add_parser("status")
    sub.add_parser("workflow-status")
    sub.add_parser("dedup-rejections")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "init": init(root)
    elif args.action == "begin-attempt": begin_attempt(root, args.attempt_id, args.filename, args.prompt)
    elif args.action == "preview-pass": preview_pass(root, args.source.resolve(), args.attempt_id, args.note)
    elif args.action == "ingest": ingest(root, args.source.resolve(), args.filename, args.note, args.prompt, args.attempt_id)
    elif args.action == "reject": reject(root, args.source.resolve(), args.filename, args.reason, args.attempt_id)
    elif args.action == "preview-reject": preview_reject(root, args.source.resolve(), args.attempt_id, args.reason)
    elif args.action == "quota-blocked": quota_blocked(root, args.attempt_id, args.reason)
    elif args.action == "generation-failed": generation_failed(root, args.attempt_id, args.reason, args.evidence.resolve())
    elif args.action == "sheets": sheets(root)
    elif args.action == "review-sheets": review_sheets(root, args.note)
    elif args.action == "publish": publish(root)
    elif args.action == "dedup-rejections": dedup_rejections(root)
    elif args.action == "workflow-status": workflow_status(root)
    else:
        checkpoint, _ = read_checkpoint(root)
        print(json.dumps(checkpoint, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
