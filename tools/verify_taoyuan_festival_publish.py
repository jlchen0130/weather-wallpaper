from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops

from audit_taoyuan_festival_assets import CITY, FESTIVALS, audit_festival
from publish_taoyuan_festivals import asset_specs, qa_names


def pixel_equal(left: Path, right: Path) -> bool:
    with Image.open(left) as a_image, Image.open(right) as b_image:
        a = a_image.convert("RGB")
        b = b_image.convert("RGB")
        return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("staging", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("formal_root", type=Path)
    parser.add_argument("checkpoint", type=Path)
    args = parser.parse_args()

    checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
    accepted = {row["filename"]: row for row in checkpoint["accepted_individually"]}
    audits = {festival: audit_festival(args.formal_root, festival) for festival in FESTIVALS}
    if not all(row["complete"] for row in audits.values()):
        raise SystemExit(f"Incomplete formal audit: {json.dumps(audits)}")

    source_equal = 0
    staging_equal = 0
    expected_names: set[str] = set()
    for festival in FESTIVALS:
        for _, filename in asset_specs(festival):
            expected_names.add(filename)
            source = args.source_root / str(accepted[filename]["source_file"])
            staged = args.staging / filename
            published = args.formal_root / filename
            if not pixel_equal(source, published):
                raise SystemExit(f"Source/published pixel mismatch: {filename}")
            source_equal += 1
            if not pixel_equal(staged, published):
                raise SystemExit(f"Staging/published pixel mismatch: {filename}")
            staging_equal += 1

    qa_dir = args.formal_root / "qa"
    expected_qa = {filename for festival in FESTIVALS for filename in qa_names(festival)}
    missing_qa = sorted(filename for filename in expected_qa if not (qa_dir / filename).is_file())
    if missing_qa:
        raise SystemExit(f"Missing published QA sheets: {missing_qa}")

    manifest_path = qa_dir / "qualified_assets.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    backups = sorted(qa_dir.glob(f"qualified_assets.before_{CITY}_festivals_*.json"))
    if not backups:
        raise SystemExit("Manifest backup is missing")
    before = json.loads(backups[-1].read_text(encoding="utf-8"))
    if manifest["qualified_all_day"] != before["qualified_all_day"]:
        raise SystemExit("qualified_all_day changed unexpectedly")
    if manifest["failed_batches"] != before["failed_batches"]:
        raise SystemExit("failed_batches changed unexpectedly")

    def unrelated(groups: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            row
            for row in groups
            if not (row.get("city") == CITY and row.get("festival") in FESTIVALS)
        ]

    if unrelated(manifest["qualified_groups"]) != unrelated(before["qualified_groups"]):
        raise SystemExit("Unrelated qualified_groups changed unexpectedly")
    taoyuan_groups = [
        row
        for row in manifest["qualified_groups"]
        if row.get("city") == CITY and row.get("festival") in FESTIVALS
    ]
    if len(taoyuan_groups) != 32:
        raise SystemExit(f"Unexpected Taoyuan festival manifest count: {len(taoyuan_groups)}")

    published_direct = {
        path.name
        for path in args.formal_root.glob(f"*_{CITY}_person_*.png")
        if any(path.name.startswith(f"{festival}_{CITY}_person_") for festival in FESTIVALS)
    }
    unexpected_published = sorted(published_direct - expected_names)
    torrential = sorted(path.name for path in args.formal_root.glob(f"*_{CITY}_*torrential_rain*.png"))
    if unexpected_published or torrential:
        raise SystemExit(
            f"Forbidden published files: unexpected={unexpected_published}, torrential={torrential}"
        )

    print(
        json.dumps(
            {
                "formal_root": str(args.formal_root),
                "festival_counts": {festival: audits[festival]["valid_png_count"] for festival in FESTIVALS},
                "published_total": len(expected_names),
                "source_published_pixel_equal": source_equal,
                "staging_published_pixel_equal": staging_equal,
                "published_qa_sheets": len(expected_qa),
                "manifest_taoyuan_festival_records": len(taoyuan_groups),
                "qualified_all_day_preserved": True,
                "failed_batches_preserved": True,
                "unrelated_qualified_groups_preserved": True,
                "unexpected_published": unexpected_published,
                "rejected_evidence_copied": False,
                "torrential_rain_published": torrential,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
