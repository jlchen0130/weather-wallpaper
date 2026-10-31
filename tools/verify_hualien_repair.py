"""Verify Hualien source provenance, formal publication, and preserved failure evidence."""
import json
from pathlib import Path
from PIL import Image
from rebuild_hualien_assets import ROOT, STAGE, REQUIRED, SIZE, digest, validate
from audit_weather_assets import audit_city


def main():
    data = json.loads((STAGE / "provenance_and_visual_qa.json").read_text(encoding="utf-8"))
    assert set(data["assets"]) == set(REQUIRED)
    for name in REQUIRED:
        record = data["assets"][name]
        validate(STAGE / name)
        assert record["visual_qa"] == "passed"
        assert digest(STAGE / name) == record["sha256"]
        original = STAGE / record["original_file"]
        assert digest(original) == record["original_sha256"]
        with Image.open(original) as image:
            image.load()
            assert image.size == SIZE
            assert image.format == record["original_format"]
            with Image.open(STAGE / name) as output:
                output.load()
                assert image.convert("RGB").tobytes() == output.tobytes()
        validate(ROOT / name)
        assert digest(ROOT / name) == record["sha256"]
    assert len(data["sheets"]) == 3
    for name, record in data["sheets"].items():
        assert record["visual_qa"] == "passed"
        assert digest(STAGE / "qa" / name) == record["sha256"]
        assert digest(ROOT / "qa" / name) == record["sha256"]
    assert digest(ROOT / "qa" / "Hualien_provenance_and_visual_qa.json") == digest(STAGE / "provenance_and_visual_qa.json")
    backup = ROOT / "qa" / "rejected" / "Hualien_2026-10-10_flat_geometry"
    failed = json.loads((backup / "failed_visual_qa.json").read_text(encoding="utf-8"))
    assert len(failed["preserved_files_sha256"]) == 28
    for name, sha in failed["preserved_files_sha256"].items():
        assert digest(backup / name) == sha
        assert digest(backup / "withdrawn_formal" / name) == sha
    before = json.loads((backup / "qualified_assets_before_rejection.json").read_text(encoding="utf-8"))
    current = json.loads((ROOT / "qa" / "qualified_assets.json").read_text(encoding="utf-8"))
    for key, count in (("qualified_groups", 2), ("qualified_all_day", 12)):
        old_other = [r for r in before[key] if r.get("city") != "Hualien"]
        new_other = [r for r in current[key] if r.get("city") != "Hualien"]
        assert old_other == new_other, "Other-city qualification changed"
        records = [r for r in current[key] if r.get("city") == "Hualien"]
        assert len(records) == count
        assert len({r["weather"] for r in records}) == count
        assert all(r["weather"] != "torrential_rain" for r in records)
    assert any(r.get("city") == "Hualien" for r in current["failed_batches"])
    audit = audit_city(ROOT, "Hualien")
    assert audit["complete"]
    print(json.dumps({"audit": audit, "fully_decoded_pngs": 25, "source_pixel_equality": 25,
                      "reviewed_sheets": 3, "preserved_failed_files": 28,
                      "qualified_groups": 2, "qualified_all_day": 12,
                      "other_city_records_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
