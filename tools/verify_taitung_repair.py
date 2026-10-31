"""Verify staged or published Taitung provenance without accepting a partial batch."""
import argparse
import json

from PIL import Image

from audit_weather_assets import audit_city
from rebuild_taitung_assets import ROOT, STAGE, REQUIRED, SIZE, digest, validate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--published", action="store_true")
    args = parser.parse_args()
    data = json.loads((STAGE / "provenance_and_visual_qa.json").read_text(encoding="utf-8"))
    assert set(data["assets"]).issubset(REQUIRED)
    for name, record in data["assets"].items():
        validate(STAGE / name)
        assert record["visual_qa"] == "passed"
        assert digest(STAGE / name) == record["sha256"]
        source_path = STAGE / record["original_file"]
        assert digest(source_path) == record["original_sha256"]
        with Image.open(source_path) as source, Image.open(STAGE / name) as output:
            source.load()
            output.load()
            assert source.size == SIZE and source.format == record["original_format"]
            assert source.convert("RGB").tobytes() == output.tobytes()
        if args.published:
            validate(ROOT / name)
            assert digest(ROOT / name) == record["sha256"]
    for name, record in data["sheets"].items():
        assert record["visual_qa"] == "passed"
        assert digest(STAGE / "qa" / name) == record["sha256"]
        if args.published:
            assert digest(ROOT / "qa" / name) == record["sha256"]

    backup = ROOT / "qa" / "rejected" / "Taitung_2026-10-10_flat_geometry"
    failed = json.loads((backup / "failed_visual_qa.json").read_text(encoding="utf-8"))
    assert len(failed["preserved_files_sha256"]) == 28
    for name, sha in failed["preserved_files_sha256"].items():
        assert digest(backup / name) == sha
        assert digest(backup / "withdrawn_formal" / name) == sha
    before = json.loads((backup / "qualified_assets_before_rejection.json").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "qa" / "qualified_assets.json").read_text(encoding="utf-8"))
    for key, count in (("qualified_groups", 2), ("qualified_all_day", 12)):
        assert [r for r in before[key] if r.get("city") != "Taitung"] == [r for r in current[key] if r.get("city") != "Taitung"], "Other-city qualification changed"
        records = [r for r in current[key] if r.get("city") == "Taitung"]
        assert len(records) == (count if args.published else 0)
        assert all(r["weather"] != "torrential_rain" for r in records)
    if args.published:
        assert set(data["assets"]) == set(REQUIRED)
        assert len(data["sheets"]) == 3
        assert digest(ROOT / "qa" / "Taitung_provenance_and_visual_qa.json") == digest(STAGE / "provenance_and_visual_qa.json")
    result = {
        "stage_complete": set(data["assets"]) == set(REQUIRED) and len(data["sheets"]) == 3,
        "staged_reviewed_pngs": len(data["assets"]),
        "source_pixel_equality": len(data["assets"]),
        "original_and_png_sha256_verified": True,
        "reviewed_sheets": len(data["sheets"]),
        "preserved_failed_files": 28,
        "other_city_records_unchanged": True,
        "missing_stage_assets": [name for name in REQUIRED if name not in data["assets"]],
        "formal_audit": audit_city(ROOT, "Taitung"),
    }
    if args.published:
        assert result["formal_audit"]["complete"]
    (STAGE / "verification_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
