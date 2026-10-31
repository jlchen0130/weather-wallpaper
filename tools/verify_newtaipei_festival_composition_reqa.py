from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops

from audit_newtaipei_festival_assets import (
    CITY,
    FESTIVALS,
    audit_festival,
)
from reqa_newtaipei_festival_composition import (
    BACKUP,
    CHECKPOINT,
    EXPECTED_SIZE,
    MANIFEST,
    REJECTED,
    ROOT,
    expected_assets,
)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def pixel_equal(source: Path, published: Path) -> bool:
    with Image.open(source) as original, Image.open(published) as png:
        original.load()
        png.load()
        if original.size != EXPECTED_SIZE or png.size != EXPECTED_SIZE:
            return False
        if png.format != "PNG":
            return False
        return ImageChops.difference(original.convert("RGB"), png.convert("RGB")).getbbox() is None


def out_of_scope_rows(manifest: dict[str, object], key: str) -> list[dict[str, object]]:
    return [
        row
        for row in manifest[key]
        if not (row.get("city") == CITY and row.get("festival") in FESTIVALS)
    ]


def main() -> None:
    checkpoint = load_json(CHECKPOINT)
    if not checkpoint.get("finalized"):
        raise SystemExit("Checkpoint is not finalized")

    expected = expected_assets()
    expected_names = {item["filename"] for item in expected}
    statuses: dict[str, int] = {}
    for item in checkpoint["assets"]:
        status = str(item["status"])
        statuses[status] = statuses.get(status, 0) + 1
    if statuses != {"passed": 15, "replacement_accepted": 69}:
        raise SystemExit(f"Unexpected checkpoint statuses: {statuses}")

    current = load_json(MANIFEST)
    before = load_json(BACKUP)
    for key in ("qualified_groups", "qualified_all_day"):
        if out_of_scope_rows(current, key) != out_of_scope_rows(before, key):
            raise SystemExit(f"Out-of-scope manifest rows changed: {key}")

    qa_record = str((REJECTED / "failed_visual_qa.json").relative_to(ROOT)).replace("\\", "/")
    active_batch = [
        row
        for row in current["failed_batches"]
        if row.get("city") == CITY and row.get("qa_record") == qa_record
    ]
    if len(active_batch) != 1 or active_batch[0].get("status") != "replaced_and_requalified":
        raise SystemExit("NewTaipei re-QA batch is not finalized")
    other_batches = [row for row in current["failed_batches"] if row not in active_batch]
    if other_batches != before["failed_batches"]:
        raise SystemExit("Unrelated failed-batch records changed")

    expected_qualifications = {
        (item["festival"], item["weather"])
        for item in expected
    }
    scoped_qualifications = [
        row
        for row in current["qualified_groups"]
        if row.get("city") == CITY and row.get("festival") in FESTIVALS
    ]
    qualification_keys = [(row.get("festival"), row.get("weather")) for row in scoped_qualifications]
    if len(qualification_keys) != 34 or set(qualification_keys) != expected_qualifications:
        raise SystemExit("Expected exactly 34 unique NewTaipei festival qualification records")

    provenance_count = 0
    equality_count = 0
    provenance_names: set[str] = set()
    for festival in FESTIVALS:
        record = load_json(ROOT / "qa" / f"{festival}_{CITY}_provenance_and_visual_qa.json")
        for asset in record["assets"]:
            filename = str(asset["filename"])
            source = Path(str(asset["source_file"]))
            published = ROOT / filename
            provenance_count += 1
            provenance_names.add(filename)
            if not source.is_file() or not published.is_file() or not pixel_equal(source, published):
                raise SystemExit(f"Source/published pixel equality failed: {filename}")
            equality_count += 1
    if provenance_count != 84 or provenance_names != expected_names:
        raise SystemExit("Provenance does not cover exactly the 84 expected assets")

    audits = {festival: audit_festival(ROOT, festival) for festival in FESTIVALS}
    if not all(result["complete"] for result in audits.values()):
        raise SystemExit(f"NewTaipei audit failed: {audits}")
    if sum(int(result["valid_png_count"]) for result in audits.values()) != 84:
        raise SystemExit("Expected exactly 84 valid native PNG assets")

    rejected = load_json(REJECTED / "failed_visual_qa.json")
    original_assets = list((REJECTED / "assets").glob("*.png"))
    original_sources = list((REJECTED / "sources").glob("*"))
    if len(rejected["records"]) != 69 or len(original_assets) != 69 or len(original_sources) != 69:
        raise SystemExit("Rejected original evidence does not contain exactly 69 complete pairs")

    rebuilt = checkpoint.get("rebuilt_contact_sheets", [])
    if len(rebuilt) != 13 or len(set(rebuilt)) != 13:
        raise SystemExit("Checkpoint does not record exactly 13 rebuilt contact sheets")

    print(
        json.dumps(
            {
                "verified": True,
                "native_png_assets": 84,
                "source_pixel_equal": equality_count,
                "checkpoint_statuses": statuses,
                "manifest_qualifications": len(scoped_qualifications),
                "contact_sheets_total": 15,
                "contact_sheets_rebuilt": len(rebuilt),
                "rejected_original_pairs": len(original_assets),
                "unrelated_manifest_rows_preserved": True,
                "failed_batches_preserved_except_scoped_finalization": True,
                "audits": audits,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
