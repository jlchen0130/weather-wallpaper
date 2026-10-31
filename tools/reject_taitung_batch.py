"""Preserve and disqualify the Taitung batch rejected by visual review."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
BACKUP = ROOT / "qa" / "rejected" / "Taitung_2026-10-10_flat_geometry"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    manifest = ROOT / "qa" / "qualified_assets.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    BACKUP.mkdir(parents=True, exist_ok=True)
    paths = list(ROOT.glob("none_Taitung_person_*.png"))
    paths += list((ROOT / "master").glob("none_Taitung_person_*.png"))
    paths += list((ROOT / "qa").glob("Taitung_*.png"))
    hashes: dict[str, str] = {}
    for source in paths:
        relative = source.relative_to(ROOT)
        target = BACKUP / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        if digest(source) != digest(target):
            raise RuntimeError(f"Backup mismatch: {relative}")
        hashes[str(relative)] = digest(target)

    saved_manifest = BACKUP / "qualified_assets_before_rejection.json"
    if not saved_manifest.exists():
        shutil.copy2(manifest, saved_manifest)

    rejected = []
    for key in ("qualified_groups", "qualified_all_day"):
        rejected += [e for e in data.get(key, []) if e.get("city") == "Taitung"]
        data[key] = [e for e in data.get(key, []) if e.get("city") != "Taitung"]

    report = {
        "city": "Taitung",
        "status": "failed",
        "reviewed_at": "2026-10-10",
        "reason": (
            "Visual QA rejects flat geometric illustration: polygon mountains, geometric hot-air "
            "balloons and stick-like figure; lacks fine matte three-dimensional needle-felt material. "
            "Prior size/file audit was incorrectly reported as visual acceptance."
        ),
        "rejected_records": rejected,
        "preserved_files_sha256": hashes,
        "qualification_revoked": True,
    }
    report_path = BACKUP / "failed_visual_qa.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = data.setdefault("failed_batches", [])
    qa_record = str(report_path.relative_to(ROOT))
    if not any(e.get("city") == "Taitung" and e.get("qa_record") == qa_record for e in failures):
        failures.append({"city": "Taitung", "status": "failed", "qa_record": qa_record, "reason": report["reason"]})
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    withdrawn = BACKUP / "withdrawn_formal"
    for source in paths:
        relative = source.relative_to(ROOT)
        target = withdrawn / relative
        target.resolve().relative_to(BACKUP.resolve())
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    print(json.dumps({"backed_up_files": len(paths), "revoked_records": len(rejected), "backup": str(BACKUP)}))


if __name__ == "__main__":
    main()
