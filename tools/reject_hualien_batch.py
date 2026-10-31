"""Preserve and disqualify the Hualien batch rejected by visual review."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(r"D:\projects\weather_wallpaper\pic\knitted\person")
BACKUP = ROOT / "qa" / "rejected" / "Hualien_2026-10-10_flat_geometry"

def main():
    manifest = ROOT / "qa" / "qualified_assets.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    BACKUP.mkdir(parents=True, exist_ok=True)
    paths = list(ROOT.glob("none_Hualien_person_*.png"))
    paths += list((ROOT / "master").glob("none_Hualien_person_*.png"))
    paths += list((ROOT / "qa").glob("Hualien_*.png"))
    hashes = {}
    for source in paths:
        relative = source.relative_to(ROOT)
        target = BACKUP / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
        hashes[str(relative)] = hashlib.sha256(target.read_bytes()).hexdigest()
    saved_manifest = BACKUP / "qualified_assets_before_rejection.json"
    if not saved_manifest.exists():
        shutil.copy2(manifest, saved_manifest)
    rejected = []
    for key in ("qualified_groups", "qualified_all_day"):
        rejected += [entry for entry in data.get(key, []) if entry.get("city") == "Hualien"]
        data[key] = [entry for entry in data.get(key, []) if entry.get("city") != "Hualien"]
    previous_report_path = BACKUP / "failed_visual_qa.json"
    if not rejected and previous_report_path.exists():
        rejected = json.loads(previous_report_path.read_text(encoding="utf-8"))["rejected_records"]
    report = {
        "city": "Hualien", "status": "failed", "reviewed_at": "2026-10-10",
        "reason": "Visual QA rejects flat geometric illustration: polygon mountains, geometric sun and stick-like figure; lacks fine matte three-dimensional needle-felt material. Prior size/file audit was incorrectly reported as visual acceptance.",
        "rejected_records": rejected,
        "preserved_files_sha256": hashes,
        "qualification_revoked": True,
    }
    (BACKUP / "failed_visual_qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = data.setdefault("failed_batches", [])
    if not any(e.get("city") == "Hualien" and e.get("qa_record") == str((BACKUP / "failed_visual_qa.json").relative_to(ROOT)) for e in failures):
        failures.append({"city": "Hualien", "status": "failed", "qa_record": str((BACKUP / "failed_visual_qa.json").relative_to(ROOT)), "reason": report["reason"]})
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Withdraw rejected formal files only after verifying the preserved copy.
    withdrawn = BACKUP / "withdrawn_formal"
    for source in paths:
        source.resolve().relative_to(ROOT.resolve())
        relative = source.relative_to(ROOT)
        preserved = BACKUP / relative
        if hashlib.sha256(source.read_bytes()).hexdigest() != hashlib.sha256(preserved.read_bytes()).hexdigest():
            raise RuntimeError(f"Backup mismatch; refusing to withdraw {source.name}")
        target = withdrawn / relative
        target.resolve().relative_to(BACKUP.resolve())
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(target))
    print(json.dumps({"backed_up_files": len(paths), "revoked_records": len(rejected), "backup": str(BACKUP)}))

if __name__ == "__main__":
    main()
